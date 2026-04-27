import os
import json
from typing import List, Optional
from ..models import ExtractResult, MAX_FULL_TEXT, MAX_TRUNCATED_TEXT, MAX_FILE_SIZE
from ..encoding_utils import decode_file


class TextExtractor:
    def supported_extensions(self) -> List[str]:
        return ["txt", "log", "md", "rst", "text", "cfg", "ini", "conf", "env", "properties"]

    def extract(self, file_path: str) -> ExtractResult:
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return ExtractResult.failed(f"无法读取文件: {e}")

        if file_size > MAX_FILE_SIZE:
            name = os.path.basename(file_path)
            return ExtractResult.failed(
                f"文件过大（{file_size / (1024*1024):.1f}MB），超过 1MB 限制。"
                f"请使用技能处理大文件。"
            )

        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            text, encoding = decode_file(raw)
        except Exception as e:
            return ExtractResult.failed(f"读取文件失败: {e}")

        if len(text) <= MAX_FULL_TEXT:
            return ExtractResult.success(text, method="full", metadata={
                "char_count": len(text),
                "encoding": encoding,
            })

        truncated = text[:MAX_TRUNCATED_TEXT]
        return ExtractResult.success(truncated, method="truncated", metadata={
            "char_count": len(text),
            "displayed_chars": MAX_TRUNCATED_TEXT,
            "encoding": encoding,
        })
