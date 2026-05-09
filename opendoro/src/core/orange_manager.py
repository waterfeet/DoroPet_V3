from datetime import date
from PyQt5.QtCore import QObject, pyqtSignal

from src.core.pet_constants import (
    ORANGE_REWARDS, ORANGE_COMBO_BONUS, ORANGE_DAILY_FIRST_BONUS,
    ORANGE_INTERACTION_COST,
    DORO_LEVEL_THRESHOLDS, DORO_LEVEL_TITLES, DORO_LEVEL_DECAY_REDUCTION,
)
from src.core.database import PetDatabase
from src.core.logger import logger


class OrangeManager(QObject):
    orange_changed = pyqtSignal(int, int)
    orange_earned = pyqtSignal(int, int, str)
    level_changed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = PetDatabase()
        self._balance = 100
        self._today_earned = 0
        self._today_date = ""
        self._total_earned = 0
        self._current_combo = 0
        self._doro_level = 1
        self._total_pomodoros = 0
        self._load_state()

    def _load_state(self):
        data = self._db.load_orange_data()
        if data:
            self._balance = data.get("balance", 0)
            self._today_earned = data.get("today_earned", 0)
            self._today_date = data.get("today_date", "")
            self._total_earned = data.get("total_earned", 0)
            self._current_combo = data.get("current_combo", 0)
            self._doro_level = data.get("doro_level", 1)
            self._total_pomodoros = data.get("total_pomodoros", 0)

        today_str = date.today().isoformat()
        if self._today_date != today_str:
            self._today_earned = 0
            self._today_date = today_str
            self._save_state()

    def _save_state(self):
        self._db.save_orange_data({
            "balance": self._balance,
            "today_earned": self._today_earned,
            "today_date": self._today_date,
            "total_earned": self._total_earned,
            "current_combo": self._current_combo,
            "doro_level": self._doro_level,
            "total_pomodoros": self._total_pomodoros,
        })

    @property
    def balance(self):
        return self._balance

    @property
    def today_earned(self):
        return self._today_earned

    @property
    def total_earned(self):
        return self._total_earned

    @property
    def current_combo(self):
        return self._current_combo

    @property
    def doro_level(self):
        return self._doro_level

    @property
    def doro_title(self):
        return DORO_LEVEL_TITLES.get(self._doro_level, "Doro崽")

    @property
    def total_pomodoros(self):
        return self._total_pomodoros

    @property
    def decay_reduction(self):
        return DORO_LEVEL_DECAY_REDUCTION.get(self._doro_level, 1.0)

    def get_next_level_threshold(self):
        next_level = self._doro_level + 1
        if next_level in DORO_LEVEL_THRESHOLDS:
            return DORO_LEVEL_THRESHOLDS[next_level]
        return None

    def earn_oranges(self, focus_minutes: int):
        self._ensure_today_reset()

        base_reward = ORANGE_REWARDS.get(focus_minutes, max(50, (focus_minutes // 15) * 50))

        bonus = 0
        reason_parts = []

        if self._today_earned == 0:
            bonus += ORANGE_DAILY_FIRST_BONUS
            reason_parts.append(f"每日首完成 +{ORANGE_DAILY_FIRST_BONUS}")

        self._current_combo += 1
        combo_bonus = 0
        for threshold, bonus_val in sorted(ORANGE_COMBO_BONUS.items()):
            if self._current_combo >= threshold:
                combo_bonus = bonus_val
        if combo_bonus > 0:
            bonus += combo_bonus
            reason_parts.append(f"连击 x{self._current_combo} +{combo_bonus}")

        total_earned = base_reward + bonus
        self._balance += total_earned
        self._today_earned += total_earned
        self._total_earned += total_earned

        self._total_pomodoros += 1
        self._check_level_up()

        self._save_state()

        reason = f"专注 {focus_minutes} 分钟 = {base_reward}🍊"
        if reason_parts:
            reason += "（" + "，".join(reason_parts) + "）"

        logger.info(f"Earned {total_earned} oranges. Balance: {self._balance}, Combo: {self._current_combo}")
        self.orange_earned.emit(total_earned, self._balance, reason)
        self.orange_changed.emit(self._balance, self._today_earned)
        return total_earned

    def interrupt_focus(self):
        self._current_combo = 0
        self._save_state()

    def spend_oranges(self, amount: int, purpose: str = "") -> bool:
        if amount <= 0:
            return False
        if self._balance < amount:
            logger.warning(f"Not enough oranges to spend {amount} for {purpose}. Balance: {self._balance}")
            return False

        self._balance -= amount
        self._save_state()

        logger.info(f"Spent {amount} oranges for {purpose}. Balance: {self._balance}")
        self.orange_changed.emit(self._balance, self._today_earned)
        return True

    def can_afford(self, purpose: str) -> bool:
        cost = ORANGE_INTERACTION_COST.get(purpose, 1)
        return self._balance >= cost

    def set_level_for_test(self, level: int):
        old_level = self._doro_level
        self._doro_level = max(1, min(10, level))
        needed = 0
        for lv in sorted(DORO_LEVEL_THRESHOLDS.keys()):
            if lv <= self._doro_level:
                needed = DORO_LEVEL_THRESHOLDS[lv]
        if self._total_pomodoros < needed:
            self._total_pomodoros = needed
        self._save_state()
        logger.info(f"[TEST] Doro level set to {self._doro_level} (pomodoros={self._total_pomodoros})")
        if self._doro_level != old_level:
            title = DORO_LEVEL_TITLES[self._doro_level]
            self.level_changed.emit(self._doro_level, title)
        self.orange_changed.emit(self._balance, self._today_earned)

    def set_oranges_for_test(self, amount: int):
        self._balance = max(0, amount)
        if self._total_earned < self._balance:
            self._total_earned = self._balance
        self._save_state()
        logger.info(f"[TEST] Orange balance set to {self._balance}")
        self.orange_changed.emit(self._balance, self._today_earned)

    def add_oranges(self, amount: int, reason: str = ""):
        if amount <= 0:
            return
        self._ensure_today_reset()
        self._balance += amount
        self._today_earned += amount
        self._total_earned += amount
        self._save_state()
        logger.info(f"Added {amount} oranges ({reason}). Balance: {self._balance}")
        self.orange_changed.emit(self._balance, self._today_earned)

    def _ensure_today_reset(self):
        today_str = date.today().isoformat()
        if self._today_date != today_str:
            self._today_earned = 0
            self._today_date = today_str
            self._current_combo = 0

    def _check_level_up(self):
        old_level = self._doro_level
        new_level = old_level
        for level in sorted(DORO_LEVEL_THRESHOLDS.keys(), reverse=True):
            if self._total_pomodoros >= DORO_LEVEL_THRESHOLDS[level]:
                new_level = level
                break

        if new_level > old_level:
            self._doro_level = new_level
            title = DORO_LEVEL_TITLES[new_level]
            logger.info(f"Doro leveled up! Level {old_level} → {new_level} ({title})")
            self.level_changed.emit(new_level, title)
