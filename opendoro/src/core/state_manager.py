"""Centralized State Manager for DoroPet application."""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from PyQt5.QtCore import QObject, pyqtSignal


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()


class GenerationState(Enum):
    IDLE = auto()
    PREPARING = auto()
    STREAMING = auto()
    TOOL_CALLING = auto()
    THINKING = auto()
    COMPLETED = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class ChatState:
    current_chat_id: Optional[int] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    generation_state: GenerationState = GenerationState.IDLE
    current_model: Optional[str] = None
    is_thinking_model: bool = False


@dataclass
class LLMState:
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    enabled_plugins: List[str] = field(default_factory=list)
    max_tokens: int = 8192


@dataclass
class UIState:
    theme: str = "light"
    is_generating: bool = False
    current_expression: Optional[str] = None
    input_text: str = ""


class StateManager(QObject):
    chat_changed = pyqtSignal()
    generation_state_changed = pyqtSignal(object)
    connection_state_changed = pyqtSignal(object)
    theme_changed = pyqtSignal(str)
    expression_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    message_added = pyqtSignal(int)
    message_updated = pyqtSignal(int, str)
    generation_completed = pyqtSignal(str, list)
    tool_status_changed = pyqtSignal(str)
    tool_execution_update = pyqtSignal(str, str, str, str, str)
    
    _instance: Optional['StateManager'] = None
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, parent=None):
        if StateManager._initialized:
            return
        super().__init__(parent)
        StateManager._initialized = True
        
        self.chat = ChatState()
        self.llm = LLMState()
        self.ui = UIState()
        
        self._subscribers: Dict[str, List[Callable]] = {}
    
    @classmethod
    def get_instance(cls) -> 'StateManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_chat_id(self, chat_id: Optional[int]):
        if self.chat.current_chat_id != chat_id:
            self.chat.current_chat_id = chat_id
            self.chat.messages = []
            self.chat_changed.emit()
    
    def set_messages(self, messages: List[Dict[str, Any]]):
        self.chat.messages = list(messages)
        self.chat_changed.emit()
    
    def add_message(self, role: str, content: str, msg_id: Optional[int] = None) -> int:
        msg = {"role": role, "content": content}
        self.chat.messages.append(msg)
        if msg_id is not None:
            self.message_added.emit(msg_id)
        return len(self.chat.messages) - 1
    
    def update_last_message(self, content: str, msg_id: Optional[int] = None):
        if self.chat.messages:
            self.chat.messages[-1]["content"] = content
            if msg_id is not None:
                self.message_updated.emit(msg_id, content)
    
    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        return [msg for msg in self.chat.messages if msg.get("content") or msg.get("tool_calls")]
    
    def set_generation_state(self, state: GenerationState):
        old_state = self.chat.generation_state
        self.chat.generation_state = state
        self.ui.is_generating = state in (GenerationState.STREAMING, GenerationState.TOOL_CALLING, GenerationState.THINKING)
        
        if old_state != state:
            self.generation_state_changed.emit(state)
    
    def set_connection_state(self, state: ConnectionState):
        old_state = self.llm.connection_state
        self.llm.connection_state = state
        
        if old_state != state:
            self.connection_state_changed.emit(state)
    
    def set_llm_config(self, api_key: str, base_url: str, model: str, is_thinking: bool = False):
        self.llm.api_key = api_key
        self.llm.base_url = base_url
        self.chat.current_model = model
        self.chat.is_thinking_model = is_thinking
    
    def set_enabled_plugins(self, plugins: List[str]):
        self.llm.enabled_plugins = list(plugins)
    
    def set_theme(self, theme: str):
        if self.ui.theme != theme:
            self.ui.theme = theme
            self.theme_changed.emit(theme)
    
    def set_expression(self, expression: str):
        if self.ui.current_expression != expression:
            self.ui.current_expression = expression
            self.expression_changed.emit(expression)
    
    def emit_error(self, error_msg: str):
        self.error_occurred.emit(error_msg)
    
    def emit_generation_complete(self, content: str, images: List[str]):
        self.set_generation_state(GenerationState.COMPLETED)
        self.generation_completed.emit(content, images)
    
    def emit_tool_status(self, status: str):
        self.tool_status_changed.emit(status)
    
    def emit_tool_execution(self, name: str, call_type: str, status: str, args: str, result: str):
        self.tool_execution_update.emit(name, call_type, status, args, result)
    
    def is_generating(self) -> bool:
        return self.ui.is_generating
    
    def can_start_generation(self) -> bool:
        return (self.chat.generation_state == GenerationState.IDLE or 
                self.chat.generation_state == GenerationState.COMPLETED or
                self.chat.generation_state == GenerationState.ERROR)
    
    def reset_chat(self):
        self.chat.messages = []
        self.chat.generation_state = GenerationState.IDLE
        self.chat_changed.emit()
    
    def subscribe(self, event: str, callback: Callable):
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)
    
    def unsubscribe(self, event: str, callback: Callable):
        if event in self._subscribers:
            if callback in self._subscribers[event]:
                self._subscribers[event].remove(callback)
