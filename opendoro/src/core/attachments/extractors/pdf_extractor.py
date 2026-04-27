import os
from typing import List
from ..models import ExtractResult, MAX_FULL_TEXT, MAX_TRUNCATED_TEXT, MAX_FILE_SIZE


class PdfExtractor:
    def supported_extensions(self) -> List[str]:
        return ["pdf"]

    def extract(self, file_path: str) -> ExtractResult:
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return ExtractResult.failed(f"无法读取文件: {e}")

        if file_size > MAX_FILE_SIZE:
            name = os.path.basename(file_path)
            return ExtractResult.failed(
                f"PDF 文件过大（{file_size / (1024*1024):.1f}MB），超过 1MB 限制。"
            )

        result = self._try_pymupdf(file_path)
        if result is not None:
            return result
        result = self._try_pdfplumber(file_path)
        if result is not None:
            return result
        return ExtractResult.failed(
            "未安装 PDF 提取库（PyMuPDF 或 pdfplumber），无法提取 .pdf 文件\n"
            "请安装: pip install PyMuPDF"
        )

    def _try_pymupdf(self, file_path: str):
        try:
            import fitz
        except ImportError:
            return None

        try:
            doc = fitz.open(file_path)
        except Exception:
            return None

        page_count = len(doc)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        max_pages = min(page_count, 50)
        text_buffer = []
        total_chars = 0

        try:
            for i in range(max_pages):
                text = doc[i].get_text()
                if text.strip():
                    text_buffer.append(text)
                    total_chars += len(text)
                    if total_chars >= MAX_FULL_TEXT:
                        break
        finally:
            doc.close()

        text = "\n\n".join(text_buffer)
        actual_pages = len(text_buffer)

        if not text.strip():
            return ExtractResult.failed("PDF 文件前 50 页中未找到可提取的文本内容（可能是扫描件）")

        if len(text) <= MAX_FULL_TEXT:
            return ExtractResult.success(text, method="full", metadata={
                "page_count": page_count,
                "extracted_pages": actual_pages,
                "engine": "PyMuPDF",
                "char_count": len(text),
                "size_bytes": file_size,
            })

        truncated = text[:MAX_TRUNCATED_TEXT]
        return ExtractResult.success(truncated, method="truncated", metadata={
            "page_count": page_count,
            "extracted_pages": actual_pages,
            "engine": "PyMuPDF",
            "char_count": len(text),
            "displayed_chars": MAX_TRUNCATED_TEXT,
            "size_bytes": file_size,
        })

    def _try_pdfplumber(self, file_path: str):
        try:
            import pdfplumber
        except ImportError:
            return None

        try:
            parts = []
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        parts.append(text)

            if not parts:
                return ExtractResult.failed("PDF 文件中未找到可提取的文本内容")

            text = "\n\n".join(parts)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            if len(text) <= MAX_FULL_TEXT:
                return ExtractResult.success(text, method="full", metadata={
                    "page_count": page_count,
                    "engine": "pdfplumber",
                    "char_count": len(text),
                    "size_bytes": file_size,
                })

            truncated = text[:MAX_TRUNCATED_TEXT]
            return ExtractResult.success(truncated, method="truncated", metadata={
                "page_count": page_count,
                "engine": "pdfplumber",
                "char_count": len(text),
                "displayed_chars": MAX_TRUNCATED_TEXT,
                "size_bytes": file_size,
            })
        except Exception as e:
            return ExtractResult.failed(f"pdfplumber 提取失败: {e}")
