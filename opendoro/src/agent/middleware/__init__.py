import logging
from src.agent.core.pipeline import Hook, HookPoint
from src.agent.core.context import ExecutionContext

logger = logging.getLogger("DoroPet.Agent")


def create_logging_hook(priority: int = 200) -> Hook:
    def _log_before_run(context: ExecutionContext, data):
        logger.info(f"[Agent] Starting run. Session={context.session_id}, Role={context.role}")
        return data

    def _log_after_run(context: ExecutionContext, data):
        total_calls = context.get_total_tool_calls()
        logger.info(f"[Agent] Run complete. Tool calls={total_calls}, Result={data.get('status', 'unknown')}")
        return data

    return Hook(
        name="logging",
        hook_point=HookPoint.BEFORE_RUN,
        callback=_log_before_run,
        priority=priority,
    )


def create_error_logging_hook(priority: int = 300) -> Hook:
    def _log_error(context: ExecutionContext, data):
        error_msg = data.get("error", "Unknown error") if isinstance(data, dict) else str(data)
        logger.error(f"[Agent] Error occurred. Session={context.session_id}, Error={error_msg}")
        return data

    return Hook(
        name="error_logging",
        hook_point=HookPoint.ON_ERROR,
        callback=_log_error,
        priority=priority,
    )


def create_rate_limit_middleware(max_calls_per_minute: int = 60):
    import time
    call_times = []

    def middleware(context: ExecutionContext, data):
        nonlocal call_times
        now = time.time()
        call_times = [t for t in call_times if now - t < 60]
        if len(call_times) >= max_calls_per_minute:
            raise Exception(f"Rate limit exceeded: {max_calls_per_minute} calls per minute")
        call_times.append(now)
        return data

    return middleware


def create_validation_middleware(max_message_length: int = 50000):
    def middleware(context: ExecutionContext, data):
        messages = data.get("messages", [])
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        if total_chars > max_message_length:
            raise Exception(f"Total message content ({total_chars} chars) exceeds limit ({max_message_length})")
        return data

    return middleware
