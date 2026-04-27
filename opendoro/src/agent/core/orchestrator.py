import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from src.agent.core.base import BaseAgent, AgentConfig
from src.agent.core.context import ExecutionContext
from src.agent.core.lifecycle import AgentState
from src.agent.core.errors import AgentError

logger = logging.getLogger("DoroPet.Agent")


class OrchestrationStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ROUND_ROBIN = "round_robin"
    VOTE = "vote"


@dataclass
class AgentTask:
    task_id: str
    agent_id: str
    messages: List[Dict]
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTaskResult:
    task_id: str
    agent_id: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class AgentOrchestrator:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._strategy: OrchestrationStrategy = OrchestrationStrategy.SEQUENTIAL
        self._task_queue: List[AgentTask] = []
        self._results: Dict[str, AgentTaskResult] = {}
        self._context: Optional[ExecutionContext] = None
        self._hooks: Dict[str, List[Callable]] = {
            "on_task_start": [],
            "on_task_complete": [],
            "on_task_error": [],
            "on_orchestration_complete": [],
        }

    def register_agent(self, agent: BaseAgent):
        if agent.config.agent_id in self._agents:
            logger.warning(f"[Orchestrator] Agent '{agent.config.agent_id}' is being overwritten.")
        self._agents[agent.config.agent_id] = agent
        logger.info(f"[Orchestrator] Registered agent: {agent.config.agent_id}")

    def unregister_agent(self, agent_id: str):
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"[Orchestrator] Unregistered agent: {agent_id}")

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict]:
        return [
            {
                "agent_id": a.config.agent_id,
                "name": a.config.name,
                "state": a.lifecycle.state.value,
            }
            for a in self._agents.values()
        ]

    def set_strategy(self, strategy: OrchestrationStrategy):
        self._strategy = strategy

    def add_hook(self, event: str, callback: Callable):
        if event in self._hooks:
            self._hooks[event].append(callback)

    def submit_task(self, task: AgentTask):
        self._task_queue.append(task)

    def submit_tasks(self, tasks: List[AgentTask]):
        self._task_queue.extend(tasks)

    async def run(self, context: ExecutionContext) -> Dict[str, AgentTaskResult]:
        self._context = context
        self._results = {}

        if not self._task_queue:
            return {}

        if self._strategy == OrchestrationStrategy.SEQUENTIAL:
            await self._run_sequential(context)
        elif self._strategy == OrchestrationStrategy.PARALLEL:
            await self._run_parallel(context)
        elif self._strategy == OrchestrationStrategy.ROUND_ROBIN:
            await self._run_round_robin(context)
        elif self._strategy == OrchestrationStrategy.VOTE:
            await self._run_vote(context)

        self._trigger_hooks("on_orchestration_complete", self._results)
        return dict(self._results)

    async def _run_sequential(self, context: ExecutionContext):
        for task in self._task_queue:
            result = await self._execute_task(task, context)
            self._results[task.task_id] = result

    async def _run_parallel(self, context: ExecutionContext):
        tasks = [self._execute_task(task, context) for task in self._task_queue]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for task, result in zip(self._task_queue, results):
            if isinstance(result, Exception):
                self._results[task.task_id] = AgentTaskResult(
                    task_id=task.task_id,
                    agent_id=task.agent_id,
                    success=False,
                    data={},
                    error=str(result),
                )
            else:
                self._results[task.task_id] = result

    async def _run_round_robin(self, context: ExecutionContext):
        agent_ids = list(self._agents.keys())
        if not agent_ids:
            return
        idx = 0
        for task in self._task_queue:
            task.agent_id = agent_ids[idx % len(agent_ids)]
            result = await self._execute_task(task, context)
            self._results[task.task_id] = result
            idx += 1

    async def _run_vote(self, context: ExecutionContext):
        for task in self._task_queue:
            agent_results = []
            for agent_id in self._agents:
                task_copy = AgentTask(
                    task_id=f"{task.task_id}_{agent_id}",
                    agent_id=agent_id,
                    messages=list(task.messages),
                    priority=task.priority,
                    metadata=dict(task.metadata),
                )
                result = await self._execute_task(task_copy, context)
                agent_results.append(result)

            best = self._select_best_result(agent_results)
            self._results[task.task_id] = best

    async def _execute_task(self, task: AgentTask, context: ExecutionContext) -> AgentTaskResult:
        self._trigger_hooks("on_task_start", task)

        agent = self._agents.get(task.agent_id)
        if not agent:
            error_result = AgentTaskResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=False,
                data={},
                error=f"Agent '{task.agent_id}' not found.",
            )
            self._trigger_hooks("on_task_error", error_result)
            return error_result

        try:
            data = await agent.run(task.messages, context, **task.metadata)
            result = AgentTaskResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=True,
                data=data,
            )
            self._trigger_hooks("on_task_complete", result)
            return result
        except Exception as e:
            error_result = AgentTaskResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=False,
                data={},
                error=str(e),
            )
            self._trigger_hooks("on_task_error", error_result)
            return error_result

    def _select_best_result(self, results: List[AgentTaskResult]) -> AgentTaskResult:
        successful = [r for r in results if r.success]
        if not successful:
            return results[0] if results else AgentTaskResult(
                task_id="vote",
                agent_id="unknown",
                success=False,
                data={},
                error="No successful results",
            )
        return max(successful, key=lambda r: len(r.data.get("content", "")))

    def _trigger_hooks(self, event: str, data: Any):
        for callback in self._hooks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"[Orchestrator] Hook error for '{event}': {e}")

    def stop_all(self):
        for agent in self._agents.values():
            agent.stop()

    def get_results(self) -> Dict[str, AgentTaskResult]:
        return dict(self._results)
