import os
import csv
import io
from typing import List
from ..models import ExtractResult, MAX_FULL_TEXT, MAX_TRUNCATED_TEXT
from ..encoding_utils import decode_file


class CsvExtractor:
    def supported_extensions(self) -> List[str]:
        return ["csv"]

    def extract(self, file_path: str) -> ExtractResult:
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return ExtractResult.failed(f"无法读取文件: {e}")

        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            text_sample, encoding = decode_file(raw)
        except Exception as e:
            return ExtractResult.failed(f"读取 CSV 文件失败: {e}")

        try:
            sniffer = csv.Sniffer()
            sample = text_sample[:8192]
            delimiter = sniffer.sniff(sample).delimiter
            has_header = sniffer.has_header(sample)
        except Exception:
            delimiter = ","
            has_header = False

        reader = csv.reader(io.StringIO(text_sample), delimiter=delimiter)
        rows = list(reader)
        if not rows:
            return ExtractResult.success("(空 CSV 文件)", method="full", metadata={
                "row_count": 0, "encoding": encoding,
            })

        col_count = max(len(r) for r in rows)
        parts = []
        for i, row in enumerate(rows):
            padded = row + [""] * (col_count - len(row))
            parts.append("| " + " | ".join(padded) + " |")
        text = "\n".join(parts)

        if len(text) <= MAX_FULL_TEXT:
            return ExtractResult.success(text, method="full", metadata={
                "row_count": len(rows),
                "column_count": col_count,
                "has_header": has_header,
                "delimiter": repr(delimiter),
                "encoding": encoding,
                "size_bytes": file_size,
            })

        truncated = "\n".join(parts[:50])
        return ExtractResult.success(truncated, method="truncated", metadata={
            "row_count": len(rows),
            "column_count": col_count,
            "displayed_rows": 50,
            "has_header": has_header,
            "delimiter": repr(delimiter),
            "encoding": encoding,
            "size_bytes": file_size,
        })
