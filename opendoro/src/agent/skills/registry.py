import os
import json
import re
import shutil
import tempfile
import zipfile
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path

import requests

from src.agent.skills.loader import SecureSkillLoader, DeclarativeSkill, SkillType, BUILTIN_SKILLS_DIR, USER_SKILLS_DIR
from src.agent.skills.validator import SkillValidator, SkillValidationResult
from src.agent.core.tool import Tool, ToolSchema, ToolCategory, ToolResult, ToolRegistry
from src.agent.core.context import ToolCallContext, ToolPermission

logger = logging.getLogger("DoroPet.Agent")


class SkillRegistry:
    _instance: Optional["SkillRegistry"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SkillRegistry._initialized:
            return
        SkillRegistry._initialized = True
        self._skills: Dict[str, DeclarativeSkill] = {}
        self._name_map: Dict[str, str] = {}
        self._loader = SecureSkillLoader()
        self._validator = SkillValidator()
        self._install_lock = False
        self._user_skills_dir = USER_SKILLS_DIR

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def discover_skills(self) -> int:
        self._skills = self._loader.load_all_skills()
        self._build_name_map()
        logger.info(f"[SkillRegistry] Discovered {len(self._skills)} skills")
        return len(self._skills)

    def _build_name_map(self):
        self._name_map = {}
        for name in self._skills:
            normalized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            self._name_map[normalized] = name

    def get(self, skill_name: str) -> Optional[DeclarativeSkill]:
        original = self._name_map.get(skill_name, skill_name)
        return self._skills.get(original)

    def list_skills(self) -> List[Dict]:
        try:
            from src.agent.skills.state import SkillEnabledState
            state = SkillEnabledState.get_instance()
        except ImportError:
            state = None
        result = []
        for name, skill in self._skills.items():
            d = skill.to_dict()
            if state is not None:
                d["is_enabled"] = state.is_enabled(name)
            else:
                d["is_enabled"] = True
            result.append(d)
        return result

    def get_schemas(self) -> List[Dict]:
        try:
            from src.agent.skills.state import SkillEnabledState
            state = SkillEnabledState.get_instance()
        except ImportError:
            state = None
        schemas = []
        for name, skill in self._skills.items():
            if state is not None and not state.is_enabled(name):
                continue
            schemas.append(skill.to_tool_schema())
        return schemas

    def get_descriptions(self) -> Dict[str, str]:
        return {name: skill.description for name, skill in self._skills.items()}

    def execute(self, skill_name: str, **kwargs) -> str:
        original = self._name_map.get(skill_name, skill_name)
        skill = self._skills.get(original)

        if not skill:
            return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found."})

        try:
            from src.agent.skills.state import SkillEnabledState
            state = SkillEnabledState.get_instance()
            if not state.is_enabled(original):
                return json.dumps({
                    "status": "error",
                    "message": f"Skill '{original}' is currently disabled. Enable it in the Skills panel to use it.",
                })
        except ImportError:
            pass

        if skill.skill_type == SkillType.DOCUMENT:
            return json.dumps({
                "status": "info",
                "message": f"Skill '{original}' is a document-type skill.",
                "content": skill.content,
                "scripts": [os.path.basename(s) for s in skill.scripts],
            }, ensure_ascii=False)

        if not skill.entry_function:
            return json.dumps({
                "status": "error",
                "message": f"Skill '{original}' has no executable entry point.",
            })

        try:
            result = skill.entry_function(**kwargs)
            if isinstance(result, str):
                return result
            return json.dumps({"status": "success", "result": result}, ensure_ascii=False, default=str)
        except TypeError as e:
            return json.dumps({"status": "error", "message": f"Parameter error: {str(e)}"})
        except Exception as e:
            logger.error(f"[SkillRegistry] Error executing '{original}': {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def get_content(self, skill_name: str) -> Optional[str]:
        original = self._name_map.get(skill_name, skill_name)
        skill = self._skills.get(original)
        if not skill:
            return None

        try:
            from src.agent.skills.state import SkillEnabledState
            state = SkillEnabledState.get_instance()
            if not state.is_enabled(original):
                return json.dumps({
                    "status": "error",
                    "message": f"Skill '{original}' is currently disabled. Enable it in the Skills panel to view its content."
                }, ensure_ascii=False)
        except ImportError:
            pass

        return skill.content

    def install(self, source: str, skill_name: Optional[str] = None) -> str:
        if self._install_lock:
            return json.dumps({"status": "error", "message": "Another skill installation is in progress."})

        self._install_lock = True
        try:
            return self._do_install(source, skill_name)
        finally:
            self._install_lock = False

    def _do_install(self, source: str, skill_name: Optional[str] = None) -> str:
        github_match = re.match(r'^(?:https?://github\.com/)?([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?$', source)

        if github_match:
            owner, repo = github_match.group(1), github_match.group(2)
            branch = github_match.group(3) or "main"
            subpath = github_match.group(4) or ""
            url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
            return self._install_from_url(url, skill_name, subpath, f"{owner}/{repo}")

        if source.startswith(("http://", "https://")) and source.endswith(".zip"):
            return self._install_from_url(source, skill_name)

        if os.path.exists(source):
            return self._install_from_local(source, skill_name)

        return json.dumps({
            "status": "error",
            "message": f"Unknown source format: {source}. Supported: GitHub, zip URL, or local path.",
        })

    def _install_from_url(self, url: str, skill_name: Optional[str], subpath: str = "", source_info: str = "") -> str:
        logger.info(f"[SkillRegistry] Downloading from {url}")

        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self._validator.MAX_ZIP_SIZE_BYTES:
                return json.dumps({"status": "error", "message": f"Download too large: {content_length} bytes."})

            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "download.zip")
                total = 0
                limit = self._validator.MAX_ZIP_SIZE_BYTES

                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        total += len(chunk)
                        if total > limit:
                            return json.dumps({"status": "error", "message": "Download exceeds size limit."})
                        f.write(chunk)

                validate_result = self._validator.validate_zip_archive(zip_path)
                if not validate_result.is_valid:
                    return json.dumps({"status": "error", "message": f"Invalid archive: {validate_result.errors}"})

                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(temp_dir)

                extracted = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                if not extracted:
                    return json.dumps({"status": "error", "message": "No directory found in archive."})

                extract_root = os.path.join(temp_dir, extracted[0])
                if subpath:
                    extract_root = os.path.join(extract_root, subpath)

                return self._install_from_local(extract_root, skill_name, source_info)

        except requests.exceptions.RequestException as e:
            return json.dumps({"status": "error", "message": f"Download failed: {str(e)}"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def _install_from_local(self, source_path: str, skill_name: Optional[str], source_info: str = "") -> str:
        if not os.path.exists(source_path):
            return json.dumps({"status": "error", "message": f"Source path not found: {source_path}"})

        skill_md = os.path.join(source_path, "SKILL.md")
        manifest = os.path.join(source_path, "manifest.json")

        if not os.path.exists(skill_md) and not os.path.exists(manifest):
            for item in os.listdir(source_path):
                sub = os.path.join(source_path, item)
                if os.path.isdir(sub):
                    if os.path.exists(os.path.join(sub, "SKILL.md")) or os.path.exists(os.path.join(sub, "manifest.json")):
                        source_path = sub
                        skill_md = os.path.join(sub, "SKILL.md")
                        manifest = os.path.join(sub, "manifest.json")
                        break

        validate_result = self._validator.validate_skill_directory(source_path)
        if not validate_result.is_valid:
            return json.dumps({"status": "error", "message": f"Invalid skill: {validate_result.errors}"})

        detected_name = validate_result.skill_name
        final_name = skill_name or detected_name or os.path.basename(source_path)

        target_path = os.path.join(self._user_skills_dir, final_name)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)
        os.makedirs(self._user_skills_dir, exist_ok=True)

        shutil.copytree(source_path, target_path)
        self.discover_skills()
        self._register_skills_as_tools()

        msg = f"Skill '{final_name}' installed successfully to user skills directory."
        if source_info:
            msg += f" from {source_info}"
        logger.info(f"[SkillRegistry] {msg}")
        return json.dumps({"status": "success", "message": msg, "skill_name": final_name})

    def remove(self, skill_name: str) -> str:
        original = self._name_map.get(skill_name, skill_name)
        skill = self._skills.get(original)

        if not skill:
            return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found."})

        if skill.is_builtin:
            return json.dumps({
                "status": "error",
                "message": f"Skill '{original}' is a built-in skill and cannot be removed. Only user-installed skills can be removed.",
            })

        try:
            shutil.rmtree(skill.path)
            if original in self._skills:
                del self._skills[original]
            self._build_name_map()
            logger.info(f"[SkillRegistry] Removed skill: {original}")
            return json.dumps({"status": "success", "message": f"Skill '{original}' removed."})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def _register_skills_as_tools(self):
        from src.agent.core.tool import ToolRegistry
        registry = ToolRegistry.get_instance()
        for name, skill in self._skills.items():
            if skill.skill_type != SkillType.DOCUMENT and skill.entry_function:
                tool = _SkillToolAdapter(skill)
                registry.register(tool)

    def reload(self):
        self._skills = {}
        self._name_map = {}
        self.discover_skills()
        self._register_skills_as_tools()
        logger.info("[SkillRegistry] Reloaded all skills")


class _SkillToolAdapter(Tool):
    def __init__(self, skill: DeclarativeSkill):
        schema = ToolSchema(
            name=skill.name,
            description=skill.description,
            parameters=skill.parameters,
            category=ToolCategory.SKILL,
            required_permissions=[ToolPermission.EXECUTE],
            version=skill.version,
            tags=["skill", skill.skill_type.value],
        )
        super().__init__(schema)
        self._skill = skill

    async def execute(self, context: ToolCallContext, **kwargs) -> ToolResult:
        try:
            result = self._skill.entry_function(**kwargs)
            if isinstance(result, str):
                try:
                    data = json.loads(result)
                except json.JSONDecodeError:
                    data = {"raw": result}
            else:
                data = result

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data=data,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.schema.name,
                success=False,
                error=str(e),
            )


def install_skill_tool_handler(skill_registry: SkillRegistry, source: str = "", skill_name: str = None):
    return skill_registry.install(source, skill_name)


def list_skills_tool_handler(skill_registry: SkillRegistry):
    skills = skill_registry.list_skills()
    return json.dumps({"status": "success", "skills": skills, "count": len(skills)}, ensure_ascii=False)


def get_skill_content_tool_handler(skill_registry: SkillRegistry, skill_name: str = ""):
    content = skill_registry.get_content(skill_name)
    if content is None:
        return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found."})
    return json.dumps({"status": "success", "skill_name": skill_name, "content": content}, ensure_ascii=False)


def remove_skill_tool_handler(skill_registry: SkillRegistry, skill_name: str = ""):
    return skill_registry.remove(skill_name)
