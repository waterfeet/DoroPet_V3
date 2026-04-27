import os
import sys
import json
import logging
from typing import Optional, Dict, Any

from src.agent.core.tool import Tool, ToolSchema, ToolCategory, ToolResult
from src.agent.core.context import ToolCallContext, ToolPermission
from src.agent.core.sandbox import SandboxManager

logger = logging.getLogger("DoroPet.Agent")


class RunPythonTool(Tool):
    schema = ToolSchema(
        name="run_python_script",
        description="Run a Python script from the project filesystem in a sandboxed environment.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the Python file to run. Must be within the project directory.",
                }
            },
            "required": ["file_path"],
        },
        category=ToolCategory.CODE_EXECUTION,
        required_permissions=[ToolPermission.EXECUTE],
        timeout_ms=35000,
        max_output_chars=50000,
    )

    async def execute(self, context: ToolCallContext, file_path: str = "", **kwargs) -> ToolResult:
        if not file_path:
            return ToolResult(tool_name=self.schema.name, success=False, error="File path is required.")

        project_dir = os.getcwd()
        abs_path = os.path.abspath(file_path)

        if not os.path.dirname(abs_path) and not os.path.exists(abs_path):
            plugin_path = os.path.join(project_dir, "plugin", file_path)
            if os.path.exists(plugin_path):
                abs_path = os.path.abspath(plugin_path)

        if not abs_path.startswith(os.path.abspath(project_dir)):
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"Permission denied: Cannot execute scripts outside project directory.",
            )

        protected_dirs = [
            os.path.join(project_dir, "src", "core"),
            os.path.join(project_dir, "src", "agent"),
        ]
        for protected in protected_dirs:
            if abs_path.startswith(os.path.abspath(protected)):
                return ToolResult(
                    tool_name=self.schema.name,
                    success=False,
                    error=f"Permission denied: Cannot execute scripts from '{protected}'.",
                )

        if not os.path.exists(abs_path):
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"File not found: {file_path}",
            )

        file_size = os.path.getsize(abs_path)
        if file_size > 5 * 1024 * 1024:
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"Script size {file_size} bytes exceeds 5MB limit.",
            )

        sandbox = SandboxManager.get_instance()
        result = sandbox.execute_script(abs_path)

        if result.get("status") == "success":
            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={
                    "script": file_path,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "returncode": result.get("returncode", 0),
                    "duration_ms": result.get("duration_ms", 0),
                },
            )
        else:
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=result.get("error_message", result.get("stderr", "Unknown error")),
            )


_code_executor_tools = [RunPythonTool()]


def register_code_executor_tools(registry=None):
    from src.agent.core.tool import ToolRegistry
    reg = registry or ToolRegistry.get_instance()
    for tool in _code_executor_tools:
        reg.register(tool)


def get_code_executor_tools():
    return list(_code_executor_tools)
