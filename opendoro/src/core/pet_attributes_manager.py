import time
from typing import Dict, Optional, Callable, List, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from src.core.pet_attribute import PetAttribute
from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, DEFAULT_VALUES, MAX_VALUES, MIN_VALUES,
    DECAY_RATES, RECOVERY_VALUES, LINKAGE_DECAY_MULTIPLIERS,
    LINKAGE_THRESHOLDS, INTERACTION_EFFECTS, INTENSITY_MULTIPLIERS,
    LEGACY_ACTION_MAPPING, INTERACTION_NAMES
)
from src.core.database import PetDatabase


class PetAttributesManager(QObject):
    attribute_changed = pyqtSignal(str, float, float)
    status_changed = pyqtSignal(str, str, str)
    interaction_triggered = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.attributes: Dict[str, PetAttribute] = {}
        self.decay_timer = QTimer()
        self.decay_timer.timeout.connect(self._on_decay_tick)
        self._bound_widgets: Dict[str, List[Tuple[Callable, Optional[Callable]]]] = {}
        self._db = PetDatabase()
        self._orange_manager = None
        self._init_default_attributes()
        self._load_state()

    def set_orange_manager(self, orange_manager):
        self._orange_manager = orange_manager

    def _init_default_attributes(self):
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            self.attributes[attr_name] = PetAttribute(
                name=attr_name,
                value=DEFAULT_VALUES[attr_name],
                max_value=MAX_VALUES[attr_name],
                min_value=MIN_VALUES[attr_name],
                decay_rate=DECAY_RATES[attr_name]
            )

    def _calculate_decay_rate(self, attr_name: str) -> float:
        rate = self.attributes[attr_name].decay_rate
        
        hunger = self.attributes[ATTR_HUNGER].value
        cleanliness = self.attributes[ATTR_CLEANLINESS].value
        energy = self.attributes[ATTR_ENERGY].value
        
        if attr_name == ATTR_MOOD:
            if hunger < LINKAGE_THRESHOLDS["hunger_critical"]:
                rate *= LINKAGE_DECAY_MULTIPLIERS["hunger_to_mood"]
            if cleanliness < LINKAGE_THRESHOLDS["cleanliness_warning"]:
                rate *= LINKAGE_DECAY_MULTIPLIERS["cleanliness_to_mood"]
        
        if energy < LINKAGE_THRESHOLDS["energy_critical"]:
            rate *= LINKAGE_DECAY_MULTIPLIERS["energy_to_all"]
        
        if self._orange_manager:
            rate *= self._orange_manager.decay_reduction
        
        return rate

    def _on_decay_tick(self):
        for attr_name in self.attributes:
            current = self.attributes[attr_name].value
            decay = self._calculate_decay_rate(attr_name) / 60.0
            new_value = max(self.attributes[attr_name].min_value, current - decay)
            
            old_status = self.attributes[attr_name].get_status()
            self.attributes[attr_name].value = new_value
            new_status = self.attributes[attr_name].get_status()
            
            self.attribute_changed.emit(attr_name, new_value, current)
            
            if old_status != new_status:
                self.status_changed.emit(attr_name, new_status, old_status)
        self._save_state()

    def start_decay_timer(self, interval_ms: int = 60000):
        self.decay_timer.start(interval_ms)

    def stop_decay_timer(self):
        self.decay_timer.stop()

    def update_attribute(self, attr_name: str, delta: float):
        if attr_name not in self.attributes:
            return
        
        attr = self.attributes[attr_name]
        old_value = attr.value
        old_status = attr.get_status()
        
        new_value = max(attr.min_value, min(attr.max_value, attr.value + delta))
        attr.value = new_value
        
        new_status = attr.get_status()
        
        self.attribute_changed.emit(attr_name, new_value, old_value)
        
        if old_status != new_status:
            self.status_changed.emit(attr_name, new_status, old_status)
        
        self._notify_bound_widgets(attr_name, new_value, new_status)
        self._save_state()

    def set_attribute(self, attr_name: str, value: float):
        if attr_name not in self.attributes:
            return
        
        attr = self.attributes[attr_name]
        old_value = attr.value
        old_status = attr.get_status()
        
        attr.value = max(attr.min_value, min(attr.max_value, value))
        
        new_status = attr.get_status()
        
        self.attribute_changed.emit(attr_name, attr.value, old_value)
        
        if old_status != new_status:
            self.status_changed.emit(attr_name, new_status, old_status)
        
        self._notify_bound_widgets(attr_name, attr.value, new_status)
        self._save_state()

    def get_attribute(self, attr_name: str) -> float:
        if attr_name in self.attributes:
            return self.attributes[attr_name].value
        return 0.0

    def get_all_attributes(self) -> Dict[str, float]:
        return {name: attr.value for name, attr in self.attributes.items()}

    def get_status(self, attr_name: str) -> str:
        if attr_name in self.attributes:
            return self.attributes[attr_name].get_status()
        return "good"

    def get_all_statuses(self) -> Dict[str, str]:
        return {name: attr.get_status() for name, attr in self.attributes.items()}

    def perform_interaction(self, interaction_type: str, intensity: str = "moderate"):
        if interaction_type in INTERACTION_EFFECTS:
            self._apply_interaction_effects(interaction_type, intensity)
            return
        
        if interaction_type == "feed":
            self.update_attribute(ATTR_HUNGER, RECOVERY_VALUES["feed"])
            self.interaction_triggered.emit(ATTR_HUNGER, "feed")
        elif interaction_type == "play":
            self.update_attribute(ATTR_MOOD, RECOVERY_VALUES["play"])
            self.interaction_triggered.emit(ATTR_MOOD, "play")
        elif interaction_type == "clean":
            self.update_attribute(ATTR_CLEANLINESS, RECOVERY_VALUES["clean"])
            self.interaction_triggered.emit(ATTR_CLEANLINESS, "clean")
        elif interaction_type == "rest":
            self.update_attribute(ATTR_ENERGY, RECOVERY_VALUES["rest"])
            self.interaction_triggered.emit(ATTR_ENERGY, "rest")

    def _apply_interaction_effects(self, interaction: str, intensity: str = "moderate"):
        if interaction not in INTERACTION_EFFECTS:
            return
        
        effects = INTERACTION_EFFECTS[interaction]
        multiplier = INTENSITY_MULTIPLIERS.get(intensity, 1.0)
        
        attr_map = {
            "hunger": ATTR_HUNGER,
            "mood": ATTR_MOOD,
            "cleanliness": ATTR_CLEANLINESS,
            "energy": ATTR_ENERGY
        }
        
        for attr_key, delta in effects.items():
            if attr_key in attr_map:
                adjusted_delta = delta * multiplier
                self.update_attribute(attr_map[attr_key], adjusted_delta)
        
        interaction_name = INTERACTION_NAMES.get(interaction, interaction)
        self.interaction_triggered.emit(interaction, intensity)

    def perform_interaction_v2(self, interaction: str, intensity: str = "moderate", 
                               attribute: Optional[str] = None, action: Optional[str] = None):
        if interaction:
            self._apply_interaction_effects(interaction, intensity)
            return
        
        if attribute and action:
            legacy_key = (action, intensity if intensity in INTENSITY_MULTIPLIERS else None)
            if legacy_key in LEGACY_ACTION_MAPPING:
                mapped_interaction, mapped_intensity = LEGACY_ACTION_MAPPING[legacy_key]
                self._apply_interaction_effects(mapped_interaction, mapped_intensity)
            else:
                default_interaction, default_intensity = LEGACY_ACTION_MAPPING.get(
                    (action, None), ("play_fun", "moderate")
                )
                self._apply_interaction_effects(default_interaction, default_intensity)

    def _save_state(self):
        attr_values = {name: attr.value for name, attr in self.attributes.items()}
        self._db.save_pet_attributes(attr_values, time.time())

    def _load_state(self):
        stored = self._db.load_pet_attributes()
        
        if not stored:
            return

        last_save_time = 0.0
        for attr_data in stored.values():
            if attr_data.get("last_save_time", 0.0) > last_save_time:
                last_save_time = attr_data["last_save_time"]

        if last_save_time > 0:
            current_time = time.time()
            offline_seconds = current_time - last_save_time
            offline_minutes = offline_seconds / 60.0
            
            if offline_minutes > 1:
                for attr_name in self.attributes:
                    attr_data = stored.get(attr_name)
                    stored_value = attr_data["value"] if attr_data else DEFAULT_VALUES[attr_name]
                    decay = self._calculate_decay_rate(attr_name) * offline_minutes
                    self.attributes[attr_name].value = max(
                        self.attributes[attr_name].min_value, stored_value - decay
                    )
            else:
                for attr_name in self.attributes:
                    attr_data = stored.get(attr_name)
                    if attr_data:
                        self.attributes[attr_name].value = attr_data["value"]
                    else:
                        self.attributes[attr_name].value = DEFAULT_VALUES[attr_name]
        else:
            for attr_name in self.attributes:
                attr_data = stored.get(attr_name)
                if attr_data:
                    self.attributes[attr_name].value = attr_data["value"]
                else:
                    self.attributes[attr_name].value = DEFAULT_VALUES[attr_name]

    def save_state(self):
        self._save_state()

    def load_state(self):
        self._load_state()

    def get_status_context_for_ai(self) -> str:
        contexts = []
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            status = self.get_status(attr_name)
            value = self.get_attribute(attr_name)
            if status in ["critical", "warning"]:
                chinese_name = ATTR_NAMES.get(attr_name, attr_name)
                status_text = "危急" if status == "critical" else "警告"
                contexts.append(f"{chinese_name}{value:.0f}%，状态{status_text}")
        
        if contexts:
            return "当前宠物状态：" + "；".join(contexts) + "。"
        return ""
    
    def bind_attribute_widget(self, attr_name: str, update_callback: Callable[[float], None], 
                               status_callback: Optional[Callable[[str], None]] = None):
        if attr_name not in self.attributes:
            return
        
        if attr_name not in self._bound_widgets:
            self._bound_widgets[attr_name] = []
        
        self._bound_widgets[attr_name].append((update_callback, status_callback))
        
        current_value = self.get_attribute(attr_name)
        update_callback(current_value)
        
        if status_callback:
            current_status = self.get_status(attr_name)
            status_callback(current_status)
    
    def unbind_attribute_widget(self, attr_name: str, update_callback: Callable):
        if attr_name not in self._bound_widgets:
            return
        
        self._bound_widgets[attr_name] = [
            (cb, status_cb) for cb, status_cb in self._bound_widgets[attr_name]
            if cb != update_callback
        ]
    
    def unbind_all_widgets(self, attr_name: str = None):
        if attr_name:
            self._bound_widgets.pop(attr_name, None)
        else:
            self._bound_widgets.clear()
    
    def _notify_bound_widgets(self, attr_name: str, value: float, status: str):
        if attr_name not in self._bound_widgets:
            return
        
        for update_callback, status_callback in self._bound_widgets[attr_name]:
            try:
                update_callback(value)
                if status_callback:
                    status_callback(status)
            except Exception as e:
                pass
