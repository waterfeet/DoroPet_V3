from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

MAX_FULL_TEXT = 10000
MAX_TRUNCATED_TEXT = 3000
MAX_FILE_SIZE = 5 * 1024 * 1024


class FileCategory(Enum):
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    CODE = "code"
    DATA = "data"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    WEB = "web"
    ARCHIVE = "archive"
    OTHER = "other"


FILE_TYPE_CONFIG: Dict[str, Dict[str, Any]] = {
    "docx": {"category": FileCategory.DOCUMENT, "icon": "📄", "color": "#2196F3"},
    "doc": {"category": FileCategory.DOCUMENT, "icon": "📄", "color": "#2196F3"},
    "pdf": {"category": FileCategory.DOCUMENT, "icon": "📕", "color": "#F44336"},
    "pptx": {"category": FileCategory.DOCUMENT, "icon": "📽", "color": "#FF9800"},
    "ppt": {"category": FileCategory.DOCUMENT, "icon": "📽", "color": "#FF9800"},
    "xlsx": {"category": FileCategory.SPREADSHEET, "icon": "📊", "color": "#4CAF50"},
    "xls": {"category": FileCategory.SPREADSHEET, "icon": "📊", "color": "#4CAF50"},
    "csv": {"category": FileCategory.SPREADSHEET, "icon": "📊", "color": "#4CAF50"},
    "txt": {"category": FileCategory.DOCUMENT, "icon": "📝", "color": "#9E9E9E"},
    "log": {"category": FileCategory.DOCUMENT, "icon": "📝", "color": "#9E9E9E"},
    "md": {"category": FileCategory.DOCUMENT, "icon": "📘", "color": "#2196F3"},
    "json": {"category": FileCategory.DATA, "icon": "📋", "color": "#795548"},
    "xml": {"category": FileCategory.DATA, "icon": "📋", "color": "#795548"},
    "yaml": {"category": FileCategory.DATA, "icon": "📋", "color": "#795548"},
    "yml": {"category": FileCategory.DATA, "icon": "📋", "color": "#795548"},
    "toml": {"category": FileCategory.DATA, "icon": "📋", "color": "#795548"},
    "html": {"category": FileCategory.WEB, "icon": "🌐", "color": "#E91E63"},
    "htm": {"category": FileCategory.WEB, "icon": "🌐", "color": "#E91E63"},
    "py": {"category": FileCategory.CODE, "icon": "🐍", "color": "#6A1B9A"},
    "js": {"category": FileCategory.CODE, "icon": "💻", "color": "#F7DF1E"},
    "ts": {"category": FileCategory.CODE, "icon": "💻", "color": "#3178C6"},
    "tsx": {"category": FileCategory.CODE, "icon": "💻", "color": "#3178C6"},
    "jsx": {"category": FileCategory.CODE, "icon": "💻", "color": "#F7DF1E"},
    "java": {"category": FileCategory.CODE, "icon": "💻", "color": "#6A1B9A"},
    "c": {"category": FileCategory.CODE, "icon": "💻", "color": "#6A1B9A"},
    "cpp": {"category": FileCategory.CODE, "icon": "💻", "color": "#6A1B9A"},
    "h": {"category": FileCategory.CODE, "icon": "💻", "color": "#6A1B9A"},
    "go": {"category": FileCategory.CODE, "icon": "💻", "color": "#00ADD8"},
    "rs": {"category": FileCategory.CODE, "icon": "💻", "color": "#DEA584"},
    "swift": {"category": FileCategory.CODE, "icon": "💻", "color": "#FF9800"},
    "kt": {"category": FileCategory.CODE, "icon": "💻", "color": "#6A1B9A"},
    "rb": {"category": FileCategory.CODE, "icon": "💻", "color": "#CC342D"},
    "php": {"category": FileCategory.CODE, "icon": "💻", "color": "#777BB4"},
    "sh": {"category": FileCategory.CODE, "icon": "💻", "color": "#4EAA25"},
    "bat": {"category": FileCategory.CODE, "icon": "💻", "color": "#4EAA25"},
    "ps1": {"category": FileCategory.CODE, "icon": "💻", "color": "#4EAA25"},
    "sql": {"category": FileCategory.CODE, "icon": "💻", "color": "#6A1B9A"},
    "css": {"category": FileCategory.CODE, "icon": "💻", "color": "#2965F1"},
    "scss": {"category": FileCategory.CODE, "icon": "💻", "color": "#CD6799"},
    "vue": {"category": FileCategory.CODE, "icon": "💻", "color": "#4CAF50"},
    "zip": {"category": FileCategory.ARCHIVE, "icon": "📦", "color": "#607D8B"},
    "tar": {"category": FileCategory.ARCHIVE, "icon": "📦", "color": "#607D8B"},
    "gz": {"category": FileCategory.ARCHIVE, "icon": "📦", "color": "#607D8B"},
    "7z": {"category": FileCategory.ARCHIVE, "icon": "📦", "color": "#607D8B"},
    "rar": {"category": FileCategory.ARCHIVE, "icon": "📦", "color": "#607D8B"},
    "png": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "jpg": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "jpeg": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "gif": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "webp": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "bmp": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "svg": {"category": FileCategory.IMAGE, "icon": "🖼", "color": "#FF9800"},
    "mp3": {"category": FileCategory.AUDIO, "icon": "🎵", "color": "#00BCD4"},
    "wav": {"category": FileCategory.AUDIO, "icon": "🎵", "color": "#00BCD4"},
    "ogg": {"category": FileCategory.AUDIO, "icon": "🎵", "color": "#00BCD4"},
    "m4a": {"category": FileCategory.AUDIO, "icon": "🎵", "color": "#00BCD4"},
    "flac": {"category": FileCategory.AUDIO, "icon": "🎵", "color": "#00BCD4"},
    "mp4": {"category": FileCategory.VIDEO, "icon": "🎬", "color": "#3F51B5"},
    "webm": {"category": FileCategory.VIDEO, "icon": "🎬", "color": "#3F51B5"},
    "avi": {"category": FileCategory.VIDEO, "icon": "🎬", "color": "#3F51B5"},
    "mov": {"category": FileCategory.VIDEO, "icon": "🎬", "color": "#3F51B5"},
    "mkv": {"category": FileCategory.VIDEO, "icon": "🎬", "color": "#3F51B5"},
}


def get_file_config(ext: str) -> Dict[str, Any]:
    return FILE_TYPE_CONFIG.get(ext.lower(), {"category": FileCategory.OTHER, "icon": "📎", "color": "#9E9E9E"})


@dataclass
class ExtractResult:
    text: str = ""
    method: str = "none"
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @classmethod
    def failed(cls, error: str) -> "ExtractResult":
        return cls(text="", method="failed", error=error)

    @classmethod
    def success(cls, text: str, method: str = "full", metadata: Dict[str, Any] = None) -> "ExtractResult":
        token_estimate = max(1, len(text) // 3)
        return cls(text=text, method=method, token_estimate=token_estimate,
                   metadata=metadata or {})


@dataclass
class AttachmentInfo:
    id: str = ""
    file_name: str = ""
    file_path: str = ""
    file_type: str = ""
    category: FileCategory = FileCategory.OTHER
    mime_type: str = ""
    size_bytes: int = 0
    extracted_text: str = ""
    extraction_method: str = "none"
    thumbnail_path: str = ""
    added_at: str = ""
    token_count: int = 0

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes}B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f}KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f}MB"
        return f"{self.size_bytes / (1024 * 1024 * 1024):.2f}GB"

    @property
    def icon(self) -> str:
        return get_file_config(self.file_type)["icon"]

    @property
    def color(self) -> str:
        return get_file_config(self.file_type)["color"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "category": self.category.value,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "extracted_text": self.extracted_text,
            "extraction_method": self.extraction_method,
            "thumbnail_path": self.thumbnail_path,
            "added_at": self.added_at,
            "token_count": self.token_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AttachmentInfo":
        return cls(
            id=data.get("id", ""),
            file_name=data.get("file_name", ""),
            file_path=data.get("file_path", ""),
            file_type=data.get("file_type", ""),
            category=FileCategory(data.get("category", "other")),
            mime_type=data.get("mime_type", ""),
            size_bytes=data.get("size_bytes", 0),
            extracted_text=data.get("extracted_text", ""),
            extraction_method=data.get("extraction_method", "none"),
            thumbnail_path=data.get("thumbnail_path", ""),
            added_at=data.get("added_at", ""),
            token_count=data.get("token_count", 0),
        )
