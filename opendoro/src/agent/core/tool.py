import abc
import json
import time
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Type, Union

from src.agent.core.errors import ToolError, PermissionError as AgentPermissionError
from src.agent.core.context import ExecutionContext, ToolCallContext, ToolPermission

logger = logging.getLogger("DoroPet.Agent")


class ToolCategory(Enum):
    FILE_SYSTEM = "file_system"
    SEARCH = "search"
    IMAGE = "image"
    CODE_EXECUTION = "code_execution"
    PET = "pet"
    SKILL = "skill"
    SYSTEM = "system"
    NETWORK = "network"
    CUSTOM = "custom"


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any]
    category: ToolCategory = ToolCategory.CUSTOM
    required_permissions: List[ToolPermission] = field(default_factory=list)
    version: str = "1.0.0"
    timeout_ms: int = 30000
    max_output_chars: int = 100000
    tags: List[str] = field(default_factory=list)

    def to_openai_schema(self) -> Dict:
        params = dict(self.parameters)
        if "additionalProperties" not in params:
            params["additionalProperties"] = False
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    metadata: Dict = field(default_factory=dict)

    def to_json(self) -> str:
        payload = {
            "status": "success" if self.success else "error",
            "tool": self.tool_name,
            "duration_ms": round(self.duration_ms, 2),
        }
        if self.success:
            payload["data"] = self.data
        else:
            payload["message"] = self.error
        if self.metadata:
            payload["metadata"] = self.metadata
        return json.dumps(payload, ensure_ascii=False, default=str)

    def to_message_content(self) -> str:
        return self.to_json()


class Tool(abc.ABC):

    schema: ToolSchema = None

    def __init__(self, schema: Optional[ToolSchema] = None):
        if schema is not None:
            self.schema = schema
        elif self.__class__.schema is not None:
            self.schema = self.__class__.schema
        else:
            raise ToolError(self.__class__.__name__, "Tool must define a schema (class-level or constructor arg).")
        self._call_count = 0
        self._total_duration_ms = 0.0

    @abc.abstractmethod
    async def execute(self, context: ToolCallContext, **kwargs) -> ToolResult:
        pass

    def execute_sync(self, context: ToolCallContext, **kwargs) -> ToolResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.execute(context, **kwargs))
                    )
                    return future.result(timeout=self.schema.timeout_ms / 1000.0)
            else:
                return loop.run_until_complete(self.execute(context, **kwargs))
        except RuntimeError:
            return asyncio.run(self.execute(context, **kwargs))

    def _wrap_execute(self, context: ToolCallContext, **kwargs) -> ToolResult:
        start = time.time()
        self._call_count += 1
        try:
            if not context.has_permission(self.schema.required_permissions):
                raise AgentPermissionError(
                    f"Missing permissions: {self.schema.required_permissions}",
                    resource=self.schema.name,
                )

            context.check_timeout(self.schema.timeout_ms)

            result = asyncio.run(self.execute(context, **kwargs))

            if result.data is not None:
                result_data_str = str(result.data)
                if len(result_data_str) > self.schema.max_output_chars:
                    result.data = (
                        result_data_str[: self.schema.max_output_chars]
                        + f"\n...[truncated, total {len(result_data_str)} chars]"
                    )

            result.tool_name = self.schema.name
            result.duration_ms = (time.time() - start) * 1000
            self._total_duration_ms += result.duration_ms
            return result

        except AgentPermissionError:
            raise
        except ToolError:
            raise
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"[Tool:{self.schema.name}] Execution failed: {e}")
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=str(e),
                duration_ms=duration,
            )

    def get_stats(self) -> Dict:
        return {
            "tool_name": self.schema.name,
            "call_count": self._call_count,
            "total_duration_ms": round(self._total_duration_ms, 2),
            "avg_duration_ms": round(self._total_duration_ms / max(self._call_count, 1), 2),
        }

    def __repr__(self):
        return f"Tool(name={self.schema.name}, category={self.schema.category.value})"


class ToolRegistry:
    _instance: Optional["ToolRegistry"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ToolRegistry._initialized:
            return
        ToolRegistry._initialized = True
        self._tools: Dict[str, Tool] = {}
        self._by_category: Dict[ToolCategory, List[str]] = {}
        for cat in ToolCategory:
            self._by_category[cat] = []

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: Tool) -> None:
        name = tool.schema.name
        if name in self._tools:
            logger.warning(f"[ToolRegistry] Overwriting tool: {name}")
        self._tools[name] = tool
        category = tool.schema.category
        if name not in self._by_category[category]:
            self._by_category[category].append(name)
        logger.info(f"[ToolRegistry] Registered tool: {name} (category={category.value})")

    def unregister(self, tool_name: str) -> bool:
        if tool_name not in self._tools:
            return False
        tool = self._tools.pop(tool_name)
        category = tool.schema.category
        if tool_name in self._by_category[category]:
            self._by_category[category].remove(tool_name)
        logger.info(f"[ToolRegistry] Unregistered tool: {tool_name}")
        return True

    def get(self, tool_name: str) -> Optional[Tool]:
        return self._tools.get(tool_name)

    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        return [self._tools[name] for name in self._by_category.get(category, []) if name in self._tools]

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_schemas(self, categories: Optional[List[ToolCategory]] = None) -> List[Dict]:
        if categories is None:
            tools = list(self._tools.values())
        else:
            tools = []
            for cat in categories:
                tools.extend(self.get_by_category(cat))
        return [t.schema.to_openai_schema() for t in tools]

    def find_tool(self, tool_name: str) -> Optional[Tool]:
        return self._tools.get(tool_name)

    def clear(self):
        self._tools.clear()
        for cat in ToolCategory:
            self._by_category[cat] = []
        logger.info("[ToolRegistry] Cleared all tools")

    async def execute_sync(self, tool_name: str, context: ToolCallContext, **kwargs) -> ToolResult:
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found in registry.",
            )
        return tool._wrap_execute(context, **kwargs)


import asyncio
