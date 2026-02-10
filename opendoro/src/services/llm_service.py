import json
from PyQt5.QtCore import QThread, pyqtSignal, QSettings
from openai import OpenAI
from src.core.agent_tools import TOOLS_SCHEMA, AVAILABLE_TOOLS
from src.core.logger import logger

class LLMWorker(QThread):
    finished = pyqtSignal(str, list) 
    chunk_received = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, messages, model="gpt-3.5-turbo", db=None):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.messages = list(messages) # Make a copy
        self.model = model
        self.db = db
        self.max_turns = 5 # Prevent infinite loops
        self.generated_images = [] # Track generated images

    def run(self):
        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            turn_count = 0
            
            while turn_count < self.max_turns:
                turn_count += 1
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    max_tokens=4096,
                    stream=True
                )
                
                full_content = ""
                tool_calls_buffer = {} # index -> dict
                
                for chunk in response:
                    delta = chunk.choices[0].delta
                    
                    # 1. Handle Content
                    if delta.content:
                        content_chunk = delta.content
                        full_content += content_chunk
                        self.chunk_received.emit(content_chunk)
                        
                    # 2. Handle Tool Calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_buffer:
                                tool_calls_buffer[idx] = {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                }
                            
                            if tc.id:
                                tool_calls_buffer[idx]["id"] = tc.id
                            if tc.function.name:
                                tool_calls_buffer[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments

                # End of stream for this turn
                
                # If no tool calls, we are done
                if not tool_calls_buffer:
                    logger.info(f"[LLMWorker] Finished. Total length: {len(full_content)}")
                    logger.info(f"[LLMWorker] Response content: {full_content}")
                    self.finished.emit(full_content, self.generated_images)
                    break
                
                # Process Tool Calls
                logger.info(f"[LLMWorker] Tool calls detected: {len(tool_calls_buffer)}")
                
                # Reconstruct assistant message with tool calls
                assistant_msg = {
                    "role": "assistant",
                    "content": full_content if full_content else None,
                    "tool_calls": []
                }
                
                sorted_indices = sorted(tool_calls_buffer.keys())
                for idx in sorted_indices:
                    assistant_msg["tool_calls"].append(tool_calls_buffer[idx])
                
                self.messages.append(assistant_msg)
                
                # Execute Tools
                for idx in sorted_indices:
                    tc_data = tool_calls_buffer[idx]
                    func_name = tc_data["function"]["name"]
                    func_args_str = tc_data["function"]["arguments"]
                    call_id = tc_data["id"]
                    
                    logger.info(f"[LLMWorker] Executing {func_name} with args: {func_args_str}")
                    
                    tool_result = ""
                    try:
                        func_args = json.loads(func_args_str)
                        if func_name in AVAILABLE_TOOLS:
                            func = AVAILABLE_TOOLS[func_name]
                            
                            if func_name == "generate_image":
                                # Read settings dynamically
                                img_base_url = ""
                                img_api_key = ""
                                img_model = "dall-e-3"
                                
                                if self.db:
                                    img_config = self.db.get_active_image_model()
                                    if img_config:
                                        # id, name, provider, base_url, api_key, model_name
                                        img_base_url = img_config[3]
                                        img_api_key = img_config[4]
                                        img_model = img_config[5]
                                
                                # Fallback to QSettings if DB config is missing (backward compatibility or initial state)
                                if not img_api_key and not img_base_url:
                                    settings = QSettings("DoroPet", "Settings")
                                    img_base_url = settings.value("img_base_url", "")
                                    img_api_key = settings.value("img_api_key", "")
                                    img_model = settings.value("img_model", "dall-e-3")
                                
                                tool_result = func(
                                    client, 
                                    base_url=img_base_url, 
                                    api_key=img_api_key, 
                                    model=img_model, 
                                    **func_args
                                )
                            else:
                                tool_result = func(**func_args)
                                
                            # Track images if any
                            if func_name == "generate_image":
                                try:
                                    res_json = json.loads(tool_result)
                                    if res_json.get("status") == "success" and "image_path" in res_json:
                                        self.generated_images.append(res_json["image_path"])
                                except:
                                    pass
                                    
                        else:
                            tool_result = json.dumps({"status": "error", "message": "Unknown tool"})
                    except Exception as e:
                        logger.error(f"[LLMWorker] Tool execution error: {e}")
                        tool_result = json.dumps({"status": "error", "message": str(e)})
                        
                    # Append tool result to messages
                    logger.info(f"[LLMWorker] Tool result: {tool_result}")
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_result
                    })
                    
                # Loop continues to next iteration to send tool results back to LLM
                
        except Exception as e:
            logger.error(f"[LLMWorker] Critical Error: {e}")
            self.error.emit(str(e))
