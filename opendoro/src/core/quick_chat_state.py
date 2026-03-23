from enum import Enum
from typing import List, Dict, Optional, Any, Callable
from PyQt5.QtCore import QObject, pyqtSignal


class GenerationState(Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    STREAMING = "streaming"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class QuickChatErrorType(Enum):
    NONE = ("none", "")
    API_KEY_MISSING = ("api_key_missing", "API Key 未配置，请在模型配置页面设置")
    MODEL_NOT_CONFIGURED = ("model_not_configured", "请先在模型配置页面添加并选择一个有效的模型")
    NETWORK_ERROR = ("network_error", "网络连接失败，请检查网络设置")
    TIMEOUT_ERROR = ("timeout_error", "请求超时，请重试")
    RATE_LIMIT = ("rate_limit", "请求过于频繁，请稍后重试")
    UNKNOWN_ERROR = ("unknown_error", "发生未知错误")


class Message:
    def __init__(
        self,
        msg_id: int,
        role: str,
        content: Any,
        images: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ):
        self.msg_id = msg_id
        self.role = role
        self.content = content
        self.images = images or []
        self.timestamp = timestamp


class QuickChatState(QObject):
    generation_state_changed = pyqtSignal(str)
    messages_changed = pyqtSignal(list)
    tool_states_changed = pyqtSignal(dict)
    session_changed = pyqtSignal(int)
    persona_changed = pyqtSignal(str, str)
    theme_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str, str)
    streaming_content = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._generation_state = GenerationState.IDLE
        self._messages: List[Message] = []
        self._tool_states: Dict[str, bool] = {
            "search": False,
            "image": False,
            "coding": False,
            "file": False
        }
        self._enabled_skills: List[str] = []
        self._session_id: Optional[int] = None
        self._current_persona_name: str = "默认助手"
        self._current_persona_prompt: str = "You are a helpful assistant."
        self._is_dark_theme: bool = True
        self._error_type: QuickChatErrorType = QuickChatErrorType.NONE
        self._error_context: Dict[str, Any] = {}
        self._current_streaming_content: str = ""

    @property
    def generation_state(self) -> GenerationState:
        return self._generation_state

    @generation_state.setter
    def generation_state(self, value: GenerationState):
        if self._generation_state != value:
            self._generation_state = value
            self.generation_state_changed.emit(value.value)

    @property
    def messages(self) -> List[Message]:
        return self._messages

    @messages.setter
    def messages(self, value: List[Message]):
        self._messages = value
        self.messages_changed.emit([self._message_to_dict(m) for m in value])

    @property
    def tool_states(self) -> Dict[str, bool]:
        return self._tool_states.copy()

    @tool_states.setter
    def tool_states(self, value: Dict[str, bool]):
        self._tool_states = value.copy()
        self.tool_states_changed.emit(self._tool_states)

    @property
    def enabled_skills(self) -> List[str]:
        return self._enabled_skills.copy()

    @enabled_skills.setter
    def enabled_skills(self, value: List[str]):
        self._enabled_skills = value.copy()

    @property
    def session_id(self) -> Optional[int]:
        return self._session_id

    @session_id.setter
    def session_id(self, value: int):
        if self._session_id != value:
            self._session_id = value
            self.session_changed.emit(value)

    @property
    def current_persona_name(self) -> str:
        return self._current_persona_name

    @property
    def current_persona_prompt(self) -> str:
        return self._current_persona_prompt

    def set_persona(self, name: str, prompt: str):
        self._current_persona_name = name
        self._current_persona_prompt = prompt
        self.persona_changed.emit(name, prompt)

    @property
    def is_dark_theme(self) -> bool:
        return self._is_dark_theme

    @is_dark_theme.setter
    def is_dark_theme(self, value: bool):
        if self._is_dark_theme != value:
            self._is_dark_theme = value
            self.theme_changed.emit(value)

    @property
    def error_type(self) -> QuickChatErrorType:
        return self._error_type

    def set_error(self, error_type: QuickChatErrorType, context: Dict[str, Any] = None):
        self._error_type = error_type
        self._error_context = context or {}
        if error_type != QuickChatErrorType.NONE:
            self.generation_state = GenerationState.ERROR
            self.error_occurred.emit(error_type.value[0], error_type.value[1])

    def clear_error(self):
        self._error_type = QuickChatErrorType.NONE
        self._error_context = {}

    @property
    def error_context(self) -> Dict[str, Any]:
        return self._error_context.copy()

    @property
    def current_streaming_content(self) -> str:
        return self._current_streaming_content

    @current_streaming_content.setter
    def current_streaming_content(self, value: str):
        self._current_streaming_content = value

    def _message_to_dict(self, msg: Message) -> Dict[str, Any]:
        return {
            "msg_id": msg.msg_id,
            "role": msg.role,
            "content": msg.content,
            "images": msg.images,
            "timestamp": msg.timestamp
        }

    def add_message(self, msg: Message):
        self._messages.append(msg)
        self.messages_changed.emit([self._message_to_dict(m) for m in self._messages])

    def update_message(self, msg_id: int, content: Any):
        for msg in self._messages:
            if msg.msg_id == msg_id:
                msg.content = content
                break
        self.messages_changed.emit([self._message_to_dict(m) for m in self._messages])

    def remove_message(self, msg_id: int):
        self._messages = [m for m in self._messages if m.msg_id != msg_id]
        self.messages_changed.emit([self._message_to_dict(m) for m in self._messages])

    def clear_messages(self):
        self._messages = []
        self.messages_changed.emit([])

    def toggle_tool(self, tool_name: str, enabled: bool):
        self._tool_states[tool_name] = enabled
        self.tool_states_changed.emit(self._tool_states)

    def is_tool_enabled(self, tool_name: str) -> bool:
        return self._tool_states.get(tool_name, False)

    def get_enabled_tools(self) -> List[str]:
        tools = [k for k, v in self._tool_states.items() if v]
        tools.extend(self._enabled_skills)
        return tools

    def reset(self):
        self._generation_state = GenerationState.IDLE
        self._error_type = QuickChatErrorType.NONE
        self._error_context = {}
        self._current_streaming_content = ""


class QuickChatStateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = QuickChatState()
        return cls._instance

    @property
    def state(self) -> QuickChatState:
        return self._state

    def reset(self):
        self._state.reset()


def get_quick_chat_state() -> QuickChatState:
    return QuickChatStateManager().state
