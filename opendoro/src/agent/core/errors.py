from typing import Optional, Any


class AgentError(Exception):
    def __init__(self, message: str, code: str = "AGENT_ERROR", detail: Optional[Any] = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)

    def to_dict(self):
        result = {"status": "error", "code": self.code, "message": self.message}
        if self.detail:
            result["detail"] = str(self.detail)
        return result


class ToolError(AgentError):
    def __init__(self, tool_name: str, message: str, code: str = "TOOL_ERROR", detail: Optional[Any] = None):
        self.tool_name = tool_name
        super().__init__(message=f"[{tool_name}] {message}", code=code, detail=detail)


class SandboxError(AgentError):
    def __init__(self, message: str, code: str = "SANDBOX_ERROR", detail: Optional[Any] = None):
        super().__init__(message=message, code=code, detail=detail)


class PermissionError(AgentError):
    def __init__(self, message: str, resource: str = "", code: str = "PERMISSION_DENIED"):
        self.resource = resource
        super().__init__(message=message, code=code)


class RateLimitError(AgentError):
    def __init__(self, message: str, retry_after: float = 0):
        self.retry_after = retry_after
        super().__init__(message=message, code="RATE_LIMITED")


class ConfigurationError(AgentError):
    def __init__(self, message: str, detail: Optional[Any] = None):
        super().__init__(message=message, code="CONFIG_ERROR", detail=detail)
