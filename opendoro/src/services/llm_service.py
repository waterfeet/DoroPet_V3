import json
import httpx
import time
import copy
from PyQt5.QtCore import QThread, pyqtSignal, QSettings
from openai import OpenAI
from src.core.agent_tools import TOOLS_SCHEMA, AVAILABLE_TOOLS
from src.core.logger import logger
from src.core.skill_manager import SkillManager
from src.core.stream_processor import StreamProcessor
from src.core.state_manager import StateManager, GenerationState

class LLMWorker(QThread):
    finished = pyqtSignal(str, str, list, list) # content, reasoning, tool_calls, images
    chunk_received = pyqtSignal(str)
    thinking_chunk = pyqtSignal(str)
    error = pyqtSignal(str)
    expression_changed = pyqtSignal(str)
    pet_attribute_changed = pyqtSignal(str, str)  # attribute, action
    tool_status_changed = pyqtSignal(str)
    tool_execution_update = pyqtSignal(str, str, str, str, str)
    stopped = pyqtSignal()

    def __init__(self, api_key, base_url, messages, model="gpt-3.5-turbo", db=None, is_thinking=0, enabled_plugins=None, available_expressions=None, skip_tools_and_max_tokens=False):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.messages = list(messages)
        self.model = model
        self.db = db
        self.is_thinking_model = is_thinking
        self.skip_tools_and_max_tokens = skip_tools_and_max_tokens
        logger.info(f"[LLMWorker] Initialized with model={model}, is_thinking_model={is_thinking} (type: {type(is_thinking).__name__}), skip_tools_and_max_tokens={skip_tools_and_max_tokens}")
        self.enabled_plugins = enabled_plugins if enabled_plugins is not None else ["search", "image", "coding", "file", "expression"]
        self.max_turns = 20
        self.generated_images = []
        self.reasoning_accumulated = ""
        self.tool_calls_accumulated = []
        self.available_expressions = available_expressions if available_expressions else []
        self.skill_manager = SkillManager()
        self._is_stopped = False
        self._response_iterator = None
        self.stream_processor = StreamProcessor()
        self.stream_processor.chunk_ready.connect(self.chunk_received.emit)
        self.stream_processor.thinking_chunk.connect(self.thinking_chunk.emit)
        self.state_manager = StateManager.get_instance()

    def stop(self):
        self._is_stopped = True
        self.stream_processor.stop()
        if self._response_iterator:
            try:
                if hasattr(self._response_iterator, 'close'):
                    self._response_iterator.close()
            except:
                pass

    def _build_api_params(self, max_tokens, turn_count):
        messages_for_api = []
        for msg in self.messages:
            msg_copy = copy.deepcopy(msg)
            if msg_copy.get("role") == "tool":
                if "tool_call_id" not in msg_copy:
                    continue
                content = msg_copy.get("content", "")
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    msg_copy["content"] = json.dumps({"result": content})
            messages_for_api.append(msg_copy)
        
        filtered_tools = []
        for tool in TOOLS_SCHEMA:
            tool_name = tool["function"]["name"]
            if tool_name == "set_expression" and "expression" not in self.enabled_plugins:
                continue
            if tool_name == "modify_pet_attribute" and "expression" not in self.enabled_plugins:
                continue
            if tool_name == "search" and "search" not in self.enabled_plugins:
                continue
            if tool_name == "generate_image" and "image" not in self.enabled_plugins:
                continue
            if tool_name in ["read_file", "write_file", "list_directory"] and "file" not in self.enabled_plugins:
                continue
            if tool_name in ["execute_python_code", "execute_command"] and "coding" not in self.enabled_plugins:
                continue
            filtered_tools.append(tool)
        
        api_params = {
            "model": self.model,
            "messages": messages_for_api,
            "stream": True,
        }
        
        if not self.skip_tools_and_max_tokens:
            api_params["max_tokens"] = max_tokens
            
            if filtered_tools:
                api_params["tools"] = filtered_tools
            
            if self.is_thinking_model:
                logger.info(f"[LLMWorker] Model '{self.model}' is configured as thinking model (is_thinking_model={self.is_thinking_model})")
                api_params["thinking"] = {"budget_tokens": 4096}
        
        return api_params

    def run(self):
        http_client = None
        try:
            http_client = httpx.Client()
            client = OpenAI(api_key=self.api_key, base_url=self.base_url, http_client=http_client)
            turn_count = 0
            self.state_manager.set_generation_state(GenerationState.PREPARING)
            
            while turn_count < self.max_turns:
                if self._is_stopped:
                    logger.info("[LLMWorker] Stopped by user request")
                    self.state_manager.set_generation_state(GenerationState.STOPPED)
                    self.stopped.emit()
                    return
                    
                turn_count += 1
                self.stream_processor.reset()
                
                settings = QSettings("DoroPet", "Settings")
                max_tokens = settings.value("llm_max_tokens", 8192, type=int)
                
                api_params = self._build_api_params(max_tokens, turn_count)
                
                messages_for_log = api_params.get("messages", [])
                logger.info(f"[LLMWorker] Sending {len(messages_for_log)} messages to API, model={self.model}")
                for i, msg in enumerate(messages_for_log):
                    content = msg.get("content", "")
                    preview = str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
                    logger.debug(f"[LLMWorker] Message[{i}] role={msg.get('role')}: {preview}")
                
                response = client.chat.completions.create(**api_params)
                self._response_iterator = response
                self.state_manager.set_generation_state(GenerationState.STREAMING)
                
                for chunk in response:
                    if self._is_stopped:
                        logger.info("[LLMWorker] Stopped during streaming")
                        self.state_manager.set_generation_state(GenerationState.STOPPED)
                        self.stopped.emit()
                        return
                    
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    self.stream_processor.process_chunk(delta)
                
                full_content, current_turn_content, current_turn_reasoning, tool_calls_buffer = self.stream_processor.finalize()
                
                if current_turn_reasoning:
                    if self.reasoning_accumulated:
                        self.reasoning_accumulated += "\n\n" + current_turn_reasoning
                    else:
                        self.reasoning_accumulated = current_turn_reasoning

                if not tool_calls_buffer:
                    logger.info(f"[LLMWorker] Finished. Total length: {len(full_content)}")
                    logger.info(f"[LLMWorker] Response content: {full_content}")
                    self.finished.emit(full_content, self.reasoning_accumulated, self.tool_calls_accumulated, self.generated_images)
                    break
                
                logger.info(f"[LLMWorker] Tool calls detected: {len(tool_calls_buffer)}")
                
                assistant_msg = {
                    "role": "assistant",
                    "content": current_turn_content if current_turn_content else None,
                    "tool_calls": []
                }
                
                if current_turn_reasoning:
                    assistant_msg["reasoning_content"] = current_turn_reasoning
                
                sorted_indices = sorted(tool_calls_buffer.keys())
                for idx in sorted_indices:
                    assistant_msg["tool_calls"].append(tool_calls_buffer[idx])
                
                self.messages.append(assistant_msg)
                
                for idx in sorted_indices:
                    if self._is_stopped:
                        logger.info("[LLMWorker] Stopped during tool execution")
                        self.state_manager.set_generation_state(GenerationState.STOPPED)
                        self.stopped.emit()
                        return
                    
                    tc_data = tool_calls_buffer[idx]
                    func_name = tc_data["function"]["name"]
                    func_args_str = tc_data["function"]["arguments"]
                    call_id = tc_data["id"]
                    
                    is_skill_call = func_name in self.skill_manager.skills
                    call_type = "skill" if is_skill_call else "tool"
                    
                    if is_skill_call:
                        skill_enabled = f"skill:{func_name}" in self.enabled_plugins
                        if not skill_enabled:
                            logger.warning(f"[LLMWorker] Skill '{func_name}' is disabled, skipping execution")
                            tool_result = json.dumps({"status": "error", "message": f"技能 '{func_name}' 已禁用，请在工具菜单中启用后再使用。"})
                            execution_status = "error"
                            self.tool_calls_accumulated.append({
                                "name": func_name,
                                "type": call_type,
                                "args": func_args_str,
                                "result": tool_result,
                                "status": "error"
                            })
                            self.tool_execution_update.emit(func_name, call_type, "error", func_args_str, tool_result)
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": call_id,
                                "content": tool_result
                            })
                            continue
                    
                    logger.info(f"[LLMWorker] [{call_type.upper()}] Executing {func_name} with args: {func_args_str}")
                    
                    self.tool_status_changed.emit(f"正在调用{'技能' if is_skill_call else '工具'}: {func_name}...")
                    self.tool_execution_update.emit(func_name, call_type, "running", func_args_str, "")
                    
                    # Track for final signal
                    tool_entry = {
                        "name": func_name,
                        "type": call_type,
                        "args": func_args_str,
                        "result": "",
                        "status": "running"
                    }
                    self.tool_calls_accumulated.append(tool_entry)
                    tool_index = len(self.tool_calls_accumulated) - 1
                    
                    tool_result = ""
                    execution_status = "success"
                    try:
                        try:
                            func_args = json.loads(func_args_str)
                        except json.JSONDecodeError as json_err:
                            logger.error(f"[LLMWorker] [{call_type.upper()}] Invalid JSON in tool arguments for {func_name}: {json_err}")
                            logger.error(f"[LLMWorker] [{call_type.upper()}] Raw arguments (truncated): {func_args_str[:500]}...")
                            tool_result = json.dumps({
                                "status": "error", 
                                "message": f"LLM返回的工具参数不完整或格式错误，请重试。错误: {str(json_err)}"
                            })
                            execution_status = "error"
                            
                            self.tool_calls_accumulated[tool_index]["status"] = "error"
                            self.tool_calls_accumulated[tool_index]["result"] = tool_result
                            
                            self.tool_execution_update.emit(func_name, call_type, execution_status, func_args_str, tool_result)
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": call_id,
                                "content": tool_result
                            })
                            continue
                        if func_name in AVAILABLE_TOOLS:
                            func = AVAILABLE_TOOLS[func_name]
                            
                            if func_name == "set_expression":
                                if "expression_name" in func_args:
                                    self.expression_changed.emit(func_args["expression_name"])
                            
                            if func_name == "modify_pet_attribute":
                                interaction = func_args.get("interaction", "")
                                intensity = func_args.get("intensity", "moderate")
                                attribute = func_args.get("attribute", "")
                                action = func_args.get("action", "")
                                
                                if interaction:
                                    self.pet_attribute_changed.emit(interaction, intensity)
                                elif attribute and action:
                                    self.pet_attribute_changed.emit(action, intensity)

                            if func_name == "generate_image":
                                img_base_url = ""
                                img_api_key = ""
                                img_model = "dall-e-3"
                                
                                if self.db:
                                    img_config = self.db.get_active_image_model()
                                    if img_config:
                                        img_base_url = img_config[3]
                                        img_api_key = img_config[4]
                                        img_model = img_config[5]
                                
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
                                
                            if func_name == "list_agent_skills":
                                try:
                                    res_json = json.loads(tool_result)
                                    if res_json.get("status") == "success" and "skills" in res_json:
                                        enabled_skill_names = set(k.replace("skill:", "") for k in self.enabled_plugins if k.startswith("skill:"))
                                        filtered_skills = [s for s in res_json["skills"] if s.get("name") in enabled_skill_names]
                                        res_json["skills"] = filtered_skills
                                        res_json["count"] = len(filtered_skills)
                                        tool_result = json.dumps(res_json, ensure_ascii=False)
                                        logger.info(f"[LLMWorker] Filtered list_agent_skills result: {len(filtered_skills)} enabled skills")
                                except json.JSONDecodeError:
                                    pass
                                
                            if func_name == "generate_image":
                                try:
                                    res_json = json.loads(tool_result)
                                    if res_json.get("status") == "success" and "image_path" in res_json:
                                        self.generated_images.append(res_json["image_path"])
                                except:
                                    pass
                                    
                        elif is_skill_call:
                            logger.info(f"[SkillCall] Executing skill function: {func_name}")
                            tool_result = self.skill_manager.execute_skill(func_name, **func_args)
                            logger.info(f"[SkillCall] Result for {func_name}: {tool_result[:200]}..." if len(tool_result) > 200 else f"[SkillCall] Result for {func_name}: {tool_result}")
                            try:
                                result_data = json.loads(tool_result)
                                if result_data.get("status") == "error":
                                    execution_status = "error"
                                    error_msg = result_data.get("message", "Unknown error")
                                    self.tool_status_changed.emit(f"❌ 技能 {func_name} 执行失败: {error_msg}")
                            except json.JSONDecodeError:
                                pass
                            
                        else:
                            tool_result = json.dumps({"status": "error", "message": "Unknown tool"})
                            execution_status = "error"
                            logger.warning(f"[LLMWorker] Unknown tool called: {func_name}")
                    except Exception as e:
                        logger.error(f"[LLMWorker] [{call_type.upper()}] Execution error for {func_name}: {e}")
                        tool_result = json.dumps({"status": "error", "message": str(e)})
                        execution_status = "error"
                        
                    self.tool_calls_accumulated[tool_index]["status"] = execution_status
                    self.tool_calls_accumulated[tool_index]["result"] = tool_result
                    self.tool_execution_update.emit(func_name, call_type, execution_status, func_args_str, tool_result)
                    
                    logger.info(f"[LLMWorker] Tool result: {tool_result}")
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": tool_result
                    })
                    
            if turn_count >= self.max_turns:
                 logger.warning("[LLMWorker] Max turns reached. Loop finished without explicit break.")
                 pass
                
        except Exception as e:
            logger.error(f"[LLMWorker] Critical Error: {e}")
            self.error.emit(str(e))
        finally:
            if http_client:
                try:
                    http_client.close()
                except:
                    pass

class ImageGenerationWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, model, prompt):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            if "generate_image" in AVAILABLE_TOOLS:
                func = AVAILABLE_TOOLS["generate_image"]
                result = func(None, self.prompt, base_url=self.base_url, api_key=self.api_key, model=self.model)
                self.finished.emit(result)
            else:
                self.error.emit("Image generation tool not available")
        except Exception as e:
            logger.error(f"[ImageGenerationWorker] Error: {e}")
            self.error.emit(str(e))
