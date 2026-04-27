import os
import json
import glob
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from src.agent.core.tool import Tool, ToolSchema, ToolCategory, ToolResult
from src.agent.core.context import ToolCallContext, ExecutionContext, ToolPermission
from src.agent.core.errors import ToolError
from src.agent.core.sandbox import SandboxManager

logger = logging.getLogger("DoroPet.Agent")


def _resolve_project_dir() -> str:
    return os.getcwd()


@dataclass
class FileSystemConfig:
    project_dir: str = ""
    max_file_size_read: int = 10 * 1024 * 1024
    max_file_size_write: int = 10 * 1024 * 1024
    protected_dirs: List[str] = None

    def __post_init__(self):
        if not self.project_dir:
            self.project_dir = _resolve_project_dir()
        if self.protected_dirs is None:
            self.protected_dirs = [
                os.path.join(self.project_dir, "src", "core"),
                os.path.join(self.project_dir, "src", "agent"),
            ]


_fs_config = FileSystemConfig()


class ReadFileTool(Tool):
    schema = ToolSchema(
        name="read_file",
        description="Read the content of a file from the project filesystem. Only files within the project directory can be read.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read. Must be within the project directory.",
                }
            },
            "required": ["file_path"],
        },
        category=ToolCategory.FILE_SYSTEM,
        required_permissions=[ToolPermission.READ_ONLY],
        max_output_chars=100000,
    )

    async def execute(self, context: ToolCallContext, file_path: str = "", **kwargs) -> ToolResult:
        if not file_path:
            return ToolResult(tool_name=self.schema.name, success=False, error="File path is required.")

        project_dir = _fs_config.project_dir
        abs_path = os.path.abspath(file_path)

        if not abs_path.startswith(os.path.abspath(project_dir)):
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"Permission denied: Cannot read files outside project directory '{project_dir}'.",
            )

        if not os.path.exists(abs_path):
            suggestion = _get_similar_files(file_path, project_dir)
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"File not found: {file_path}.{suggestion}",
            )

        if not os.path.isfile(abs_path):
            return ToolResult(tool_name=self.schema.name, success=False, error=f"Not a file: {file_path}")

        file_size = os.path.getsize(abs_path)
        if file_size > _fs_config.max_file_size_read:
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"File size {file_size} exceeds read limit {_fs_config.max_file_size_read}.",
            )

        try:
            content = _read_file_content(abs_path)
            if len(content) > self.schema.max_output_chars:
                content = content[:self.schema.max_output_chars] + f"\n...[truncated, {len(content)} total chars]"

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={
                    "file_path": file_path,
                    "content": content,
                    "size": file_size,
                },
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class WriteFileTool(Tool):
    schema = ToolSchema(
        name="write_file",
        description="Write content to a file in the project filesystem. Overwrites if exists. Creates directories if needed.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to write the file to. Must be within the project directory.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["file_path", "content"],
        },
        category=ToolCategory.FILE_SYSTEM,
        required_permissions=[ToolPermission.READ_WRITE],
        max_output_chars=1000,
    )

    async def execute(self, context: ToolCallContext, file_path: str = "", content: str = "", **kwargs) -> ToolResult:
        if not file_path:
            return ToolResult(tool_name=self.schema.name, success=False, error="File path is required.")

        project_dir = os.path.abspath(_fs_config.project_dir)
        abs_path = os.path.abspath(file_path)

        if not abs_path.startswith(project_dir):
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"Permission denied: Cannot write outside project directory '{project_dir}'.",
            )

        for protected in _fs_config.protected_dirs:
            protected_abs = os.path.abspath(protected)
            if abs_path == protected_abs or abs_path.startswith(protected_abs + os.sep):
                return ToolResult(
                    tool_name=self.schema.name,
                    success=False,
                    error=f"Permission denied: Cannot write to protected directory '{protected}'.",
                )

        if len(content.encode("utf-8")) > _fs_config.max_file_size_write:
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=f"Content size exceeds write limit {_fs_config.max_file_size_write} bytes.",
            )

        try:
            dir_name = os.path.dirname(abs_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"file_path": file_path, "bytes_written": len(content.encode("utf-8"))},
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class ListFilesTool(Tool):
    schema = ToolSchema(
        name="list_files",
        description="List all files and directories in a given directory within the project.",
        parameters={
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "The path to the directory to list. Defaults to project root.",
                }
            },
            "required": [],
        },
        category=ToolCategory.FILE_SYSTEM,
        required_permissions=[ToolPermission.READ_ONLY],
    )

    async def execute(self, context: ToolCallContext, dir_path: str = ".", **kwargs) -> ToolResult:
        project_dir = os.path.abspath(_fs_config.project_dir)
        abs_path = os.path.abspath(dir_path if dir_path else project_dir)

        if not abs_path.startswith(project_dir):
            abs_path = os.path.join(project_dir, dir_path.lstrip(os.sep))
            abs_path = os.path.abspath(abs_path)

        if not abs_path.startswith(project_dir):
            return ToolResult(tool_name=self.schema.name, success=False, error="Permission denied: Cannot list outside project directory.")

        if not os.path.exists(abs_path):
            return ToolResult(tool_name=self.schema.name, success=False, error=f"Directory not found: {dir_path}")

        try:
            items = os.listdir(abs_path)
            dirs = sorted([i + "/" for i in items if os.path.isdir(os.path.join(abs_path, i))])
            files = sorted([i for i in items if not os.path.isdir(os.path.join(abs_path, i))])

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"dir_path": dir_path, "items": dirs + files, "count": len(items)},
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class SearchFilesTool(Tool):
    schema = ToolSchema(
        name="search_files",
        description="Search for files by glob pattern within the project directory.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern (e.g., '*.py', 'src/**/*.ts').",
                },
                "dir_path": {
                    "type": "string",
                    "description": "Root directory to search in. Defaults to project root.",
                },
            },
            "required": ["pattern"],
        },
        category=ToolCategory.FILE_SYSTEM,
        required_permissions=[ToolPermission.READ_ONLY],
    )

    async def execute(self, context: ToolCallContext, pattern: str = "", dir_path: str = ".", **kwargs) -> ToolResult:
        if not pattern:
            return ToolResult(tool_name=self.schema.name, success=False, error="Pattern is required.")

        project_dir = os.path.abspath(_fs_config.project_dir)
        target_dir = os.path.abspath(dir_path if dir_path else project_dir)

        if not target_dir.startswith(project_dir):
            target_dir = project_dir

        search_pattern = os.path.join(target_dir, pattern)

        try:
            matches = glob.glob(search_pattern, recursive=True)
            rel_matches = []
            for m in matches:
                try:
                    rel_matches.append(os.path.relpath(m, target_dir))
                except ValueError:
                    rel_matches.append(m)

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"pattern": pattern, "matches": rel_matches[:100], "count": len(matches)},
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class EditFileTool(Tool):
    schema = ToolSchema(
        name="edit_file",
        description="Edit a file by searching for specific content and replacing it. Supports fuzzy matching.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to edit."},
                "search": {"type": "string", "description": "Exact text to search for."},
                "replace": {"type": "string", "description": "Text to replace search content with."},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences. Default: false."},
                "fuzzy_match": {"type": "boolean", "description": "Enable fuzzy matching. Default: false."},
            },
            "required": ["file_path", "search", "replace"],
        },
        category=ToolCategory.FILE_SYSTEM,
        required_permissions=[ToolPermission.READ_WRITE],
    )

    async def execute(
        self, context: ToolCallContext,
        file_path: str = "", search: str = "", replace: str = "",
        replace_all: bool = False, fuzzy_match: bool = False, **kwargs
    ) -> ToolResult:
        if not file_path or not search:
            return ToolResult(tool_name=self.schema.name, success=False, error="File path and search content are required.")

        project_dir = os.path.abspath(_fs_config.project_dir)
        abs_path = os.path.abspath(file_path)

        if not abs_path.startswith(project_dir):
            return ToolResult(tool_name=self.schema.name, success=False, error="Permission denied: Cannot edit files outside project directory.")

        for protected in _fs_config.protected_dirs:
            if abs_path.startswith(os.path.abspath(protected)):
                return ToolResult(tool_name=self.schema.name, success=False, error=f"Cannot edit protected files in '{protected}'.")

        if not os.path.exists(abs_path):
            return ToolResult(tool_name=self.schema.name, success=False, error=f"File not found: {file_path}")

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            if search in content:
                if replace_all:
                    new_content = content.replace(search, replace)
                    count = content.count(search)
                else:
                    new_content = content.replace(search, replace, 1)
                    count = 1
            elif fuzzy_match:
                norm_content = re.sub(r'[ \t]+', ' ', content)
                norm_search = re.sub(r'[ \t]+', ' ', search)
                if norm_search in norm_content:
                    new_content = content
                    count = _fuzzy_replace_count(content, search, replace)
                else:
                    return ToolResult(
                        tool_name=self.schema.name,
                        success=False,
                        error=f"Search content not found in file. Try fuzzy_match for whitespace-insensitive matching.",
                    )
            else:
                return ToolResult(
                    tool_name=self.schema.name,
                    success=False,
                    error=f"Search content not found. Use exact text including whitespace.",
                )

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"file_path": file_path, "occurrences_replaced": count},
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


def _read_file_content(abs_path: str) -> str:
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(abs_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception:
            return "[Binary or undecodable file content]"


def _get_similar_files(file_path: str, project_dir: str) -> str:
    try:
        similar = glob.glob(os.path.join(project_dir, "**", f"*{os.path.basename(file_path)}*"), recursive=True)
        if similar:
            rel = [os.path.relpath(f, project_dir) for f in similar[:5]]
            return f" Similar files: {', '.join(rel)}"
    except Exception:
        pass
    return ""


def _fuzzy_replace_count(content: str, search: str, replace: str) -> int:
    norm_content = re.sub(r'[ \t]+', ' ', content)
    norm_search = re.sub(r'[ \t]+', ' ', search)
    return norm_content.count(norm_search)


_file_system_tools = [ReadFileTool(), WriteFileTool(), ListFilesTool(), SearchFilesTool(), EditFileTool()]


def register_file_system_tools(registry=None):
    from src.agent.core.tool import ToolRegistry
    reg = registry or ToolRegistry.get_instance()
    for tool in _file_system_tools:
        reg.register(tool)


def get_file_system_tools():
    return list(_file_system_tools)
