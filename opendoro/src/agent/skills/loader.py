import os
import re
import json
import glob
import importlib.util
import sys
import logging
from typing import Optional, Dict, List, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from src.agent.skills.validator import SkillValidator, SkillValidationResult, compute_skill_hash

logger = logging.getLogger("DoroPet.Agent")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BUILTIN_SKILLS_DIR = os.path.join(BASE_DIR, "src", "skills")


def _get_user_data_dir():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return os.path.join(local_app_data, "DoroPet")
    return os.path.join(os.path.expanduser("~"), "AppData", "Local", "DoroPet")


USER_SKILLS_DIR = os.path.join(_get_user_data_dir(), "skills")


class SkillType(Enum):
    DOCUMENT = "document"
    EXECUTABLE = "executable"
    HYBRID = "hybrid"


@dataclass
class DeclarativeSkill:
    name: str
    description: str
    version: str
    skill_type: SkillType
    path: str
    content: str = ""
    entry_point: Optional[str] = None
    entry_module: Any = None
    entry_function: Optional[Callable] = None
    scripts: List[str] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    skill_hash: str = ""
    is_verified: bool = False
    permissions: List[str] = field(default_factory=list)
    is_builtin: bool = True
    source: str = "builtin"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "type": self.skill_type.value,
            "path": self.path,
            "has_entry_point": self.entry_point is not None,
            "is_verified": self.is_verified,
            "permissions": self.permissions,
            "is_builtin": self.is_builtin,
            "source": self.source,
        }

    def to_tool_schema(self) -> Dict:
        normalized = re.sub(r'[^a-zA-Z0-9_-]', '_', self.name)
        return {
            "type": "function",
            "function": {
                "name": normalized,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }


class SecureSkillLoader:
    def __init__(self, builtin_dir: str = BUILTIN_SKILLS_DIR, user_dir: str = USER_SKILLS_DIR):
        self.builtin_dir = builtin_dir
        self.user_dir = user_dir
        self.validator = SkillValidator()

    @property
    def skills_dir(self) -> str:
        return self.builtin_dir

    def load_all_skills(self) -> Dict[str, DeclarativeSkill]:
        skills = {}
        self._load_from_directory(self.builtin_dir, skills, is_builtin=True)
        self._load_from_directory(self.user_dir, skills, is_builtin=False)
        logger.info(
            f"[SkillLoader] Loaded {len(skills)} skills "
            f"(builtin: {sum(1 for s in skills.values() if s.is_builtin)}, "
            f"user: {sum(1 for s in skills.values() if not s.is_builtin)})"
        )
        return skills

    def _load_from_directory(self, directory: str, skills: Dict[str, DeclarativeSkill], is_builtin: bool):
        if not os.path.exists(directory):
            if not is_builtin:
                os.makedirs(directory, exist_ok=True)
            return
        logger.info(f"[SkillLoader] Loading {'builtin' if is_builtin else 'user'} skills from {directory}")
        self._load_recursive(directory, skills, is_builtin=is_builtin)

    def _load_recursive(self, directory: str, skills: Dict[str, DeclarativeSkill], depth: int = 0, is_builtin: bool = True):
        if depth > 3:
            return

        try:
            items = os.listdir(directory)
        except OSError:
            return

        for item in items:
            if item.startswith(("_", ".")):
                continue

            skill_path = os.path.join(directory, item)
            if not os.path.isdir(skill_path):
                continue

            skill_md = os.path.join(skill_path, "SKILL.md")
            manifest = os.path.join(skill_path, "manifest.json")

            if os.path.exists(skill_md) or os.path.exists(manifest):
                result = self.validator.validate_skill_directory(skill_path)
                if not result.is_valid:
                    logger.warning(f"[SkillLoader] Invalid skill '{item}': {result.errors}")
                    continue

                try:
                    skill = self._load_single_skill(skill_path, skill_md, manifest)
                    if skill:
                        skill.is_builtin = is_builtin
                        skill.source = "builtin" if is_builtin else "user"
                        skills[skill.name] = skill
                except Exception as e:
                    logger.error(f"[SkillLoader] Failed to load skill '{item}': {e}")
            else:
                self._load_recursive(skill_path, skills, depth + 1, is_builtin=is_builtin)

    def _load_single_skill(self, skill_path: str, skill_md: str, manifest: str) -> Optional[DeclarativeSkill]:
        metadata = {}
        body_content = ""
        skill_type = SkillType.DOCUMENT

        if os.path.exists(skill_md):
            with open(skill_md, "r", encoding="utf-8") as f:
                raw = f.read()
            metadata = self._parse_front_matter(raw)
            body_content = self._strip_front_matter(raw)

        if os.path.exists(manifest):
            with open(manifest, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            metadata.update(manifest_data)

        name = metadata.get("name") or os.path.basename(skill_path)
        description = metadata.get("description", f"Skill: {name}")
        version = metadata.get("version", "0.0.0")
        parameters = metadata.get("parameters", {"type": "object", "properties": {}})

        scripts = self._discover_scripts(skill_path)
        entry_point = None
        entry_module = None
        entry_function = None

        if "entry_point" in metadata:
            entry_spec = metadata["entry_point"]
            filepath, func_name = entry_spec, None
            if ":" in entry_spec:
                parts = entry_spec.split(":")
                filepath = parts[0]
                func_name = parts[1] if len(parts) > 1 else None

            full_path = os.path.join(skill_path, filepath)
            if os.path.exists(full_path):
                result = self._safe_load_module(full_path, name)
                if result:
                    entry_module, main_func, func_name = result
                    entry_function = main_func
                    entry_point = f"{filepath}:{func_name}"
                    if not parameters.get("properties"):
                        parameters = self._infer_parameters(main_func, body_content)

        if entry_function and scripts:
            skill_type = SkillType.HYBRID
        elif entry_function:
            skill_type = SkillType.EXECUTABLE

        try:
            skill_hash = compute_skill_hash(skill_path)
        except Exception:
            skill_hash = "unknown"

        permissions = metadata.get("permissions", [])
        if skill_type != SkillType.DOCUMENT:
            if "execute" not in permissions:
                permissions.append("execute")

        return DeclarativeSkill(
            name=name,
            description=description,
            version=version,
            skill_type=skill_type,
            path=skill_path,
            content=body_content,
            entry_point=entry_point,
            entry_module=entry_module,
            entry_function=entry_function,
            scripts=scripts,
            parameters=parameters,
            metadata=metadata,
            skill_hash=skill_hash,
            is_verified=True,
            permissions=permissions,
        )

    def _safe_load_module(self, file_path: str, skill_name: str) -> Optional[Tuple]:
        try:
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', skill_name)
            module_name = f"agent_skills.{safe_name}_{os.path.splitext(os.path.basename(file_path))[0]}"

            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not spec or not spec.loader:
                    return None
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            func_name = self._find_entry_function(module)
            if func_name:
                return module, getattr(module, func_name), func_name
        except FileNotFoundError:
            logger.error(f"[SkillLoader] Module file not found: {file_path}")
        except ImportError as e:
            logger.error(f"[SkillLoader] Import error for {file_path}: {e}")
        except Exception as e:
            logger.error(f"[SkillLoader] Failed to load module {file_path}: {e}")

        return None

    def _find_entry_function(self, module) -> Optional[str]:
        import types
        import inspect

        common = ["main", "execute", "run", "handle", "process", "skill_main"]
        for name in common:
            obj = getattr(module, name, None)
            if obj and callable(obj) and isinstance(obj, types.FunctionType):
                if inspect.getmodule(obj) == module:
                    return name

        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name, None)
            if callable(obj) and isinstance(obj, types.FunctionType):
                if inspect.getmodule(obj) == module:
                    return name

        return None

    def _parse_front_matter(self, content: str) -> Dict:
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return {}
        yaml_str = match.group(1)
        try:
            import yaml
            return yaml.safe_load(yaml_str) or {}
        except Exception:
            metadata = {}
            for line in yaml_str.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
            return metadata

    def _strip_front_matter(self, content: str) -> str:
        match = re.match(r'^---\s*\n.*?\n---\s*\n(.*)$', content, re.DOTALL)
        return match.group(1).strip() if match else content

    def _discover_scripts(self, skill_path: str) -> List[str]:
        scripts_dir = os.path.join(skill_path, "scripts")
        scripts = []
        if os.path.exists(scripts_dir):
            for ext in ["*.py", "*.sh", "*.js", "*.bat"]:
                for script in glob.glob(os.path.join(scripts_dir, ext)):
                    if not os.path.basename(script).startswith("_"):
                        scripts.append(script)
        return scripts

    def _infer_parameters(self, func: Callable, content: str) -> Dict:
        import inspect
        sig = inspect.signature(func)
        parameters = {"type": "object", "properties": {}, "required": []}

        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls', 'kwargs', 'args'):
                continue

            param_info = {"type": "string", "description": f"Parameter: {param_name}"}

            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

            if param.annotation in (int, float):
                param_info["type"] = "number"
            elif param.annotation == bool:
                param_info["type"] = "boolean"
            elif param.annotation == list:
                param_info["type"] = "array"
            elif param.annotation == dict:
                param_info["type"] = "object"

            parameters["properties"][param_name] = param_info

        return parameters
