import os
import re
from pathlib import Path
from typing import List
from ..models import ExtractResult, MAX_FULL_TEXT, MAX_TRUNCATED_TEXT, MAX_FILE_SIZE
from ..encoding_utils import decode_html_file


class HtmlExtractor:
    def supported_extensions(self) -> List[str]:
        return ["html", "htm"]

    def extract(self, file_path: str) -> ExtractResult:
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return ExtractResult.failed(f"无法读取文件: {e}")

        if file_size > MAX_FILE_SIZE:
            name = os.path.basename(file_path)
            return ExtractResult.failed(
                f"文件过大（{file_size / (1024*1024):.1f}MB），超过 1MB 限制。"
            )

        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            html, encoding = decode_html_file(raw)
        except Exception as e:
            return ExtractResult.failed(f"读取文件失败: {e}")

        text = self._extract_text(html)
        if not text.strip():
            return ExtractResult.failed("HTML 文件中未找到可提取的文本内容")

        if len(text) <= MAX_FULL_TEXT:
            return ExtractResult.success(text, method="full", metadata={
                "char_count": len(text),
                "encoding": encoding,
                "extractor": self._used_extractor,
                "size_bytes": file_size,
            })

        truncated = text[:MAX_TRUNCATED_TEXT]
        return ExtractResult.success(truncated, method="truncated", metadata={
            "char_count": len(text),
            "displayed_chars": MAX_TRUNCATED_TEXT,
            "encoding": encoding,
            "extractor": self._used_extractor,
            "size_bytes": file_size,
        })

    def _extract_text(self, html: str) -> str:
        result = self._try_beautifulsoup(html)
        if result is not None:
            self._used_extractor = "BeautifulSoup"
            return result

        self._used_extractor = "regex"
        return self._strip_tags_regex(html)

    def _try_beautifulsoup(self, html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
            except ImportError:
                return None

        for tag in soup(["script", "style", "noscript", "meta", "link", "head"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _strip_tags_regex(self, html: str) -> str:
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<head[^>]*>[\s\S]*?</head>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<!--[\s\S]*?-->", "", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#\d+;", " ", text)
        text = re.sub(r"\s+", " ", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
