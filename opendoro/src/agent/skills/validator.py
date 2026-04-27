import os
import re
import json
import hashlib
import zipfile
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("DoroPet.Agent")


@dataclass
class SkillValidationResult:
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skill_name: str = ""
    skill_type: str = ""

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


class SkillValidator:
    MAX_SKILL_NAME_LENGTH = 64
    MAX_DESCRIPTION_LENGTH = 1024
    MAX_SKILLMD_SIZE_BYTES = 512 * 1024
    MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024
    ALLOWED_ARCHIVE_EXTENSIONS = {".zip"}
    BLOCKED_FILE_EXTENSIONS = {".exe", ".dll", ".so", ".dylib", ".bin", ".sys", ".scr"}
    BLOCKED_DIR_PATTERNS = ["..", "/etc", "C:", "\\\\", "~"]

    def validate_skill_directory(self, skill_path: str) -> SkillValidationResult:
        result = SkillValidationResult()

        if not os.path.exists(skill_path):
            result.add_error(f"Skill directory does not exist: {skill_path}")
            return result

        if not os.path.isdir(skill_path):
            result.add_error(f"Path is not a directory: {skill_path}")
            return result

        skill_md = os.path.join(skill_path, "SKILL.md")
        manifest = os.path.join(skill_path, "manifest.json")

        if not os.path.exists(skill_md) and not os.path.exists(manifest):
            result.add_error(f"No SKILL.md or manifest.json found in {skill_path}")
            return result

        if os.path.exists(skill_md):
            md_result = self._validate_skill_md(skill_md)
            result.errors.extend(md_result.errors)
            result.warnings.extend(md_result.warnings)
            result.skill_name = md_result.skill_name
            result.skill_type = md_result.skill_type

        if os.path.exists(manifest):
            manifest_result = self._validate_manifest(manifest)
            result.errors.extend(manifest_result.errors)
            result.warnings.extend(manifest_result.warnings)
            if not result.skill_name:
                result.skill_name = manifest_result.skill_name

        path_result = self._validate_path_content(skill_path)
        result.errors.extend(path_result.errors)
        result.warnings.extend(path_result.warnings)

        if not result.skill_name:
            result.add_error("Skill name cannot be determined.")

        result.is_valid = len(result.errors) == 0
        return result

    def _validate_skill_md(self, md_path: str) -> SkillValidationResult:
        result = SkillValidationResult()

        try:
            file_size = os.path.getsize(md_path)
            if file_size > self.MAX_SKILLMD_SIZE_BYTES:
                result.add_error(f"SKILL.md size {file_size} exceeds limit {self.MAX_SKILLMD_SIZE_BYTES}")

            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            front_matter = self._parse_yaml_front_matter(content)
            if not front_matter:
                result.add_warning("No YAML front matter found in SKILL.md")
            else:
                name = front_matter.get("name", "")
                if name:
                    if len(name) > self.MAX_SKILL_NAME_LENGTH:
                        result.add_error(f"Skill name too long: {len(name)} > {self.MAX_SKILL_NAME_LENGTH}")
                    if not re.match(r'^[\w\-\.]+$', name):
                        result.add_warning(f"Skill name '{name}' contains special characters")
                    result.skill_name = name

                description = front_matter.get("description", "")
                if len(description) > self.MAX_DESCRIPTION_LENGTH:
                    result.add_warning(f"Description exceeds recommended length")

                entry_point = front_matter.get("entry_point", "")
                if entry_point:
                    if ".." in entry_point or ":" not in entry_point:
                        result.add_error(f"Invalid entry_point format: {entry_point}")
                    result.skill_type = "executable"
                else:
                    result.skill_type = "document"

        except Exception as e:
            result.add_error(f"Failed to read SKILL.md: {e}")

        return result

    def _validate_manifest(self, manifest_path: str) -> SkillValidationResult:
        result = SkillValidationResult()

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            if not isinstance(manifest, dict):
                result.add_error("manifest.json must be a JSON object")
                return result

            name = manifest.get("name", "")
            if name:
                if len(name) > self.MAX_SKILL_NAME_LENGTH:
                    result.add_error(f"Skill name too long: {len(name)} > {self.MAX_SKILL_NAME_LENGTH}")
                result.skill_name = name

            entry_point = manifest.get("entry_point", "")
            if entry_point:
                if ".." in entry_point:
                    result.add_error(f"Suspicious entry_point: {entry_point}")
                result.skill_type = "executable"

        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in manifest.json: {e}")
        except Exception as e:
            result.add_error(f"Failed to read manifest.json: {e}")

        return result

    def _validate_path_content(self, skill_path: str) -> SkillValidationResult:
        result = SkillValidationResult()
        total_size = 0

        for root, dirs, files in os.walk(skill_path):
            for blocked in self.BLOCKED_DIR_PATTERNS:
                if blocked in root:
                    result.add_error(f"Suspicious directory path: {root}")
                    return result

            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    size = os.path.getsize(file_path)
                    total_size += size

                    _, ext = os.path.splitext(filename)
                    if ext.lower() in self.BLOCKED_FILE_EXTENSIONS:
                        result.add_error(f"Blocked file type: {filename}")

                    if size > 100 * 1024 * 1024:
                        result.add_error(f"File too large: {filename} ({size} bytes)")
                except OSError:
                    pass

        if total_size > 200 * 1024 * 1024:
            result.add_error(f"Total skill size {total_size} bytes exceeds 200MB limit")

        return result

    def _parse_yaml_front_matter(self, content: str) -> Optional[Dict]:
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return None
        yaml_content = match.group(1)
        try:
            import yaml
            return yaml.safe_load(yaml_content) or {}
        except Exception:
            metadata = {}
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip().strip('"\'')
            return metadata

    def validate_zip_archive(self, zip_path: str) -> SkillValidationResult:
        result = SkillValidationResult()

        try:
            archive_size = os.path.getsize(zip_path)
            if archive_size > self.MAX_ZIP_SIZE_BYTES:
                result.add_error(f"Archive size {archive_size} exceeds limit {self.MAX_ZIP_SIZE_BYTES}")
                return result

            total_uncompressed = 0
            max_uncompressed = 500 * 1024 * 1024

            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                if len(names) > 5000:
                    result.add_error(f"Too many files in archive: {len(names)}")

                for name in names:
                    if any(blocked in name for blocked in self.BLOCKED_DIR_PATTERNS):
                        result.add_error(f"Suspicious path in archive: {name}")
                        break

                    _, ext = os.path.splitext(name)
                    if ext.lower() in self.BLOCKED_FILE_EXTENSIONS:
                        result.add_error(f"Blocked file type in archive: {name}")

                    info = zf.getinfo(name)
                    total_uncompressed += info.file_size
                    if total_uncompressed > max_uncompressed:
                        result.add_error("Archive exceeds uncompressed size limit (possible zip bomb)")
                        break

        except zipfile.BadZipFile:
            result.add_error("Corrupted or invalid ZIP archive")
        except Exception as e:
            result.add_error(f"Archive validation failed: {e}")

        result.is_valid = len(result.errors) == 0
        return result


def compute_skill_hash(skill_path: str) -> str:
    hasher = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(skill_path)):
        for filename in sorted(files):
            file_path = os.path.join(root, filename)
            try:
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        hasher.update(chunk)
            except OSError:
                pass
    return hasher.hexdigest()
