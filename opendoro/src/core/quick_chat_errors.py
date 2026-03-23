from enum import Enum
from typing import Optional, Callable, Any, Dict
from PyQt5.QtCore import QObject, pyqtSignal

from src.core.logger import logger


class ErrorSeverity(Enum):
    BLOCKING = "blocking"
    RETRYABLE = "retryable"
    WARNING = "warning"
    FATAL = "fatal"


class QuickChatErrorType(Enum):
    NONE = ("none", "")
    API_KEY_MISSING = ("api_key_missing", "API Key 未配置，请在模型配置页面设置")
    API_KEY_INVALID = ("api_key_invalid", "API Key 无效或已过期")
    MODEL_NOT_CONFIGURED = ("model_not_configured", "请先在模型配置页面添加并选择一个有效的模型")
    NETWORK_ERROR = ("network_error", "网络连接失败，请检查网络设置")
    TIMEOUT_ERROR = ("timeout_error", "请求超时，请重试")
    RATE_LIMIT = ("rate_limit", "请求过于频繁，请稍后重试")
    UNKNOWN_ERROR = ("unknown_error", "发生未知错误")


class QuickChatError(Exception):
    def __init__(self, error_type: 'QuickChatErrorType', message: str = None, context: Dict[str, Any] = None):
        self.error_type = error_type
        self.message = message or error_type.value[1]
        self.context = context or {}
        super().__init__(self.message)

    @property
    def severity(self) -> ErrorSeverity:
        if self.error_type == QuickChatErrorType.NONE:
            return ErrorSeverity.WARNING
        elif self.error_type in (
            QuickChatErrorType.API_KEY_MISSING,
            QuickChatErrorType.MODEL_NOT_CONFIGURED
        ):
            return ErrorSeverity.BLOCKING
        elif self.error_type in (
            QuickChatErrorType.NETWORK_ERROR,
            QuickChatErrorType.TIMEOUT_ERROR,
            QuickChatErrorType.RATE_LIMIT
        ):
            return ErrorSeverity.RETRYABLE
        else:
            return ErrorSeverity.FATAL

    @property
    def is_retryable(self) -> bool:
        return self.severity == ErrorSeverity.RETRYABLE


class ErrorHandler(QObject):
    error_handled = pyqtSignal(str, str)
    retry_requested = pyqtSignal(object)
    show_message = pyqtSignal(str, str, bool)

    def __init__(self, state_manager=None):
        super().__init__()
        self._state_manager = state_manager
        self._last_error: Optional[QuickChatError] = None
        self._retry_callback: Optional[Callable] = None

    def set_state_manager(self, state_manager):
        self._state_manager = state_manager

    def handle_error(self, error: QuickChatError, retry_callback: Callable = None):
        self._last_error = error
        self._retry_callback = retry_callback

        logger.error(f"[ErrorHandler] 处理错误: {error.error_type.value[0]} - {error.message}")

        if error.severity == ErrorSeverity.RETRYABLE:
            self._handle_retryable_error(error)
        elif error.severity == ErrorSeverity.BLOCKING:
            self._handle_blocking_error(error)
        elif error.severity == ErrorSeverity.FATAL:
            self._handle_fatal_error(error)
        else:
            self._handle_warning_error(error)

    def _handle_retryable_error(self, error: QuickChatError):
        self._state_manager.set_error(error.error_type, error.context) if self._state_manager else None
        self.error_handled.emit(error.error_type.value[0], error.message)

        if self._retry_callback:
            self.show_message.emit(
                "操作失败",
                f"{error.message}\n\n是否重试？",
                True
            )

    def _handle_blocking_error(self, error: QuickChatError):
        self._state_manager.set_error(error.error_type, error.context) if self._state_manager else None
        self.error_handled.emit(error.error_type.value[0], error.message)
        self.show_message.emit(
            "配置问题",
            error.message,
            False
        )

    def _handle_fatal_error(self, error: QuickChatError):
        self._state_manager.set_error(error.error_type, error.context) if self._state_manager else None
        self.error_handled.emit(error.error_type.value[0], error.message)
        self.show_message.emit(
            "严重错误",
            f"{error.message}\n\n请检查日志了解详情。",
            False
        )

    def _handle_warning_error(self, error: QuickChatError):
        self.error_handled.emit(error.error_type.value[0], error.message)
        self.show_message.emit(
            "提示",
            error.message,
            False
        )

    def retry(self):
        if self._retry_callback and self._last_error and self._last_error.is_retryable:
            logger.info("[ErrorHandler] 重试请求")
            self.retry_requested.emit(self._last_error)
            self._last_error = None
            self._retry_callback = None

    @property
    def last_error(self) -> Optional[QuickChatError]:
        return self._last_error


class ErrorClassifier:
    @staticmethod
    def classify_error(error: Exception) -> 'QuickChatErrorType':
        error_str = str(error).lower()

        if "api key" in error_str or "auth" in error_str or "401" in error_str:
            if "missing" in error_str or "not found" in error_str:
                return QuickChatErrorType.API_KEY_MISSING
            return QuickChatErrorType.API_KEY_INVALID

        if "model" in error_str and ("not found" in error_str or "not exist" in error_str or "does not exist" in error_str):
            return QuickChatErrorType.MODEL_NOT_CONFIGURED

        if "timeout" in error_str or "timed out" in error_str:
            return QuickChatErrorType.TIMEOUT_ERROR

        if "network" in error_str or "connection" in error_str or "dns" in error_str:
            return QuickChatErrorType.NETWORK_ERROR

        if "rate limit" in error_str or "too many requests" in error_str or "429" in error_str:
            return QuickChatErrorType.RATE_LIMIT

        return QuickChatErrorType.UNKNOWN_ERROR


def create_error_from_exception(error: Exception, context: Dict[str, Any] = None) -> QuickChatError:
    error_type = ErrorClassifier.classify_error(error)
    return QuickChatError(error_type, str(error), context)
