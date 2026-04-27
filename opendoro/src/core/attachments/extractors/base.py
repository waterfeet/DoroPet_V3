from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from ..models import ExtractResult


class BaseExtractor(ABC):
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        pass

    @abstractmethod
    def extract(self, file_path: str) -> ExtractResult:
        pass

    def can_handle(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower().lstrip(".")
        return ext in self.supported_extensions()
