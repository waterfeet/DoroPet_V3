from dataclasses import dataclass, field
from typing import Dict
from src.core.pet_constants import STATUS_THRESHOLDS, STATUS_COLORS

@dataclass
class PetAttribute:
    name: str
    value: float = 100.0
    max_value: float = 100.0
    min_value: float = 0.0
    decay_rate: float = 1.0
    thresholds: Dict[str, float] = field(default_factory=lambda: STATUS_THRESHOLDS.copy())
    color_map: Dict[str, str] = field(default_factory=lambda: STATUS_COLORS.copy())
    
    def get_status(self) -> str:
        if self.value < self.thresholds["critical"]:
            return "critical"
        elif self.value < self.thresholds["warning"]:
            return "warning"
        else:
            return "good"
    
    def get_color(self) -> str:
        return self.color_map.get(self.get_status(), "#4CAF50")
    
    def get_status_text(self) -> str:
        status = self.get_status()
        if status == "critical":
            return "危急"
        elif status == "warning":
            return "警告"
        else:
            return "良好"
