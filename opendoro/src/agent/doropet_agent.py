import json
import asyncio
import logging
from typing import Optional, Dict, List, Any, Generator, Callable

from PyQt5.QtCore import QThread, pyqtSignal, QSettings, QMutex, QMutexLocker

from src.agent.core.base import BaseAgent, AgentConfig
from src.agent.core.context import ExecutionContext, ToolCallContext, ToolPermission
from src.agent.core.tool import Tool, ToolRegistry, ToolSchema, ToolCategory, ToolResult
from src.agent.core.lifecycle import AgentState
from src.agent.core.pipeline import ExecutionPipeline, Hook, HookPoint
from src.agent.core.errors import AgentError
from src.agent.core.sandbox import SandboxManager
from src.agent.skills.registry import SkillRegistry
from src.agent.tools import register_all_tools
from src.agent.middleware import create_logging_hook, create_error_logging_hook, create_rate_limit_middleware
from src.provider.manager import ProviderManager
from src.provider.entities import LLMResponse, ToolCall

logger = logging.getLogger("DoroPet.Agent")


class DoroPetAgent(BaseAgent):
    finished = pyqtSignal(str, str, list, list)
    chunk_received = pyqtSignal(str)
    thinking_chunk = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    expression_changed = pyqtSignal(str)
    pet_attribute_changed = pyqtSignal(str, str)
    tool_status_changed = pyqtSignal(str)
    tool_execution_update = pyqtSignal(str, str, str, str, str)
    stopped = pyqtSignal()
    state_changed = pyqtSignal(str, str)

    def __init__(
        self,
        config: AgentConfig,
        api_key: str = "",
        base_url: str = "",
        db=None,
        enabled_plugins: Optional[List[str]] = None,
        available_expressions: Optional[List[str]] = None,
        skip_tools_and_max_tokens: bool = False,
    ):
        super().__init__(config)
        self.api_key = api_key
        self.base_url = base_url
        self.db = db
        self.enabled_plugins = enabled_plugins or ["search", "image", "coding", "file", "expression"]
        self.available_expressions = available_expressions or []
        self.skip_tools_and_max_tokens = skip_tools_and_max_tokens

        self.generated_images: List[str] = []
        self.reasoning_accumulated: str = ""
        self.tool_calls_accumulated: List[Dict] = []

        self._is_stopped = False
        self._stop_mutex = QMutex()
        self._provider_manager = ProviderManager.get_instance()
        self._matched_provider = None
        self._use_provider = self._check_provider()

        self._init_tools()
        self._init_skills()
        self._init_pipeline()

        self.lifecycle.on_transition(self._on_state_transition)

    def _on_state_transition(self, old_state: AgentState, new_state: AgentState):
        self.state_changed.emit(old_state.value, new_state.value)

    def _check_provider(self) -> bool:
        if self.skip_tools_and_max_tokens:
            return False
        try:
            provider = self._provider_manager.get_llm_provider_by_model(self.config.model)
            if provider:
                self._matched_provider = provider
                return True
        except Exception as e:
            logger.debug(f"[DoroPetAgent] Provider not available: {e}")
        return False

    def _init_tools(self):
        registry = ToolRegistry.get_instance()
        if not registry.list_tool_names():
            register_all_tools(registry)

        tool_names = registry.list_tool_names()
        for name in tool_names:
            if name == "set_expression" and "expression" not in self.enabled_plugins:
                continue
            if name == "modify_pet_attribute" and "expression" not in self.enabled_plugins:
                continue
            if name in ("search_baidu", "search_bing", "visit_webpage") and "search" not in self.enabled_plugins:
                continue
            if name == "generate_image" and "image" not in self.enabled_plugins:
                continue
            if name in ("read_file", "write_file", "list_files", "search_files", "edit_file") and "file" not in self.enabled_plugins:
                continue
            if name == "run_python_script" and "coding" not in self.enabled_plugins:
                continue

        sandbox = SandboxManager.get_instance()
        sandbox.update_config(max_execution_time_sec=30.0, max_output_bytes=1024 * 1024)

    def _init_skills(self):
        skill_registry = SkillRegistry.get_instance()
        skill_registry.discover_skills()
        skill_registry._register_skills_as_tools()

    def _init_pipeline(self):
        self.pipeline.add_hook(create_logging_hook(priority=50))
        self.pipeline.add_hook(create_error_logging_hook(priority=50))

        self.pipeline.add_hook(Hook(
            name="state_streaming",
            hook_point=HookPoint.AFTER_TOOL_CALL,
            callback=self._hook_after_tool_call,
            priority=150,
        ))

    def _hook_after_tool_call(self, context, data):
        if isinstance(data, ToolResult):
            if data.tool_name in ("set_expression", "modify_pet_attribute"):
                pass
        return data

    def stop(self):
        with QMutexLocker(self._stop_mutex):
            if self._is_stopped:
                return
            self._is_stopped = True
        super().stop()
        self.stopped.emit()

    def is_stopped(self) -> bool:
        with QMutexLocker(self._stop_mutex):
            return self._is_stopped

    async def _call_llm(
        self, messages: List[Dict], tools: Optional[List[Dict]] = None, **kwargs
    ):
        pass

    async def _call_llm_stream(
        self, messages: List[Dict], tools: Optional[List[Dict]] = None, **kwargs
    ):
        pass

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], context: ExecutionContext) -> ToolResult:
        call_context = ToolCallContext(
            tool_name=tool_name,
            arguments=arguments,
            call_id=f"call_{id(arguments)}",
            session_id=context.session_id,
        )

        self.tool_status_changed.emit(f"正在调用工具: {tool_name}...")
        self.tool_execution_update.emit(tool_name, "tool", "running", json.dumps(arguments, ensure_ascii=False), "")
        self.lifecycle.transition(AgentState.TOOL_CALLING)

        try:
            tool = self.tool_registry.get(tool_name)
            if not tool:
                result = ToolResult(tool_name=tool_name, success=False, error=f"Tool '{tool_name}' not found.")
            else:
                result = tool._wrap_execute(call_context, **arguments)

            status = "success" if result.success else "error"
            result_summary = str(result.data)[:200] if result.data else result.error or ""
            self.tool_execution_update.emit(tool_name, "tool", status, json.dumps(arguments, ensure_ascii=False), result_summary)

            tool_entry = {
                "name": tool_name,
                "type": "tool",
                "args": json.dumps(arguments, ensure_ascii=False),
                "result": result.to_json(),
                "status": status,
            }
            self.tool_calls_accumulated.append(tool_entry)

            if tool_name == "set_expression" and "expression_name" in arguments:
                self.expression_changed.emit(arguments["expression_name"])
            if tool_name == "modify_pet_attribute":
                interaction = arguments.get("interaction", "")
                intensity = arguments.get("intensity", "moderate")
                if interaction:
                    self.pet_attribute_changed.emit(interaction, intensity)

            return result

        except Exception as e:
            logger.error(f"[DoroPetAgent] Tool execution error: {e}")
            error_result = ToolResult(tool_name=tool_name, success=False, error=str(e))
            self.tool_execution_update.emit(tool_name, "tool", "error", json.dumps(arguments, ensure_ascii=False), str(e))
            return error_result

    def sync_execute_tool(self, tool_name: str, arguments: Dict[str, Any], context: ExecutionContext) -> ToolResult:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.execute_tool(tool_name, arguments, context))
                    )
                    return future.result(timeout=60)
            return loop.run_until_complete(self.execute_tool(tool_name, arguments, context))
        except RuntimeError:
            return asyncio.run(self.execute_tool(tool_name, arguments, context))

    def get_agent_schemas(self) -> List[Dict]:
        all_tools = list(self.tool_registry._tools.values())
        filtered = []
        for tool in all_tools:
            name = tool.schema.name
            if name == "set_expression" and "expression" not in self.enabled_plugins:
                continue
            if name == "modify_pet_attribute" and "expression" not in self.enabled_plugins:
                continue
            if name in ("search_baidu", "search_bing", "visit_webpage") and "search" not in self.enabled_plugins:
                continue
            if name == "generate_image" and "image" not in self.enabled_plugins:
                continue
            if name in ("read_file", "write_file", "list_files", "search_files", "edit_file") and "file" not in self.enabled_plugins:
                continue
            if name == "run_python_script" and "coding" not in self.enabled_plugins:
                continue
            filtered.append(tool.schema.to_openai_schema())

        skill_registry = SkillRegistry.get_instance()
        for schema in skill_registry.get_schemas():
            filtered.append(schema)

        return filtered


class AgentBridge:
    _instance: Optional["AgentBridge"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._agent: Optional[DoroPetAgent] = None
        self._registry = ToolRegistry.get_instance()
        self._skill_registry = SkillRegistry.get_instance()

    @classmethod
    def instance(cls) -> "AgentBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_default_tools(self):
        if not self._registry.list_tool_names():
            register_all_tools(self._registry)

    def create_agent(
        self,
        api_key: str = "",
        base_url: str = "",
        messages: List[Dict] = None,
        model: str = "gpt-3.5-turbo",
        db=None,
        is_thinking: bool = False,
        enabled_plugins: List[str] = None,
        available_expressions: List[str] = None,
        skip_tools_and_max_tokens: bool = False,
    ) -> DoroPetAgent:
        config = AgentConfig(
            agent_id=f"doropet_{id(messages)}",
            name="DoroPet",
            description="DoroPet桌面宠物AI助手",
            model=model,
            system_prompt="You are Doro, a helpful desktop pet assistant.",
            max_turns=20,
            max_tokens=8192 if not skip_tools_and_max_tokens else None,
            thinking_budget=4096 if is_thinking else 0,
            tools_enabled=not skip_tools_and_max_tokens,
        )

        self._agent = DoroPetAgent(
            config=config,
            api_key=api_key,
            base_url=base_url,
            db=db,
            enabled_plugins=enabled_plugins,
            available_expressions=available_expressions,
            skip_tools_and_max_tokens=skip_tools_and_max_tokens,
        )

        return self._agent

    def get_agent(self) -> Optional[DoroPetAgent]:
        return self._agent

    def get_tool_schemas(self) -> List[Dict]:
        if self._agent:
            return self._agent.get_agent_schemas()
        return []

    def execute_skill(self, skill_name: str, **kwargs) -> str:
        return self._skill_registry.execute(skill_name, **kwargs)

    def get_skill_descriptions(self) -> Dict[str, str]:
        return self._skill_registry.get_descriptions()

    def get_tool_registry(self) -> ToolRegistry:
        return self._registry

    def get_skill_registry(self) -> SkillRegistry:
        return self._skill_registry
