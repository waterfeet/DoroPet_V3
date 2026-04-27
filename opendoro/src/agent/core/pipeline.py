import abc
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, AsyncGenerator
import time
import logging

from src.agent.core.context import ExecutionContext
from src.agent.core.lifecycle import AgentState

logger = logging.getLogger("DoroPet.Agent")


class HookPoint(Enum):
    BEFORE_RUN = auto()
    AFTER_RUN = auto()
    BEFORE_TOOL_CALL = auto()
    AFTER_TOOL_CALL = auto()
    BEFORE_LLM_CALL = auto()
    AFTER_LLM_CALL = auto()
    ON_ERROR = auto()
    ON_COMPLETE = auto()
    ON_STOP = auto()


@dataclass
class Hook:
    name: str
    hook_point: HookPoint
    callback: Callable
    priority: int = 100
    enabled: bool = True

    def __post_init__(self):
        if self.priority < 0:
            self.priority = 0
        if self.priority > 1000:
            self.priority = 1000

    def __lt__(self, other):
        return self.priority < other.priority


@dataclass
class PipelineStage:
    name: str
    order: int

    async def enter(self, context: ExecutionContext, data: Dict[str, Any]) -> Dict[str, Any]:
        return data

    async def exit(self, context: ExecutionContext, data: Dict[str, Any]) -> Dict[str, Any]:
        return data


class ExecutionPipeline:
    def __init__(self, name: str = "default"):
        self.name = name
        self._stages: List[PipelineStage] = []
        self._hooks: Dict[HookPoint, List[Hook]] = {hp: [] for hp in HookPoint}
        self._middleware: List[Callable] = []
        self._aborted = False
        self._stats: Dict[str, Any] = {}

    def add_stage(self, stage: PipelineStage) -> "ExecutionPipeline":
        self._stages.append(stage)
        self._stages.sort(key=lambda s: s.order)
        return self

    def add_hook(self, hook: Hook) -> "ExecutionPipeline":
        self._hooks[hook.hook_point].append(hook)
        self._hooks[hook.hook_point].sort()
        return self

    def add_middleware(self, middleware: Callable) -> "ExecutionPipeline":
        self._middleware.append(middleware)
        return self

    def abort(self):
        self._aborted = True

    def is_aborted(self) -> bool:
        return self._aborted

    def reset(self):
        self._aborted = False
        self._stats = {}

    def _apply_hooks(self, hook_point: HookPoint, context: ExecutionContext, data: Any = None) -> Any:
        for hook in self._hooks.get(hook_point, []):
            if not hook.enabled:
                continue
            try:
                result = hook.callback(context, data)
                if result is not None:
                    data = result
            except Exception as e:
                logger.error(f"[Pipeline:{self.name}] Hook error '{hook.name}' at {hook_point.name}: {e}")
        return data

    async def execute(
        self,
        context: ExecutionContext,
        runner: Callable,
        **kwargs,
    ) -> Dict[str, Any]:
        self.reset()
        data = dict(kwargs)
        start = time.time()

        try:
            self._apply_hooks(HookPoint.BEFORE_RUN, context, data)

            for middleware in self._middleware:
                if self._aborted:
                    break
                data = middleware(context, data)
                if data is None:
                    data = {}

            for stage in self._stages:
                if self._aborted:
                    break
                stage_start = time.time()
                data = await stage.enter(context, data)
                stage_duration = time.time() - stage_start
                self._stats[f"stage_{stage.name}_duration"] = stage_duration

            if not self._aborted:
                try:
                    result = await runner(context, data)
                    if isinstance(result, dict):
                        data.update(result)
                except Exception as e:
                    logger.error(f"[Pipeline:{self.name}] Runner error: {e}")
                    self._apply_hooks(HookPoint.ON_ERROR, context, {"error": str(e)})
                    data["error"] = str(e)
                    data["status"] = "error"

            for stage in reversed(self._stages):
                data = await stage.exit(context, data)

            self._apply_hooks(HookPoint.AFTER_RUN, context, data)
            self._apply_hooks(HookPoint.ON_COMPLETE, context, data)

        except Exception as e:
            logger.error(f"[Pipeline:{self.name}] Fatal error: {e}")
            self._apply_hooks(HookPoint.ON_ERROR, context, {"error": str(e)})
            data["error"] = str(e)
            data["status"] = "error"

        self._stats["total_duration_ms"] = round((time.time() - start) * 1000, 2)
        data["_pipeline_stats"] = dict(self._stats)
        return data

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)
