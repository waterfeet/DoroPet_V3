import os
import abc
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Set
import logging

from src.agent.core.errors import PermissionError, ConfigurationError
from src.agent.core.context import ExecutionContext, ToolPermission

logger = logging.getLogger("DoroPet.Agent")


class PermissionLevel(Enum):
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


@dataclass
class AccessPolicy:
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    denied_commands: List[str] = field(default_factory=list)
    allowed_network_hosts: List[str] = field(default_factory=list)
    denied_network_hosts: List[str] = field(default_factory=list)
    max_file_size_bytes: int = 100 * 1024 * 1024
    max_output_chars: int = 100000
    allow_subprocess: bool = False
    allow_network_outbound: bool = False
    allow_skill_install: bool = False
    allow_skill_delete: bool = False

    def to_dict(self) -> Dict:
        return {
            "allowed_paths": self.allowed_paths,
            "denied_paths": self.denied_paths,
            "max_file_size_bytes": self.max_file_size_bytes,
            "allow_subprocess": self.allow_subprocess,
            "allow_network_outbound": self.allow_network_outbound,
            "allow_skill_install": self.allow_skill_install,
            "allow_skill_delete": self.allow_skill_delete,
        }

    def is_path_allowed(self, abs_path: str) -> bool:
        normalized = os.path.normpath(os.path.abspath(abs_path))
        for denied in self.denied_paths:
            denied_normalized = os.path.normpath(os.path.abspath(denied))
            if normalized == denied_normalized or normalized.startswith(denied_normalized + os.sep):
                return False
        for allowed in self.allowed_paths:
            allowed_normalized = os.path.normpath(os.path.abspath(allowed))
            if normalized == allowed_normalized or normalized.startswith(allowed_normalized + os.sep):
                return True
        return len(self.allowed_paths) == 0

    def is_network_host_allowed(self, host: str) -> bool:
        for denied in self.denied_network_hosts:
            if denied in host:
                return False
        if not self.allowed_network_hosts:
            return True
        for allowed in self.allowed_network_hosts:
            if allowed in host:
                return True
        return False


class AccessControlProvider(abc.ABC):
    @abc.abstractmethod
    def get_policy(self, context: ExecutionContext) -> AccessPolicy:
        pass


class DefaultAccessControlProvider(AccessControlProvider):
    def __init__(self, project_dir: str, trusted_dirs: Optional[List[str]] = None):
        self.project_dir = os.path.abspath(project_dir)
        self.trusted_dirs = trusted_dirs or [self.project_dir]
        self._protected_dirs = [
            os.path.join(self.project_dir, "src", "core"),
            os.path.join(self.project_dir, "src", "agent"),
        ]

    def get_policy(self, context: ExecutionContext) -> AccessPolicy:
        return AccessPolicy(
            allowed_paths=[self.project_dir],
            denied_paths=self._protected_dirs,
            allow_network_outbound=True,
            allow_skill_install=True,
            allow_skill_delete=True,
            max_file_size_bytes=100 * 1024 * 1024,
        )


class PermissionManager:
    _instance: Optional["PermissionManager"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if PermissionManager._initialized:
            return
        PermissionManager._initialized = True
        self._provider: Optional[AccessControlProvider] = None
        self._required_tool_permissions: Dict[str, List[ToolPermission]] = {}
        self._role_permissions: Dict[str, Set[ToolPermission]] = {
            "default": {ToolPermission.READ_ONLY, ToolPermission.NETWORK},
            "assistant": {ToolPermission.READ_ONLY, ToolPermission.READ_WRITE, ToolPermission.NETWORK},
            "developer": {ToolPermission.READ_ONLY, ToolPermission.READ_WRITE, ToolPermission.NETWORK, ToolPermission.EXECUTE},
            "admin": set(ToolPermission),
        }

    @classmethod
    def get_instance(cls) -> "PermissionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_provider(self, provider: AccessControlProvider):
        self._provider = provider

    def get_policy(self, context: ExecutionContext) -> AccessPolicy:
        if not self._provider:
            return AccessPolicy()
        return self._provider.get_policy(context)

    def register_tool_permissions(self, tool_name: str, permissions: List[ToolPermission]):
        self._required_tool_permissions[tool_name] = permissions

    def check_tool_permissions(self, tool_name: str, granted: Set[ToolPermission]) -> bool:
        required = self._required_tool_permissions.get(tool_name, [])
        if not required:
            return True
        for perm in required:
            if perm not in granted:
                return False
        return True

    def get_role_permissions(self, role: str) -> Set[ToolPermission]:
        return self._role_permissions.get(role, self._role_permissions["default"])

    def validate_path(self, abs_path: str, context: ExecutionContext) -> bool:
        policy = self.get_policy(context)
        normalized = os.path.normpath(os.path.abspath(abs_path))
        for denied in policy.denied_paths:
            denied_norm = os.path.normpath(os.path.abspath(denied))
            if normalized == denied_norm or normalized.startswith(denied_norm + os.sep):
                raise PermissionError(
                    f"Path '{abs_path}' is in a protected directory.",
                    resource=abs_path,
                )
        for allowed in policy.allowed_paths:
            allowed_norm = os.path.normpath(os.path.abspath(allowed))
            if normalized == allowed_norm or normalized.startswith(allowed_norm + os.sep):
                return True
        raise PermissionError(
            f"Path '{abs_path}' is outside allowed directories.",
            resource=abs_path,
        )

    def validate_file_size(self, size: int, context: ExecutionContext) -> bool:
        policy = self.get_policy(context)
        if size > policy.max_file_size_bytes:
            raise PermissionError(
                f"File size {size} exceeds limit {policy.max_file_size_bytes} bytes.",
                resource=f"max_size={policy.max_file_size_bytes}",
            )
        return True
