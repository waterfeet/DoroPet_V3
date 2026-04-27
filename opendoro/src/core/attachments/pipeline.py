from pathlib import Path
from typing import List, Optional
from .models import ExtractResult
from .extractors.base import BaseExtractor
from .extractors.docx_extractor import DocxExtractor
from .extractors.excel_extractor import ExcelExtractor
from .extractors.csv_extractor import CsvExtractor
from .extractors.text_extractor import TextExtractor
from .extractors.code_extractor import CodeExtractor
from .extractors.html_extractor import HtmlExtractor


class FileExtractorPipeline:
    def __init__(self):
        self._extractors: List[BaseExtractor] = []
        self._register_defaults()

    def _register_defaults(self):
        self._extractors = [
            DocxExtractor(),
            ExcelExtractor(),
            CsvExtractor(),
            HtmlExtractor(),
            TextExtractor(),
            CodeExtractor(),
        ]

    def register(self, extractor):
        self._extractors.insert(0, extractor)

    def _find_extractor(self, file_path: str):
        ext = Path(file_path).suffix.lower().lstrip(".")
        for extractor in self._extractors:
            if ext in extractor.supported_extensions():
                return extractor
        return None

    def extract(self, file_path: str) -> ExtractResult:
        extractor = self._find_extractor(file_path)
        if extractor is None:
            ext = Path(file_path).suffix.lower().lstrip(".")
            return ExtractResult.failed(f"不支持的文件类型: .{ext}")
        return extractor.extract(file_path)

    def get_supported_extensions(self) -> List[str]:
        exts = set()
        for extractor in self._extractors:
            exts.update(extractor.supported_extensions())
        return sorted(exts)


_pipeline: Optional[FileExtractorPipeline] = None


def get_pipeline() -> FileExtractorPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = FileExtractorPipeline()
    return _pipeline
