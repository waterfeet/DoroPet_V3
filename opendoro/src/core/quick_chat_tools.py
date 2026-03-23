from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum

from src.core.logger import logger


class ToolResult:
    def __init__(self, success: bool, content: Any = None, error: str = None):
        self.success = success
        self.content = content
        self.error = error

    def __repr__(self):
        if self.success:
            return f"ToolResult(success=True, content={self.content})"
        else:
            return f"ToolResult(success=False, error={self.error})"


class QuickChatTool(ABC):
    TOOL_TYPE = "base"

    def __init__(self, name: str, display_name: str = None, icon: str = None):
        self._name = name
        self._display_name = display_name or name
        self._icon = icon or "🔧"
        self._enabled = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def tool_type(self) -> str:
        return self.TOOL_TYPE

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self):
        if not self._enabled:
            self._enabled = True
            logger.info(f"[QuickChatTool] 启用工具: {self._name}")

    def disable(self):
        if self._enabled:
            self._enabled = False
            logger.info(f"[QuickChatTool] 禁用工具: {self._name}")

    def toggle(self):
        if self._enabled:
            self.disable()
        else:
            self.enable()

    @abstractmethod
    def execute(self, params: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "display_name": self._display_name,
            "description": self.__doc__ or "",
            "parameters": {}
        }


class QuickChatToolRegistry:
    _tools: Dict[str, QuickChatTool] = {}
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, tool: QuickChatTool) -> bool:
        if tool.name in cls._tools:
            logger.warning(f"[QuickChatToolRegistry] 工具已存在: {tool.name}")
            return False

        cls._tools[tool.name] = tool
        logger.info(f"[QuickChatToolRegistry] 注册工具: {tool.name}")
        return True

    @classmethod
    def unregister(cls, tool_name: str) -> bool:
        if tool_name not in cls._tools:
            logger.warning(f"[QuickChatToolRegistry] 工具不存在: {tool_name}")
            return False

        del cls._tools[tool_name]
        logger.info(f"[QuickChatToolRegistry] 注销工具: {tool_name}")
        return True

    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[QuickChatTool]:
        return cls._tools.get(tool_name)

    @classmethod
    def get_all_tools(cls) -> List[QuickChatTool]:
        return list(cls._tools.values())

    @classmethod
    def get_enabled_tools(cls) -> List[QuickChatTool]:
        return [t for t in cls._tools.values() if t.enabled]

    @classmethod
    def get_tool_names(cls) -> List[str]:
        return list(cls._tools.keys())

    @classmethod
    def enable_tool(cls, tool_name: str) -> bool:
        tool = cls.get_tool(tool_name)
        if tool:
            tool.enable()
            return True
        return False

    @classmethod
    def disable_tool(cls, tool_name: str) -> bool:
        tool = cls.get_tool(tool_name)
        if tool:
            tool.disable()
            return True
        return False

    @classmethod
    def toggle_tool(cls, tool_name: str) -> bool:
        tool = cls.get_tool(tool_name)
        if tool:
            tool.toggle()
            return True
        return False

    @classmethod
    def is_tool_enabled(cls, tool_name: str) -> bool:
        tool = cls.get_tool(tool_name)
        return tool.enabled if tool else False

    @classmethod
    def clear(cls):
        cls._tools.clear()
        logger.info("[QuickChatToolRegistry] 清空所有工具")

    @classmethod
    def initialize_builtins(cls):
        from src.tools.search_tool import SearchTool
        from src.tools.image_tool import ImageTool
        from src.tools.coding_tool import CodingTool
        from src.tools.file_tool import FileTool

        builtins = [
            SearchTool(),
            ImageTool(),
            CodingTool(),
            FileTool()
        ]

        for tool in builtins:
            cls.register(tool)


class QuickChatToolManager:
    def __init__(self, state_manager=None):
        self._registry = QuickChatToolRegistry
        self._state_manager = state_manager

    def toggle_tool(self, tool_name: str, enabled: bool) -> bool:
        if enabled:
            result = self._registry.enable_tool(tool_name)
        else:
            result = self._registry.disable_tool(tool_name)

        if result and self._state_manager:
            self._state_manager.toggle_tool(tool_name, enabled)

        return result

    def get_enabled_tools(self) -> List[str]:
        enabled_tools = self._registry.get_enabled_tools()
        return [t.name for t in enabled_tools]

    def is_tool_enabled(self, tool_name: str) -> bool:
        return self._registry.is_tool_enabled(tool_name)

    def get_all_tools(self) -> List[QuickChatTool]:
        return self._registry.get_all_tools()

    def execute_tool(self, tool_name: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        tool = self._registry.get_tool(tool_name)
        if not tool:
            return ToolResult(False, error=f"工具不存在: {tool_name}")

        if not tool.enabled:
            return ToolResult(False, error=f"工具未启用: {tool_name}")

        return tool.execute(params, context)

    def initialize_builtins(self):
        self._registry.initialize_builtins()


def get_tool_registry() -> type:
    return QuickChatToolRegistry
