from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
import time


class ToolPermission(Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    EXECUTE = "execute"
    NETWORK = "network"
    ADMIN = "admin"


@dataclass
class ExecutionContext:
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    role: str = "default"
    permissions: Set[ToolPermission] = field(default_factory=lambda: {ToolPermission.READ_ONLY})
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    tool_call_history: List[ToolCallContext] = field(default_factory=list)

    def has_permission(self, required: List[ToolPermission]) -> bool:
        if not required:
            return True
        for perm in required:
            if perm not in self.permissions:
                return False
        return True

    def add_tool_call(self, call: "ToolCallContext"):
        self.tool_call_history.append(call)

    def get_recent_tool_calls(self, count: int = 10) -> List["ToolCallContext"]:
        return self.tool_call_history[-count:]

    def get_total_tool_calls(self) -> int:
        return len(self.tool_call_history)

    def clone(self, **overrides) -> "ExecutionContext":
        data = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "permissions": set(self.permissions),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "tool_call_history": list(self.tool_call_history),
        }
        data.update(overrides)
        return ExecutionContext(**data)


@dataclass
class ToolCallContext:
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str
    session_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "pending"
    result_summary: Optional[str] = None

    def mark_completed(self, success: bool, summary: str = ""):
        self.completed_at = time.time()
        self.status = "success" if success else "error"
        self.result_summary = summary

    def mark_running(self):
        self.status = "running"

    def is_expired(self, timeout_ms: int) -> bool:
        if self.completed_at:
            return False
        elapsed = (time.time() - self.started_at) * 1000
        return elapsed > timeout_ms

    def check_timeout(self, timeout_ms: int):
        if self.is_expired(timeout_ms):
            raise TimeoutError(
                f"Tool '{self.tool_name}' timed out after {timeout_ms}ms"
            )

    def duration_ms(self) -> float:
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "call_id": self.call_id,
            "status": self.status,
            "duration_ms": round(self.duration_ms(), 2),
            "result_summary": self.result_summary,
        }
