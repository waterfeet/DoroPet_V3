import json
import base64
import httpx
import time
import copy
import threading
from PyQt5.QtCore import QThread, pyqtSignal, QSettings, QMutex, QMutexLocker
from src.core.agent_tools import TOOLS_SCHEMA, AVAILABLE_TOOLS
from src.core.logger import logger
from src.core.skill_manager import SkillManager
from src.core.stream_processor import StreamProcessor
from src.core.state_manager import StateManager, GenerationState
from src.provider.manager import ProviderManager
from src.provider.entities import LLMResponse, ToolCall


def _truncate_content_for_log(content, max_length=500):
    if not content:
        return content
    if len(content) <= max_length:
        return content
    if 'data:image' in content:
        truncated = content[:max_length]
        truncated += f"\n...[图片数据已省略，原始长度: {len(content)} 字符]..."
        return truncated
    return content[:max_length] + "..."


class LLMWorker(QThread):
    finished = pyqtSignal(str, str, list, list)
    chunk_received = pyqtSignal(str)
    thinking_chunk = pyqtSignal(str)
    error = pyqtSignal(str)
    expression_changed = pyqtSignal(str)
    pet_attribute_changed = pyqtSignal(str, str)
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
        self._stop_mutex = QMutex()
        self._response_iterator = None
        self._http_client = None
        self._provider_stream = None
        self.stream_processor = StreamProcessor()
        self.stream_processor.chunk_ready.connect(self.chunk_received.emit)
        self.stream_processor.thinking_chunk.connect(self.thinking_chunk.emit)
        self.state_manager = StateManager.get_instance()
        
        self._provider_manager = ProviderManager.get_instance()
        self._use_provider_framework = self._check_provider_framework()
        
    def _check_provider_framework(self) -> bool:
        if self.skip_tools_and_max_tokens:
            logger.info(f"[LLMWorker] skip_tools_and_max_tokens=True, using legacy mode for vision model: {self.model}")
            return False
        
        self._matched_provider = None
        
        try:
            provider = self._provider_manager.get_llm_provider_by_model(self.model)
            if provider:
                self._matched_provider = provider
                logger.info(f"[LLMWorker] Using provider framework with: {provider.meta().type} (model={provider.meta().model})")
                return True
            else:
                logger.info(f"[LLMWorker] No provider found for model={self.model}, using legacy mode")
        except Exception as e:
            logger.debug(f"[LLMWorker] Provider framework not available, using legacy mode: {e}")
        return False

    def stop(self):
        with QMutexLocker(self._stop_mutex):
            if self._is_stopped:
                return
            self._is_stopped = True
            logger.info("[LLMWorker] Stop requested")
        
        self.stream_processor.stop()
        logger.debug("[LLMWorker] Stop flag set, waiting for worker to exit gracefully")
    
    def is_stopped(self) -> bool:
        with QMutexLocker(self._stop_mutex):
            return self._is_stopped

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
            if tool_name in ["search_baidu", "search_bing", "visit_webpage", "zhipu_web_search", "zhipu_web_read"] and "search" not in self.enabled_plugins:
                continue
            if tool_name == "generate_image" and "image" not in self.enabled_plugins:
                continue
            if tool_name in ["read_file", "write_file", "list_files", "search_files", "edit_file", "insert_at_line", "delete_lines", "find_in_file"] and "file" not in self.enabled_plugins:
                continue
            if tool_name in ["execute_python_code", "execute_command"] and "coding" not in self.enabled_plugins:
                continue
            filtered_tools.append(tool)
        
        skill_schemas = self.skill_manager.get_tool_schemas()
        filtered_tools.extend(skill_schemas)
        
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
        was_stopped = False
        try:
            if self._use_provider_framework:
                self._run_with_provider()
            else:
                self._run_legacy()
                
        except Exception as e:
            logger.error(f"[LLMWorker] Critical Error: {e}")
            if not self.is_stopped():
                self.error.emit(str(e))
        finally:
            was_stopped = self.is_stopped()
            self._cleanup_resources()
        
        try:
            if was_stopped:
                self.state_manager.set_generation_state(GenerationState.STOPPED)
                self.stopped.emit()
            else:
                self.state_manager.set_generation_state(GenerationState.COMPLETED)
        except RuntimeError:
            pass
    
    def _cleanup_resources(self):
        if self._http_client:
            try:
                self._http_client.close()
            except:
                pass
            self._http_client = None
        
        self._response_iterator = None
        self._provider_stream = None

    def _run_with_provider(self):
        provider = self._matched_provider
        if not provider:
            logger.warning("[LLMWorker] No matched provider, falling back to legacy mode")
            self._run_legacy()
            return
        
        provider_meta = provider.meta()
        logger.info(f"[LLMWorker] Using provider: id={provider_meta.id}, type={provider_meta.type}, model={provider_meta.model}")
        
        turn_count = 0
        self.state_manager.set_generation_state(GenerationState.PREPARING)
        
        while turn_count < self.max_turns:
            if self.is_stopped():
                logger.info("[LLMWorker] Stopped by user request")
                return
                
            turn_count += 1
            self.stream_processor.reset()
            
            settings = QSettings("DoroPet", "Settings")
            max_tokens = settings.value("llm_max_tokens", 8192, type=int)
            
            api_params = self._build_api_params(max_tokens, turn_count)
            messages_for_api = api_params.get("messages", [])
            tools = api_params.get("tools")
            
            logger.info(f"[LLMWorker] Sending {len(messages_for_api)} messages via provider, model={self.model}")
            
            self.state_manager.set_generation_state(GenerationState.STREAMING)
            
            full_content = ""
            current_turn_content = ""
            current_turn_reasoning = ""
            tool_calls_buffer = {}
            
            try:
                stream = provider.chat_stream(
                    messages=messages_for_api,
                    tools=tools,
                    max_tokens=max_tokens if not self.skip_tools_and_max_tokens else None,
                    thinking_budget=4096 if self.is_thinking_model else None
                )
                self._provider_stream = stream
                
                for response in stream:
                    if self.is_stopped():
                        logger.debug("[LLMWorker] Stopped during streaming")
                        break
                    
                    if response.content:
                        current_turn_content += response.content
                        full_content += response.content
                        self.chunk_received.emit(response.content)
                    
                    if response.reasoning:
                        current_turn_reasoning += response.reasoning
                        self.thinking_chunk.emit(response.reasoning)
                    
                    for tc in response.tool_calls:
                        tc_index = tc.index if tc.index is not None else 0
                        tc_key = f"idx_{tc_index}"
                        
                        # logger.info(f"[LLMWorker] Tool call chunk: key={tc_key}, id={tc.id}, name={tc.name}, args_len={len(tc.arguments) if tc.arguments else 0}")
                        
                        if tc_key not in tool_calls_buffer:
                            tool_calls_buffer[tc_key] = {
                                "id": tc.id or f"call_{tc_index}",
                                "index": tc_index,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": tc.arguments
                                }
                            }
                        else:
                            if tc.id:
                                tool_calls_buffer[tc_key]["id"] = tc.id
                            if tc.name and not tool_calls_buffer[tc_key]["function"]["name"]:
                                tool_calls_buffer[tc_key]["function"]["name"] = tc.name
                            if tc.arguments:
                                tool_calls_buffer[tc_key]["function"]["arguments"] += tc.arguments
                
            except StopIteration:
                logger.debug("[LLMWorker] Stream stopped by user")
                return
            except GeneratorExit:
                logger.debug("[LLMWorker] Generator closed by user")
                return
            except Exception as e:
                if self.is_stopped():
                    logger.debug("[LLMWorker] Stopped during streaming (exception)")
                    return
                logger.error(f"[LLMWorker] Provider streaming error: {e}")
                self.error.emit(str(e))
                return
            finally:
                self._provider_stream = None
            
            if self.is_stopped():
                logger.debug("[LLMWorker] Processing stop state after streaming")
                return
            
            if current_turn_reasoning:
                if self.reasoning_accumulated:
                    self.reasoning_accumulated += "\n\n" + current_turn_reasoning
                else:
                    self.reasoning_accumulated = current_turn_reasoning

            if not tool_calls_buffer:
                logger.info(f"[LLMWorker] Finished. Total length: {len(full_content)}")
                logger.debug(f"[LLMWorker] Response content: {_truncate_content_for_log(full_content)}")
                self.finished.emit(full_content, self.reasoning_accumulated, self.tool_calls_accumulated, self.generated_images)
                break
            
            logger.info(f"[LLMWorker] Tool calls detected: {len(tool_calls_buffer)} via provider id={provider_meta.id}, model={provider_meta.model}")
            
            assistant_msg = {
                "role": "assistant",
                "tool_calls": []
            }
            
            if current_turn_content:
                assistant_msg["content"] = current_turn_content
            
            if current_turn_reasoning:
                assistant_msg["reasoning_content"] = current_turn_reasoning
            
            sorted_indices = sorted(tool_calls_buffer.keys())
            for idx in sorted_indices:
                assistant_msg["tool_calls"].append(tool_calls_buffer[idx])
            
            self.messages.append(assistant_msg)
            
            self._execute_tool_calls(sorted_indices, tool_calls_buffer)
            
        if turn_count >= self.max_turns:
            logger.warning("[LLMWorker] Max turns reached. Loop finished without explicit break.")

    def _run_legacy(self):
        logger.info(f"[LLMWorker] Using legacy mode: base_url={self.base_url}, model={self.model}")
        self._http_client = httpx.Client()
        
        api_key_for_client = self.api_key
        if not api_key_for_client or api_key_for_client.strip() == "":
            if "ollama" in self.base_url.lower() or "localhost:11434" in self.base_url:
                api_key_for_client = "ollama"
                logger.debug("[LLMWorker] Using placeholder API key for Ollama")
        
        client = OpenAI(api_key=api_key_for_client, base_url=self.base_url, http_client=self._http_client)
        turn_count = 0
        self.state_manager.set_generation_state(GenerationState.PREPARING)
        
        while turn_count < self.max_turns:
            if self.is_stopped():
                logger.info("[LLMWorker] Stopped by user request")
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
            
            try:
                response = client.chat.completions.create(**api_params)
                self._response_iterator = response
                self.state_manager.set_generation_state(GenerationState.STREAMING)
                
                for chunk in response:
                    if self.is_stopped():
                        logger.debug("[LLMWorker] Stopped during streaming")
                        return
                    
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    self.stream_processor.process_chunk(delta)
                
            except StopIteration:
                logger.debug("[LLMWorker] Stream stopped by user")
                return
            except GeneratorExit:
                logger.debug("[LLMWorker] Generator closed by user")
                return
            except Exception as e:
                if self.is_stopped():
                    logger.debug("[LLMWorker] Stopped during streaming (exception)")
                    return
                logger.error(f"[LLMWorker] Legacy streaming error: {e}")
                self.error.emit(str(e))
                return
            finally:
                self._response_iterator = None
            
            if self.is_stopped():
                logger.debug("[LLMWorker] Processing stop state after streaming")
                return
            
            full_content, current_turn_content, current_turn_reasoning, tool_calls_buffer = self.stream_processor.finalize()
            
            if current_turn_reasoning:
                if self.reasoning_accumulated:
                    self.reasoning_accumulated += "\n\n" + current_turn_reasoning
                else:
                    self.reasoning_accumulated = current_turn_reasoning

            if not tool_calls_buffer:
                logger.info(f"[LLMWorker] Finished. Total length: {len(full_content)}")
                logger.debug(f"[LLMWorker] Response content: {_truncate_content_for_log(full_content)}")
                self.finished.emit(full_content, self.reasoning_accumulated, self.tool_calls_accumulated, self.generated_images)
                break
            
            logger.info(f"[LLMWorker] Tool calls detected: {len(tool_calls_buffer)} (legacy mode, model={self.model})")
            
            assistant_msg = {
                "role": "assistant",
                "tool_calls": []
            }
            
            if current_turn_content:
                assistant_msg["content"] = current_turn_content
            
            if current_turn_reasoning:
                assistant_msg["reasoning_content"] = current_turn_reasoning
            
            sorted_indices = sorted(tool_calls_buffer.keys())
            for idx in sorted_indices:
                assistant_msg["tool_calls"].append(tool_calls_buffer[idx])
            
            self.messages.append(assistant_msg)
            
            self._execute_tool_calls(sorted_indices, tool_calls_buffer)
            
        if turn_count >= self.max_turns:
            logger.warning("[LLMWorker] Max turns reached. Loop finished without explicit break.")

    def _execute_tool_calls(self, sorted_indices, tool_calls_buffer):
        for idx in sorted_indices:
            if self.is_stopped():
                logger.debug("[LLMWorker] Stopped during tool execution")
                return
            
            tc_data = tool_calls_buffer[idx]
            func_name = tc_data["function"]["name"]
            func_args_str = tc_data["function"]["arguments"]
            call_id = tc_data["id"]
            
            is_skill_call = func_name in self.skill_manager.skills
            call_type = "skill" if is_skill_call else "tool"
            
            if is_skill_call:
                skill_enabled = True
                try:
                    from src.agent.skills.state import SkillEnabledState
                    state = SkillEnabledState.get_instance()
                    skill_enabled = state.is_enabled(func_name)
                except ImportError:
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
            
            logger.debug(f"[LLMWorker] [{call_type.upper()}] Executing {func_name} with args: {func_args_str} (provider model: {self.model})")
            
            self.tool_status_changed.emit(f"正在调用{'技能' if is_skill_call else '工具'}: {func_name}...")
            self.tool_execution_update.emit(func_name, call_type, "running", func_args_str, "")
            
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
                agent_result = None
                try:
                    from src.core.agent_tools import execute_tool_via_agent, is_new_agent_available
                    if is_new_agent_available():
                        agent_result = execute_tool_via_agent(func_name, func_args)
                except Exception:
                    pass

                if agent_result is not None:
                    tool_result = agent_result
                    try:
                        res_json = json.loads(tool_result)
                        if func_name == "generate_image" and res_json.get("status") == "success":
                            data = res_json.get("data", {})
                            image_path = data.get("image_path") if isinstance(data, dict) else res_json.get("image_path")
                            if image_path:
                                self.generated_images.append(image_path)
                    except json.JSONDecodeError:
                        pass

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

                elif func_name in AVAILABLE_TOOLS:
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
                        img_provider = self._provider_manager.get_image_provider()
                        if img_provider:
                            try:
                                img_response = img_provider.generate(
                                    prompt=func_args.get("prompt", ""),
                                    size=func_args.get("size", "1024x1024"),
                                    quality=func_args.get("quality", "standard")
                                )
                                if img_response.image_path:
                                    tool_result = json.dumps({
                                        "status": "success",
                                        "image_path": img_response.image_path,
                                        "revised_prompt": img_response.revised_prompt
                                    })
                                    self.generated_images.append(img_response.image_path)
                                else:
                                    tool_result = json.dumps({"status": "error", "message": "Image generation failed"})
                            except Exception as e:
                                tool_result = json.dumps({"status": "error", "message": str(e)})
                        else:
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
                                None, 
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
                                logger.debug(f"[LLMWorker] Filtered list_agent_skills result: {len(filtered_skills)} enabled skills")
                        except json.JSONDecodeError:
                            pass
                        
                    if func_name == "generate_image" and not img_provider:
                        try:
                            res_json = json.loads(tool_result)
                            if res_json.get("status") == "success" and "image_path" in res_json:
                                self.generated_images.append(res_json["image_path"])
                        except:
                            pass
                            
                elif is_skill_call:
                    logger.info(f"[SkillCall] Executing skill function: {func_name}")
                    tool_result = self.skill_manager.execute_skill(func_name, **func_args)
                    logger.debug(f"[SkillCall] Result for {func_name}: {tool_result[:200]}..." if len(tool_result) > 200 else f"[SkillCall] Result for {func_name}: {tool_result}")
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
            
            logger.debug(f"[LLMWorker] Tool result: {tool_result}")
            self.messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_result
            })

from openai import OpenAI


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
            provider_manager = ProviderManager.get_instance()
            img_provider = provider_manager.get_image_provider()
            
            if img_provider:
                response = img_provider.generate(prompt=self.prompt, model=self.model)
                if response.image_path:
                    result = json.dumps({
                        "status": "success",
                        "image_path": response.image_path,
                        "revised_prompt": response.revised_prompt
                    })
                else:
                    result = json.dumps({"status": "error", "message": "Image generation failed"})
                self.finished.emit(result)
            elif "generate_image" in AVAILABLE_TOOLS:
                func = AVAILABLE_TOOLS["generate_image"]
                result = func(None, self.prompt, base_url=self.base_url, api_key=self.api_key, model=self.model)
                self.finished.emit(result)
            else:
                self.error.emit("Image generation tool not available")
        except Exception as e:
            logger.error(f"[ImageGenerationWorker] Error: {e}")
            self.error.emit(str(e))
