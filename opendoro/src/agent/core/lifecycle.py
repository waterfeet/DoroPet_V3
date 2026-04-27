from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Callable, List
import time
import logging

logger = logging.getLogger("DoroPet.Agent")


class AgentState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    GENERATING = "generating"
    WAITING = "waiting"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"
    PAUSED = "paused"


class AgentLifecycle:
    VALID_TRANSITIONS = {
        AgentState.IDLE: {AgentState.INITIALIZING, AgentState.ERROR},
        AgentState.INITIALIZING: {AgentState.IDLE, AgentState.THINKING, AgentState.ERROR},
        AgentState.THINKING: {AgentState.TOOL_CALLING, AgentState.GENERATING, AgentState.COMPLETED, AgentState.ERROR, AgentState.STOPPED},
        AgentState.TOOL_CALLING: {AgentState.THINKING, AgentState.GENERATING, AgentState.COMPLETED, AgentState.ERROR, AgentState.STOPPED},
        AgentState.GENERATING: {AgentState.THINKING, AgentState.COMPLETED, AgentState.ERROR, AgentState.STOPPED},
        AgentState.WAITING: {AgentState.THINKING, AgentState.IDLE, AgentState.ERROR, AgentState.STOPPED},
        AgentState.COMPLETED: {AgentState.IDLE, AgentState.INITIALIZING, AgentState.WAITING},
        AgentState.STOPPED: {AgentState.IDLE, AgentState.ERROR},
        AgentState.ERROR: {AgentState.IDLE, AgentState.INITIALIZING, AgentState.STOPPED},
        AgentState.PAUSED: {AgentState.THINKING, AgentState.WAITING, AgentState.ERROR, AgentState.STOPPED},
    }

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._state: AgentState = AgentState.IDLE
        self._state_history: List[tuple] = [(AgentState.IDLE, time.time())]
        self._state_callbacks: dict = {}
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None
        self.total_turns: int = 0
        self.total_tool_calls: int = 0
        self.total_errors: int = 0
        self.total_tokens_used: int = 0

    @property
    def state(self) -> AgentState:
        return self._state

    def transition(self, new_state: AgentState) -> bool:
        valid_next = self.VALID_TRANSITIONS.get(self._state, set())
        if new_state not in valid_next:
            logger.warning(
                f"[Lifecycle:{self.agent_id}] Invalid transition: {self._state.value} -> {new_state.value}"
            )
            return False

        old_state = self._state
        self._state = new_state
        self._state_history.append((new_state, time.time()))

        if new_state == AgentState.COMPLETED:
            self.completed_at = time.time()
        if new_state == AgentState.TOOL_CALLING:
            self.total_tool_calls += 1
        if new_state == AgentState.ERROR:
            self.total_errors += 1

        callback = self._state_callbacks.get("on_transition")
        if callback:
            callback(old_state, new_state)

        specific_callback = self._state_callbacks.get(f"on_{new_state.value}")
        if specific_callback:
            specific_callback()

        logger.debug(
            f"[Lifecycle:{self.agent_id}] {old_state.value} -> {new_state.value}"
        )
        return True

    def is_terminal(self) -> bool:
        return self._state in {AgentState.COMPLETED, AgentState.ERROR, AgentState.STOPPED}

    def is_active(self) -> bool:
        return self._state in {
            AgentState.THINKING, AgentState.TOOL_CALLING, AgentState.GENERATING,
            AgentState.INITIALIZING,
        }

    def can_accept_task(self) -> bool:
        return self._state in {AgentState.IDLE, AgentState.COMPLETED, AgentState.WAITING}

    def on_transition(self, callback: Callable):
        self._state_callbacks["on_transition"] = callback

    def on_state(self, state: AgentState, callback: Callable):
        self._state_callbacks[f"on_{state.value}"] = callback

    def add_tokens(self, count: int):
        self.total_tokens_used += count

    def get_duration_sec(self) -> float:
        end = self.completed_at or time.time()
        return end - self.created_at

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "state": self._state.value,
            "total_turns": self.total_turns,
            "total_tool_calls": self.total_tool_calls,
            "total_errors": self.total_errors,
            "total_tokens": self.total_tokens_used,
            "duration_sec": round(self.get_duration_sec(), 2),
            "state_transitions": len(self._state_history),
        }

    def reset(self):
        self._state = AgentState.IDLE
        self._state_history = [(AgentState.IDLE, time.time())]
        self.total_turns = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        self.completed_at = None
