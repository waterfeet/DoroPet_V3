import abc
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Tuple

from src.agent.core.context import ExecutionContext, ToolCallContext
from src.agent.core.tool import Tool, ToolRegistry, ToolSchema, ToolCategory, ToolResult
from src.agent.core.pipeline import ExecutionPipeline, Hook, HookPoint
from src.agent.core.lifecycle import AgentState, AgentLifecycle
from src.agent.core.errors import AgentError, ConfigurationError

logger = logging.getLogger("DoroPet.Agent")


@dataclass
class AgentConfig:
    agent_id: str
    name: str = "DefaultAgent"
    description: str = ""
    model: str = "gpt-3.5-turbo"
    system_prompt: str = "You are a helpful assistant."
    max_turns: int = 20
    max_tokens: int = 8192
    temperature: float = 0.7
    thinking_budget: int = 0
    tools_enabled: bool = True
    enabled_tool_categories: Optional[List[str]] = None
    disabled_tools: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model": self.model,
            "max_turns": self.max_turns,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


class BaseAgent(abc.ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.lifecycle = AgentLifecycle(config.agent_id)
        self.tool_registry = ToolRegistry.get_instance()
        self.pipeline = ExecutionPipeline(name=config.agent_id)
        self._setup_default_hooks()
        self._setup_default_pipeline()

    def _setup_default_hooks(self):
        self.pipeline.add_hook(Hook(
            name="lifecycle_update",
            hook_point=HookPoint.BEFORE_RUN,
            callback=lambda ctx, data: self.lifecycle.transition(AgentState.INITIALIZING),
            priority=0,
        ))

    def _setup_default_pipeline(self):
        pass

    async def initialize(self, context: ExecutionContext) -> bool:
        self.lifecycle.transition(AgentState.INITIALIZING)
        return True

    @abc.abstractmethod
    async def _call_llm(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Tuple[str, List[Dict], str]:
        pass

    @abc.abstractmethod
    async def _call_llm_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ):
        pass

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        call_context = ToolCallContext(
            tool_name=tool_name,
            arguments=arguments,
            call_id=f"call_{int(time.time() * 1000)}",
            session_id=context.session_id,
        )

        context.add_tool_call(call_context)
        self.lifecycle.transition(AgentState.TOOL_CALLING)

        self.pipeline._apply_hooks(HookPoint.BEFORE_TOOL_CALL, context, {
            "tool_name": tool_name,
            "arguments": arguments,
        })

        result = await self.tool_registry.execute_sync(tool_name, call_context, **arguments)

        call_context.mark_completed(result.success, str(result.data)[:200] if result.data else result.error)

        self.pipeline._apply_hooks(HookPoint.AFTER_TOOL_CALL, context, result)

        return result

    async def run(
        self,
        messages: List[Dict],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        if not self.lifecycle.can_accept_task():
            raise AgentError(
                f"Agent '{self.config.agent_id}' is not ready. Current state: {self.lifecycle.state.value}"
            )

        self.lifecycle.transition(AgentState.INITIALIZING)

        async def _runner(ctx: ExecutionContext, data: Dict) -> Dict:
            return await self._agent_loop(messages, ctx, **data)

        result = await self.pipeline.execute(context, _runner, **kwargs)

        self.lifecycle.transition(AgentState.COMPLETED)
        return result

    async def _agent_loop(
        self,
        messages: List[Dict],
        context: ExecutionContext,
        **kwargs,
    ) -> Dict[str, Any]:
        turn = 0
        full_content = ""
        tool_calls_log = []

        tools = self._get_enabled_tools() if self.config.tools_enabled else None

        while turn < self.config.max_turns:
            turn += 1
            self.lifecycle.total_turns = turn
            self.lifecycle.transition(AgentState.THINKING)

            if self.pipeline.is_aborted():
                break

            content, raw_tool_calls, finish_reason = await self._call_llm(
                messages=messages,
                tools=tools,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            full_content += content

            if not raw_tool_calls:
                break

            tool_calls = raw_tool_calls if isinstance(raw_tool_calls, list) else [raw_tool_calls]
            assistant_msg = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

            messages.append(assistant_msg)

            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                func_args_str = tc.get("function", {}).get("arguments", "{}")
                call_id = tc.get("id", "")

                try:
                    arguments = json.loads(func_args_str)
                except json.JSONDecodeError:
                    arguments = {}

                result = await self.execute_tool(func_name, arguments, context)
                tool_calls_log.append({
                    "tool_name": func_name,
                    "arguments": arguments,
                    "success": result.success,
                    "data": result.data,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result.to_message_content(),
                })

        return {
            "content": full_content,
            "tool_calls": tool_calls_log,
            "turns": turn,
            "lifecycle_stats": self.lifecycle.get_stats(),
        }

    def _get_enabled_tools(self) -> Optional[List[Dict]]:
        all_tools = list(self.tool_registry._tools.values())

        if self.config.disabled_tools:
            all_tools = [t for t in all_tools if t.schema.name not in self.config.disabled_tools]

        if self.config.enabled_tool_categories:
            from src.agent.core.tool import ToolCategory
            categories = [getattr(ToolCategory, cat.upper(), None) for cat in self.config.enabled_tool_categories]
            categories = [c for c in categories if c is not None]
            if categories:
                all_tools = [t for t in all_tools if t.schema.category in categories]

        return [t.schema.to_openai_schema() for t in all_tools]

    def stop(self):
        self.pipeline.abort()
        self.lifecycle.transition(AgentState.STOPPED)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "lifecycle": self.lifecycle.get_stats(),
            "pipeline_stats": self.pipeline.get_stats(),
        }

    def __repr__(self):
        return f"BaseAgent(id={self.config.agent_id}, state={self.lifecycle.state.value})"
