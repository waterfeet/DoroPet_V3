import os
import json
import shutil
import uuid
import time
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from .models import AttachmentInfo, FileCategory, get_file_config
from .pipeline import get_pipeline


class AttachmentStorage:
    _instance: Optional["AttachmentStorage"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.root = os.path.join(base, "DoroPet", "attachments")
        os.makedirs(self.root, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "AttachmentStorage":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def store_without_extract(self, source_path: str) -> AttachmentInfo:
        attachment_id = uuid.uuid4().hex[:12]
        dest_dir = os.path.join(self.root, attachment_id)
        os.makedirs(dest_dir, exist_ok=True)

        file_name = os.path.basename(source_path)
        ext = Path(file_name).suffix.lower().lstrip(".")
        dest_path = os.path.join(dest_dir, file_name)

        try:
            shutil.copy2(source_path, dest_path)
        except OSError as e:
            raise OSError(f"无法复制文件到附件仓库: {e}")

        size_bytes = os.path.getsize(dest_path)
        mime_type, _ = mimetypes.guess_type(file_name)
        config = get_file_config(ext)

        info = AttachmentInfo(
            id=attachment_id,
            file_name=file_name,
            file_path=dest_path,
            file_type=ext,
            category=config["category"],
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
            added_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        return info

    def apply_extract(self, info: AttachmentInfo, result):
        info.extracted_text = result.text
        info.extraction_method = result.method
        info.token_count = result.token_estimate
        dest_dir = os.path.join(self.root, info.id)
        os.makedirs(dest_dir, exist_ok=True)
        meta_path = os.path.join(dest_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "extract_result": {
                    "method": result.method,
                    "token_estimate": result.token_estimate,
                    "metadata": result.metadata,
                    "error": result.error,
                }
            }, f, ensure_ascii=False, indent=2)

    def store(self, source_path: str) -> AttachmentInfo:
        attachment_id = uuid.uuid4().hex[:12]
        dest_dir = os.path.join(self.root, attachment_id)
        os.makedirs(dest_dir, exist_ok=True)

        file_name = os.path.basename(source_path)
        ext = Path(file_name).suffix.lower().lstrip(".")
        dest_path = os.path.join(dest_dir, file_name)

        try:
            shutil.copy2(source_path, dest_path)
        except OSError as e:
            raise OSError(f"无法复制文件到附件仓库: {e}")

        size_bytes = os.path.getsize(dest_path)
        mime_type, _ = mimetypes.guess_type(file_name)
        config = get_file_config(ext)

        info = AttachmentInfo(
            id=attachment_id,
            file_name=file_name,
            file_path=dest_path,
            file_type=ext,
            category=config["category"],
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
            added_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        pipeline = get_pipeline()
        result = pipeline.extract(dest_path)
        info.extracted_text = result.text
        info.extraction_method = result.method
        info.token_count = result.token_estimate

        meta_path = os.path.join(dest_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "extract_result": {
                    "method": result.method,
                    "token_estimate": result.token_estimate,
                    "metadata": result.metadata,
                    "error": result.error,
                }
            }, f, ensure_ascii=False, indent=2)

        return info

    def get_path(self, attachment_id: str) -> Optional[str]:
        for entry in os.scandir(self.root):
            if entry.name == attachment_id and entry.is_dir():
                for f in os.scandir(entry.path):
                    if f.is_file() and f.name != "meta.json":
                        return f.path
        return None

    def apply_extract_by_id(self, attachment_id: str, result):
        dest_dir = os.path.join(self.root, attachment_id)
        os.makedirs(dest_dir, exist_ok=True)
        meta_path = os.path.join(dest_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "extract_result": {
                    "method": result.method,
                    "token_estimate": result.token_estimate,
                    "metadata": result.metadata,
                    "error": result.error,
                }
            }, f, ensure_ascii=False, indent=2)

    def load_info(self, attachment_id: str) -> Optional[AttachmentInfo]:
        dir_path = os.path.join(self.root, attachment_id)
        if not os.path.isdir(dir_path):
            return None
        file_path = None
        for entry in os.scandir(dir_path):
            if entry.is_file() and entry.name != "meta.json":
                file_path = entry.path
                break
        if not file_path:
            return None
        file_name = os.path.basename(file_path)
        ext = Path(file_name).suffix.lower().lstrip(".")
        size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        mime_type, _ = mimetypes.guess_type(file_name)
        config = get_file_config(ext)
        info = AttachmentInfo(
            id=attachment_id,
            file_name=file_name,
            file_path=file_path,
            file_type=ext,
            category=config["category"],
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
            added_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        meta = self.get_meta(attachment_id)
        ext_result = meta.get("extract_result", {})
        if ext_result:
            info.extraction_method = ext_result.get("method", "none")
            info.token_count = ext_result.get("token_estimate", 0)
        return info

    def get_meta(self, attachment_id: str) -> Dict[str, Any]:
        meta_path = os.path.join(self.root, attachment_id, "meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def delete(self, attachment_id: str):
        dir_path = os.path.join(self.root, attachment_id)
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)

    def get_total_size(self) -> int:
        total = 0
        for dirpath, _, filenames in os.walk(self.root):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        return total

    def get_total_size_display(self) -> str:
        size = self.get_total_size()
        if size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.2f}GB"

    def clean_old(self, days: int = 30):
        cutoff = time.time() - days * 86400
        for entry in os.scandir(self.root):
            if entry.is_dir():
                meta_path = os.path.join(entry.path, "meta.json")
                mtime = os.path.getmtime(meta_path) if os.path.exists(meta_path) else entry.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(entry.path, ignore_errors=True)

    def clean_all(self):
        for entry in os.scandir(self.root):
            if entry.is_dir():
                shutil.rmtree(entry.path, ignore_errors=True)
