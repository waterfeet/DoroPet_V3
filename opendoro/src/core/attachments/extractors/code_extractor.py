import os
from pathlib import Path
from typing import List
from ..models import ExtractResult
from ..encoding_utils import decode_file

CODE_EXTENSIONS = {
    "py", "js", "ts", "tsx", "jsx", "java", "c", "cpp", "cc", "cxx", "h", "hpp",
    "go", "rs", "swift", "kt", "kts", "rb", "php", "sh", "bash", "zsh", "bat",
    "ps1", "sql", "css", "scss", "less", "vue", "svelte", "xml",
    "yaml", "yml", "toml", "json", "ini", "cfg", "conf", "dockerfile", "makefile",
    "cmake", "r", "pl", "lua", "dart", "scala", "clj", "cljs", "ex", "exs",
    "elm", "hs", "ml", "nim", "zig", "v", "fs", "fsx",
}

MAX_CODE_SIZE = 500 * 1024


class CodeExtractor:
    def supported_extensions(self) -> List[str]:
        return sorted(CODE_EXTENSIONS)

    def extract(self, file_path: str) -> ExtractResult:
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return ExtractResult.failed(f"无法读取文件: {e}")

        if file_size > MAX_CODE_SIZE:
            name = os.path.basename(file_path)
            return ExtractResult.failed(
                f"代码文件过大（{file_size / 1024:.1f}KB），超过 500KB 限制。"
            )

        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            text, encoding = decode_file(raw)
        except Exception as e:
            return ExtractResult.failed(f"读取代码文件失败: {e}")

        ext = Path(file_path).suffix.lower().lstrip(".")
        line_count = text.count("\n") + 1 if text else 0

        return ExtractResult.success(text, method="full", metadata={
            "char_count": len(text),
            "line_count": line_count,
            "language": ext,
            "encoding": encoding,
        })
