import os
import re
import sys
import json
import time
import subprocess
import tempfile
import threading
import shutil
import signal
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple, IO
from pathlib import Path
import logging

from src.agent.core.errors import SandboxError
from src.agent.core.permission import AccessPolicy

logger = logging.getLogger("DoroPet.Agent")


@dataclass
class SandboxConfig:
    max_execution_time_sec: float = 30.0
    max_output_bytes: int = 1024 * 1024
    max_memory_mb: int = 512
    allowed_import_modules: List[str] = field(default_factory=lambda: [
        "json", "math", "random", "datetime", "collections",
        "itertools", "functools", "re", "string", "typing",
        "os.path", "pathlib", "csv",
    ])
    blocked_import_modules: List[str] = field(default_factory=lambda: [
        "os", "subprocess", "sys", "shutil", "socket", "http",
        "urllib", "requests", "ctypes", "importlib", "inspect",
        "builtins", "__builtins__",
    ])
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    use_isolated_process: bool = True
    network_enabled: bool = False

    def to_dict(self) -> Dict:
        return {
            "max_execution_time_sec": self.max_execution_time_sec,
            "max_output_bytes": self.max_output_bytes,
            "max_memory_mb": self.max_memory_mb,
            "network_enabled": self.network_enabled,
        }


class _CodeValidator:
    DANGEROUS_PATTERNS = [
        r'__import__\s*\(',
        r'exec\s*\(',
        r'eval\s*\(',
        r'compile\s*\(',
        r'globals\s*\(\s*\)',
        r'locals\s*\(\s*\)',
        r'getattr\s*\(.*?__',
        r'setattr\s*\(.*?__',
        r'delattr\s*\(.*?__',
        r'os\.system\s*\(',
        r'os\.popen\s*\(',
        r'os\.exec',
        r'os\.spawn',
        r'os\.kill\s*\(',
        r'subprocess\.',
        r'shutil\.rmtree\s*\(',
        r'shutil\.move\s*\(',
        r'socket\.',
        r'urllib',
        r'http\.',
        r'requests\.',
        r'ctypes\.',
        r'builtins\.',
        r'__builtins__',
        r'open\s*\([^)]*\bw\b',  # open with write mode is suspicious
        r'\.remove\s*\(',
        r'\.unlink\s*\(',
        r'\.rmdir\s*\(',
        r'os\.remove\s*\(',
        r'os\.unlink\s*\(',
        r'os\.rmdir\s*\(',
        r'os\.chmod\s*\(',
        r'os\.chown\s*\(',
        r'os\.link\s*\(',
        r'os\.symlink\s*\(',
        r'os\.rename\s*\(',
        r'sys\.exit\s*\(',
        r'sys\.modules',
        r'importlib\.',
    ]

    @classmethod
    def validate(cls, code: str, config: SandboxConfig) -> Tuple[bool, Optional[str]]:
        for module in config.blocked_import_modules:
            patterns = [
                rf'import\s+{re.escape(module)}',
                rf'from\s+{re.escape(module)}\s+import',
                rf'__import__\s*\(\s*["\']{re.escape(module)}["\']',
            ]
            for pattern in patterns:
                if re.search(pattern, code):
                    return False, f"Blocked import: '{module}' not allowed in sandbox."

        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                return False, f"Dangerous pattern detected: '{pattern}'"

        return True, None


class SecureExecutor:

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    def execute_script(
        self,
        script_path: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        abs_path = os.path.abspath(script_path)
        if not os.path.exists(abs_path):
            raise SandboxError(f"Script not found: {abs_path}")

        file_size = os.path.getsize(abs_path)
        if file_size > self.config.max_output_bytes:
            raise SandboxError(f"Script size {file_size} exceeds limit {self.config.max_output_bytes}")

        cmd = [sys.executable, abs_path] + (args or [])
        return self._run_subprocess(cmd, cwd=cwd, env=env)

    def execute_code(self, code: str, context_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        is_valid, error_msg = _CodeValidator.validate(code, self.config)
        if not is_valid:
            raise SandboxError(f"Code validation failed: {error_msg}")

        if self.config.use_isolated_process:
            return self._execute_isolated(code, context_vars)
        else:
            return self._execute_restricted(code, context_vars)

    def _execute_isolated(self, code: str, context_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            wrapper = self._build_sandbox_wrapper(code, context_vars)
            f.write(wrapper)
            temp_path = f.name

        try:
            result = self._run_subprocess(
                [sys.executable, temp_path],
                cwd=tempfile.gettempdir(),
                env={k: v for k, v in os.environ.items() if k in ("PATH", "TEMP", "TMP", "SYSTEMROOT", "USERPROFILE")},
            )
            return result
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _build_sandbox_wrapper(self, code: str, context_vars: Optional[Dict[str, Any]] = None) -> str:
        wrapper = [
            "import sys",
            "import os",
            "import json",
            "import traceback",
            "",
            "def _sandbox_main():",
            "    _sandbox_globals = {}",
        ]

        if context_vars:
            for key, value in context_vars.items():
                wrapper.append(f'    _sandbox_globals["{key}"] = {json.dumps(value)}')

        wrapper.extend([
            "    try:",
        ])

        for line in code.split("\n"):
            wrapper.append(f"        {line}")

        wrapper.extend([
            "    except SystemExit:",
            "        pass",
            "    except Exception as e:",
            "        print(json.dumps({'status': 'error', 'error_type': type(e).__name__, 'error_message': str(e), 'traceback': traceback.format_exc()}))",
            "        sys.exit(1)",
            "",
            "if __name__ == '__main__':",
            "    _sandbox_main()",
        ])

        return "\n".join(wrapper)

    def _execute_restricted(self, code: str, context_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sorted": sorted,
                "reversed": reversed,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "type": type,
                "isinstance": isinstance,
                "hasattr": hasattr,
                "getattr": getattr,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "StopIteration": StopIteration,
            },
            "json": json,
            "math": __import__("math"),
            "random": __import__("random"),
            "datetime": __import__("datetime"),
            "re": re,
            "os": type("RestrictedOS", (), {
                "path": os.path,
                "getcwd": os.getcwd,
                "listdir": os.listdir,
                "sep": os.sep,
            })(),
        }

        if context_vars:
            restricted_globals.update(context_vars)

        output = []
        def _capture_print(*args, **kwargs):
            output.append(" ".join(str(a) for a in args))

        restricted_globals["__builtins__"]["print"] = _capture_print

        try:
            exec(code, restricted_globals)
            return {
                "status": "success",
                "output": "\n".join(output) if output else "Code executed successfully (no output).",
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    def _run_subprocess(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.max_execution_time_sec,
                cwd=cwd,
                env=env,
            )

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            max_len = self.config.max_output_bytes
            if len(stdout) > max_len:
                stdout = stdout[:max_len] + f"\n...[truncated, total {len(stdout)} bytes]"
            if len(stderr) > max_len:
                stderr = stderr[:max_len] + f"\n...[truncated, total {len(stderr)} bytes]"

            return {
                "status": "success" if process.returncode == 0 else "error",
                "returncode": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": round((time.time() - start) * 1000, 2),
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error_type": "TimeoutExpired",
                "error_message": f"Script exceeded time limit of {self.config.max_execution_time_sec}s",
                "duration_ms": round(self.config.max_execution_time_sec * 1000, 2),
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }


class SandboxManager:
    _instance: Optional["SandboxManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SandboxManager._initialized:
            return
        SandboxManager._initialized = True
        self._config = SandboxConfig()
        self._executor = SecureExecutor(self._config)
        self._execution_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SandboxManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def config(self) -> SandboxConfig:
        return self._config

    @property
    def executor(self) -> SecureExecutor:
        return self._executor

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self._executor = SecureExecutor(self._config)

    def execute_python(self, code: str, context_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._execution_lock:
            return self._executor.execute_code(code, context_vars)

    def execute_script(self, script_path: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        with self._execution_lock:
            return self._executor.execute_script(script_path, args)
