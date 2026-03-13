import os
import json
import importlib.util
import sys
import shutil
import subprocess
import tempfile
import re
import glob
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

import requests

from src.core.logger import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(BASE_DIR, "src", "skills")


class SkillType(Enum):
    DOCUMENT = "document"
    EXECUTABLE = "executable"
    HYBRID = "hybrid"


@dataclass
class Skill:
    name: str
    description: str
    version: str
    skill_type: SkillType
    path: str
    content: str = ""
    entry_point: Optional[str] = None
    function: Optional[Callable] = None
    module: Any = None
    scripts: List[str] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "type": self.skill_type.value,
            "path": self.path,
            "scripts": self.scripts,
            "has_entry_point": self.entry_point is not None,
        }


class SkillManager:
    def __init__(self, skills_dir: str = SKILLS_DIR):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}
        self.load_skills()

    def load_skills(self) -> None:
        self.skills = {}
        if not os.path.exists(self.skills_dir):
            try:
                os.makedirs(self.skills_dir)
            except Exception as e:
                logger.error(f"Failed to create skills directory: {e}")
                return

        logger.info(f"Loading skills from {self.skills_dir}")
        self._load_skills_recursive(self.skills_dir)

    def _load_skills_recursive(self, directory: str, depth: int = 0) -> None:
        if depth > 3:
            return

        try:
            items = os.listdir(directory)
        except Exception as e:
            logger.error(f"Failed to list directory {directory}: {e}")
            return

        for item in items:
            if item.startswith(("_", ".")):
                continue

            skill_path = os.path.join(directory, item)
            if not os.path.isdir(skill_path):
                continue

            skill_md_path = os.path.join(skill_path, "SKILL.md")
            manifest_path = os.path.join(skill_path, "manifest.json")

            if os.path.exists(skill_md_path):
                try:
                    self._load_skill_from_md(skill_path, skill_md_path)
                except Exception as e:
                    logger.error(f"Failed to load skill from SKILL.md {item}: {e}")
            elif os.path.exists(manifest_path):
                try:
                    self._load_skill_from_manifest(skill_path, manifest_path)
                except Exception as e:
                    logger.error(f"Failed to load skill from manifest {item}: {e}")
            else:
                self._load_skills_recursive(skill_path, depth + 1)

    def _parse_yaml_front_matter(self, content: str) -> Optional[Dict]:
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return None

        yaml_content = match.group(1)
        try:
            import yaml
            metadata = yaml.safe_load(yaml_content)
            if isinstance(metadata, dict):
                return metadata
        except Exception as e:
            logger.warning(f"YAML parsing failed, falling back to simple parsing: {e}")

        metadata = {}
        for line in yaml_content.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                metadata[key] = value

        return metadata

    def _get_body_content(self, content: str) -> str:
        match = re.match(r'^---\s*\n.*?\n---\s*\n(.*)$', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content

    def _find_scripts(self, skill_path: str) -> List[str]:
        scripts_dir = os.path.join(skill_path, "scripts")
        scripts = []

        if os.path.exists(scripts_dir):
            for ext in ["*.sh", "*.py", "*.js", "*.bat"]:
                for script in glob.glob(os.path.join(scripts_dir, ext)):
                    if not os.path.basename(script).startswith("_"):
                        scripts.append(script)

        return scripts

    def _find_python_entry(self, skill_path: str, metadata: Dict = None) -> Optional[tuple]:
        search_paths = [
            skill_path,
            os.path.join(skill_path, "scripts"),
        ]

        preferred_names = ["main.py", "skill.py", "index.py", "handler.py", "run.py", "pptx_tool.py"]

        if metadata and "entry_point" in metadata:
            entry_spec = metadata["entry_point"]
            if ":" in entry_spec:
                file_part = entry_spec.split(":")[0]
            else:
                file_part = entry_spec
            for search_path in search_paths:
                explicit_path = os.path.join(search_path, file_part)
                if os.path.exists(explicit_path):
                    return explicit_path, search_path

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            for preferred in preferred_names:
                file_path = os.path.join(search_path, preferred)
                if os.path.exists(file_path):
                    return file_path, search_path

            for f in glob.glob(os.path.join(search_path, "*.py")):
                basename = os.path.basename(f)
                if not basename.startswith("_") and basename not in ["setup.py", "__init__.py"]:
                    return f, search_path

        return None

    def _find_main_function(self, module) -> Optional[str]:
        import types
        import inspect

        common_names = ["main", "execute", "run", "handle", "process"]

        for name in common_names:
            obj = getattr(module, name, None)
            if obj and callable(obj) and isinstance(obj, types.FunctionType):
                if inspect.getmodule(obj) == module:
                    return name

        public_funcs = [
            name for name in dir(module)
            if not name.startswith('_') and callable(getattr(module, name))
            and isinstance(getattr(module, name), types.FunctionType)
            and inspect.getmodule(getattr(module, name)) == module
        ]

        return public_funcs[0] if public_funcs else None

    def _load_python_module(self, file_path: str, skill_name: str) -> Optional[tuple]:
        try:
            module_name = f"skills.{skill_name}.{os.path.splitext(os.path.basename(file_path))[0]}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return None

            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            func_name = self._find_main_function(module)
            if func_name:
                return module, getattr(module, func_name)

        except Exception as e:
            logger.error(f"Error loading Python module {file_path}: {e}")

        return None

    def _infer_parameters(self, func: Callable, content: str) -> Dict:
        import inspect

        sig = inspect.signature(func)
        parameters = {"type": "object", "properties": {}, "required": []}

        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'cls', 'kwargs', 'args']:
                continue

            param_info = {"type": "string", "description": f"Parameter: {param_name}"}

            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

            if param.annotation == int or param.annotation == float:
                param_info["type"] = "number"
            elif param.annotation == bool:
                param_info["type"] = "boolean"
            elif param.annotation == list:
                param_info["type"] = "array"
            elif param.annotation == dict:
                param_info["type"] = "object"

            param_pattern = rf'({param_name}|"?{param_name}"?)\s*[:：]\s*(.+)'
            param_match = re.search(param_pattern, content, re.IGNORECASE)
            if param_match:
                param_info["description"] = param_match.group(2).strip()

            parameters["properties"][param_name] = param_info

        return parameters

    def _determine_skill_type(self, has_entry: bool, has_scripts: bool) -> SkillType:
        if has_entry and has_scripts:
            return SkillType.HYBRID
        elif has_entry:
            return SkillType.EXECUTABLE
        else:
            return SkillType.DOCUMENT

    def _load_skill_from_md(self, skill_path: str, skill_md_path: str) -> None:
        with open(skill_md_path, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = self._parse_yaml_front_matter(content)
        if not metadata:
            logger.error(f"No YAML front matter found in {skill_md_path}")
            return

        name = metadata.get('name') or os.path.basename(skill_path)
        description = metadata.get('description', f"Skill: {name}")
        version = metadata.get('version', '0.0.0')

        body_content = self._get_body_content(content)
        scripts = self._find_scripts(skill_path)

        entry_point = None
        module = None
        function = None
        parameters = metadata.get("parameters", {})

        if "entry_point" in metadata:
            entry_spec = metadata["entry_point"]
            if ":" in entry_spec:
                filename, func_name = entry_spec.split(":", 1)
            else:
                filename, func_name = entry_spec, None
            file_path = os.path.join(skill_path, filename)
            if os.path.exists(file_path):
                module_result = self._load_python_module(file_path, name)
                if module_result:
                    module, function = module_result
                    entry_point = entry_spec
                    if not parameters:
                        parameters = self._infer_parameters(function, content)

        skill_type = self._determine_skill_type(function is not None, len(scripts) > 0)

        self.skills[name] = Skill(
            name=name,
            description=description,
            version=version,
            skill_type=skill_type,
            path=skill_path,
            content=body_content,
            entry_point=entry_point,
            function=function,
            module=module,
            scripts=scripts,
            parameters=parameters,
            metadata=metadata,
        )

        # logger.info(
        #     f"Loaded skill: {name} (type: {skill_type.value}, "
        #     f"entry: {entry_point or 'none'}, scripts: {len(scripts)})"
        # )

    def _load_skill_from_manifest(self, skill_path: str, manifest_path: str) -> None:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        name = manifest.get("name")
        entry_point_str = manifest.get("entry_point")

        if not name:
            logger.error(f"Invalid manifest in {skill_path}: missing name")
            return

        description = manifest.get("description", f"Skill: {name}")
        version = manifest.get("version", "0.0.0")
        parameters = manifest.get("parameters", {"type": "object", "properties": {}})

        scripts = self._find_scripts(skill_path)
        module = None
        function = None
        entry_point = None

        if entry_point_str:
            try:
                filename, func_name = entry_point_str.split(":")
            except ValueError:
                logger.error(f"Invalid entry_point format in {skill_path}: {entry_point_str}")
                return

            file_path = os.path.join(skill_path, filename)
            if os.path.exists(file_path):
                module_result = self._load_python_module(file_path, name)
                if module_result:
                    module, function = module_result
                    entry_point = entry_point_str

        skill_type = self._determine_skill_type(function is not None, len(scripts) > 0)

        skill_md_path = os.path.join(skill_path, "SKILL.md")
        content = ""
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = self._get_body_content(f.read())

        self.skills[name] = Skill(
            name=name,
            description=description,
            version=version,
            skill_type=skill_type,
            path=skill_path,
            content=content,
            entry_point=entry_point,
            function=function,
            module=module,
            scripts=scripts,
            parameters=parameters,
            metadata=manifest,
        )

        logger.info(f"Loaded skill from manifest: {name}")

    def get_tool_schemas(self) -> List[Dict]:
        schemas = []
        for name, skill in self.skills.items():
            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": skill.description,
                    "parameters": skill.parameters or {"type": "object", "properties": {}},
                },
            }
            schemas.append(schema)
        return schemas

    def get_skill_content(self, skill_name: str) -> Optional[str]:
        if skill_name in self.skills:
            return self.skills[skill_name].content
        return None

    def get_all_skill_descriptions(self) -> Dict[str, str]:
        return {name: skill.description for name, skill in self.skills.items()}

    def execute_skill(self, skill_name: str, **kwargs) -> str:
        if skill_name not in self.skills:
            logger.error(f"[SkillManager] Skill '{skill_name}' not found. Available skills: {list(self.skills.keys())}")
            return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found"})

        skill = self.skills[skill_name]
        logger.info(f"[SkillManager] Executing skill '{skill_name}' (type: {skill.skill_type.value}, entry: {skill.entry_point})")
        logger.info(f"[SkillManager] Skill '{skill_name}' parameters: {kwargs}")

        if skill.function:
            try:
                logger.info(f"[SkillManager] Calling skill function for '{skill_name}'...")
                result = skill.function(**kwargs)
                if isinstance(result, str):
                    logger.info(f"[SkillManager] Skill '{skill_name}' executed successfully (string result, length: {len(result)})")
                    return result
                logger.info(f"[SkillManager] Skill '{skill_name}' executed successfully (result type: {type(result).__name__})")
                return json.dumps({"status": "success", "result": result}, ensure_ascii=False)
            except TypeError as e:
                logger.error(f"[SkillManager] Skill '{skill_name}' parameter error: {e}. Expected params: {list(skill.parameters.get('properties', {}).keys())}, Got: {list(kwargs.keys())}")
                return json.dumps({"status": "error", "message": f"Parameter error: {str(e)}"})
            except Exception as e:
                logger.error(f"[SkillManager] Error executing skill '{skill_name}': {type(e).__name__}: {e}")
                return json.dumps({"status": "error", "message": str(e)})

        logger.info(f"[SkillManager] Skill '{skill_name}' is document-type, returning full content for AI to learn")
        return json.dumps({
            "status": "info",
            "message": f"Skill '{skill_name}' is a document-type skill. Please read the content below and learn how to use it.",
            "content": skill.content,
            "scripts": [os.path.basename(s) for s in skill.scripts],
        }, ensure_ascii=False)

    def execute_script(self, skill_name: str, script_name: str, *args) -> str:
        if skill_name not in self.skills:
            return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found"})

        skill = self.skills[skill_name]

        script_path = None
        for script in skill.scripts:
            if os.path.basename(script) == script_name:
                script_path = script
                break

        if not script_path:
            return json.dumps({
                "status": "error",
                "message": f"Script '{script_name}' not found in skill '{skill_name}'",
                "available_scripts": [os.path.basename(s) for s in skill.scripts],
            })

        try:
            if script_path.endswith(".py"):
                cmd = [sys.executable, script_path] + list(args)
            elif script_path.endswith(".sh"):
                cmd = ["bash", script_path] + list(args)
            elif script_path.endswith(".bat"):
                cmd = ["cmd", "/c", script_path] + list(args)
            elif script_path.endswith(".js"):
                cmd = ["node", script_path] + list(args)
            else:
                cmd = [script_path] + list(args)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=skill.path,
            )

            return json.dumps({
                "status": "success" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }, ensure_ascii=False)

        except subprocess.TimeoutExpired:
            return json.dumps({"status": "error", "message": "Script execution timed out"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def install_skill(self, source: str, skill_name: Optional[str] = None) -> str:
        try:
            github_pattern = r'^(?:https?://github\.com/)?([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?$'
            gitlab_pattern = r'^(?:https?://gitlab\.com/)?([^/]+)/([^/]+)'

            github_match = re.match(github_pattern, source)
            gitlab_match = re.match(gitlab_pattern, source)

            if github_match:
                owner, repo = github_match.group(1), github_match.group(2)
                branch = github_match.group(3) or "main"
                subpath = github_match.group(4) or ""
                url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
                return self._install_from_zip_url(url, skill_name, subpath, f"{owner}/{repo}")

            elif gitlab_match:
                owner, repo = gitlab_match.group(1), gitlab_match.group(2)
                url = f"https://gitlab.com/{owner}/{repo}/-/archive/main/{repo}-main.zip"
                return self._install_from_zip_url(url, skill_name, "", f"{owner}/{repo}")

            elif source.startswith(("http://", "https://")) and source.endswith(".zip"):
                return self._install_from_zip_url(source, skill_name)

            elif os.path.exists(source):
                return self._install_from_local(source, skill_name)

            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown source format: {source}. "
                    "Supported: GitHub (owner/repo), GitLab URL, zip URL, or local path.",
                })

        except Exception as e:
            logger.error(f"Failed to install skill: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _install_from_zip_url(
        self, url: str, skill_name: Optional[str], subpath: str = "", source_info: str = ""
    ) -> str:
        logger.info(f"Downloading skill from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "download.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)

            import zipfile
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp_dir)

            extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d != "_temp_install"]
            if not extracted_dirs:
                return json.dumps({"status": "error", "message": "No directory found in archive"})

            extract_root = os.path.join(temp_dir, extracted_dirs[0])
            if subpath:
                extract_root = os.path.join(extract_root, subpath)

            return self._install_from_local(extract_root, skill_name, source_info)

    def _install_from_local(self, source_path: str, skill_name: Optional[str], source_info: str = "") -> str:
        skill_md_path = os.path.join(source_path, "SKILL.md")
        manifest_path = os.path.join(source_path, "manifest.json")

        if not os.path.exists(skill_md_path) and not os.path.exists(manifest_path):
            for item in os.listdir(source_path):
                sub_path = os.path.join(source_path, item)
                if os.path.isdir(sub_path):
                    if os.path.exists(os.path.join(sub_path, "SKILL.md")):
                        skill_md_path = os.path.join(sub_path, "SKILL.md")
                        source_path = sub_path
                        break
                    if os.path.exists(os.path.join(sub_path, "manifest.json")):
                        manifest_path = os.path.join(sub_path, "manifest.json")
                        source_path = sub_path
                        break

        detected_name = None
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()
            metadata = self._parse_yaml_front_matter(content)
            if metadata:
                detected_name = metadata.get("name")
        elif os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            detected_name = manifest.get("name")

        final_name = skill_name or detected_name or os.path.basename(source_path)

        target_path = os.path.join(self.skills_dir, final_name)
        if os.path.exists(target_path):
            logger.info(f"Removing existing skill: {final_name}")
            shutil.rmtree(target_path)

        shutil.copytree(source_path, target_path)
        self.load_skills()

        msg = f"Skill '{final_name}' installed successfully"
        if source_info:
            msg += f" from {source_info}"
        logger.info(msg)
        return json.dumps({"status": "success", "message": msg, "skill_name": final_name})

    def remove_skill(self, skill_name: str) -> str:
        if skill_name not in self.skills:
            return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found"})

        skill = self.skills[skill_name]
        try:
            shutil.rmtree(skill.path)
            del self.skills[skill_name]
            msg = f"Skill '{skill_name}' removed successfully"
            logger.info(msg)
            return json.dumps({"status": "success", "message": msg})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    def list_skills(self) -> List[Dict]:
        return [skill.to_dict() for skill in self.skills.values()]

    def get_skill_info(self, skill_name: str) -> Optional[Dict]:
        if skill_name in self.skills:
            skill = self.skills[skill_name]
            info = skill.to_dict()
            info["content_length"] = len(skill.content)
            info["parameters"] = skill.parameters
            return info
        return None

    def reload_skills(self) -> None:
        self.load_skills()
        logger.info("Skills reloaded")
