import random
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (CardWidget, PrimaryPushButton, PushButton,
                             TitleLabel, BodyLabel, StrongBodyLabel, isDarkTheme)

from .work_constants import WORK_JOBS, WORK_EVENTS
from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
)


class JobCard(CardWidget):
    job_selected = pyqtSignal(str)

    def __init__(self, job: dict, selected: bool = False, parent=None):
        super().__init__(parent)
        self._job = job
        self._selected = selected
        self._locked = False
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        icon = BodyLabel(self._job["icon"])
        icon.setFixedWidth(36)
        icon.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = StrongBodyLabel(self._job["name"])
        info.addWidget(name)

        desc_label = BodyLabel(self._job["desc"])
        desc_label.setStyleSheet("font-size: 11px; color: #777;")
        info.addWidget(desc_label)

        dur_label = BodyLabel(
            f"⏱ {self._job['duration_minutes']}分钟  |  🍊 +{self._job['earnings']}"
        )
        dur_label.setStyleSheet("font-size: 11px; color: #FF9800; font-weight: bold;")
        info.addWidget(dur_label)

        layout.addLayout(info, 1)

        self._check_mark = BodyLabel("✓")
        self._check_mark.setFixedWidth(24)
        self._check_mark.setAlignment(Qt.AlignCenter)
        self._check_mark.setStyleSheet(
            "font-size: 18px; color: #4CAF50; font-weight: bold; background: transparent;"
        )
        self._check_mark.setVisible(self._selected)
        layout.addWidget(self._check_mark)

        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._check_mark.setVisible(selected)
        self._update_style()

    def set_locked(self, locked: bool, unlock_level: int = 0):
        self._locked = locked
        self.setEnabled(not locked)
        self.setCursor(Qt.PointingHandCursor if not locked else Qt.ArrowCursor)
        self._update_style()

    def _update_style(self):
        if self._selected:
            accent = self._job.get("accent", "#FF8C00")
            self.setStyleSheet(f"""
                JobCard {{
                    border: 2px solid {accent};
                    border-radius: 8px;
                    background-color: {accent}15;
                }}
            """)
        elif self._locked:
            self.setStyleSheet("""
                JobCard {
                    border: 1px solid rgba(0,0,0,0.04);
                    border-radius: 8px;
                    opacity: 0.45;
                }
            """)
        else:
            self.setStyleSheet("""
                JobCard {
                    border: 1px solid rgba(0,0,0,0.08);
                    border-radius: 8px;
                }
                JobCard:hover {
                    border: 1px solid rgba(0,0,0,0.18);
                    background-color: rgba(0,0,0,0.02);
                }
            """)

    def mousePressEvent(self, event):
        if not self._locked:
            self.job_selected.emit(self._job["key"])
        super().mousePressEvent(event)


class WorkPage(QWidget):
    back_requested = pyqtSignal()
    work_completed = pyqtSignal(int, str)

    def __init__(self, orange_manager=None, attr_manager=None, parent=None):
        super().__init__(parent)
        self._orange_manager = orange_manager
        self._attr_manager = attr_manager
        self._location_key = "fruit_shop"
        self._selected_job = None
        self._working = False
        self._work_remaining = 0
        self._work_total = 0

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_work_tick)

        self._init_ui()

    def open_location(self, location_key: str):
        self._location_key = location_key
        self._selected_job = None
        self._working = False
        self._timer.stop()
        self._refresh_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        back_btn = PushButton("◀ 回都市")
        back_btn.setFixedHeight(30)
        back_btn.clicked.connect(self._on_back)
        header.addWidget(back_btn)

        self._title_label = TitleLabel("🍊 欧润吉水果店")
        header.addWidget(self._title_label)
        header.addStretch()
        layout.addLayout(header)

        self._status_area = QWidget()
        self._status_layout = QVBoxLayout(self._status_area)
        self._status_layout.setContentsMargins(0, 0, 0, 0)
        self._status_layout.setSpacing(8)
        self._status_area.hide()
        layout.addWidget(self._status_area)

        self._select_label = StrongBodyLabel("选择工作：")
        layout.addWidget(self._select_label)

        self._jobs_layout = QVBoxLayout()
        self._jobs_layout.setSpacing(8)
        layout.addLayout(self._jobs_layout)

        layout.addStretch()
        self._refresh_ui()

    def _refresh_ui(self):
        data = WORK_JOBS.get(self._location_key, WORK_JOBS["fruit_shop"])
        self._title_label.setText(data["name"])

        for i in reversed(range(self._jobs_layout.count())):
            w = self._jobs_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        doro_level = self._orange_manager.doro_level if self._orange_manager else 1

        if self._working:
            self._select_label.hide()
            self._status_area.show()
            for i in reversed(range(self._status_layout.count())):
                w = self._status_layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

            job = self._selected_job or {}
            status_text = BodyLabel(f"🔨 {job.get('name', '')} 进行中...")
            status_text.setStyleSheet("font-size: 14px; font-weight: bold;")
            self._status_layout.addWidget(status_text)

            mins = self._work_remaining // 60
            secs = self._work_remaining % 60
            time_text = BodyLabel(f"⏱ 剩余 {mins}:{secs:02d}")
            time_text.setStyleSheet("font-size: 22px; color: #FF8C00; font-weight: bold;")
            self._status_layout.addWidget(time_text)

            self._progress_label = BodyLabel("")
            self._progress_label.setStyleSheet("font-size: 11px; color: #888;")
            self._status_layout.addWidget(self._progress_label)

            cancel_btn = PushButton("❌ 取消打工")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(self._cancel_work)
            self._status_layout.addWidget(cancel_btn)
        else:
            self._select_label.show()
            self._status_area.hide()

            self._job_cards = []
            accent = data.get("accent", "#FF8C00")
            for job in data["jobs"]:
                job["accent"] = accent
                locked = doro_level < job["unlock_level"]
                card = JobCard(job)
                card.job_selected.connect(self._on_job_selected)
                if locked:
                    card.set_locked(True, job["unlock_level"])
                self._job_cards.append(card)
                self._jobs_layout.addWidget(card)

            start_btn = PrimaryPushButton("▶ 开始打工")
            start_btn.setFixedHeight(36)
            start_btn.clicked.connect(self._start_work)
            start_btn.setEnabled(self._selected_job is not None)
            self._start_btn = start_btn
            self._jobs_layout.addWidget(start_btn)

    def _on_job_selected(self, job_key: str):
        data = WORK_JOBS.get(self._location_key, WORK_JOBS["fruit_shop"])
        for card in self._job_cards:
            card.set_selected(card._job["key"] == job_key)
        for job in data["jobs"]:
            if job["key"] == job_key:
                self._selected_job = job
                self._start_btn.setEnabled(True)
                self._start_btn.setText(f"▶ 开始打工 — {job['name']}")
                break

    def _start_work(self):
        if not self._selected_job or self._working:
            return
        self._working = True
        self._work_total = self._selected_job["duration_minutes"] * 60
        self._work_remaining = self._work_total
        self._timer.start()
        self._refresh_ui()

    def _cancel_work(self):
        self._working = False
        self._timer.stop()
        self._selected_job = None
        self._refresh_ui()

    def _on_work_tick(self):
        self._work_remaining -= 1
        if self._work_remaining > 0:
            for i in range(self._status_layout.count()):
                w = self._status_layout.itemAt(i).widget()
                if w and hasattr(w, 'setText') and '剩余' in (w.text() or ''):
                    mins = self._work_remaining // 60
                    secs = self._work_remaining % 60
                    w.setText(f"⏱ 剩余 {mins}:{secs:02d}")
                    break
            progress_pct = int((1 - self._work_remaining / self._work_total) * 100)
            if hasattr(self, '_progress_label'):
                bar = "█" * (progress_pct // 5) + "░" * (20 - progress_pct // 5)
                self._progress_label.setText(f"[{bar}] {progress_pct}%")
        else:
            self._timer.stop()
            self._working = False
            self._complete_work()

    def _complete_work(self):
        if not self._selected_job:
            return

        job = self._selected_job
        base_earnings = job["earnings"]

        event_triggered = None
        if random.random() < 0.25:
            weights = [e["prob"] for e in WORK_EVENTS]
            event_triggered = random.choices(WORK_EVENTS, weights=weights, k=1)[0]

        final_earnings = base_earnings
        if event_triggered:
            eff = event_triggered["effect"]
            if "earnings_multiplier" in eff:
                final_earnings *= eff["earnings_multiplier"]
            if "earnings_bonus" in eff:
                final_earnings += eff["earnings_bonus"]

        if self._orange_manager:
            self._orange_manager.add_oranges(final_earnings, f"打工-{job['name']}")

        if self._attr_manager and "effects" in job:
            attr_map_effects = {
                "hunger": ATTR_HUNGER,
                "mood": ATTR_MOOD,
                "cleanliness": ATTR_CLEANLINESS,
                "energy": ATTR_ENERGY,
            }
            for attr_key, delta in job["effects"].items():
                if attr_key in attr_map_effects:
                    self._attr_manager.update_attribute(attr_map_effects[attr_key], delta)

        if event_triggered:
            eff = event_triggered["effect"]
            attr_map_effects = {
                "hunger": ATTR_HUNGER,
                "mood": ATTR_MOOD,
                "cleanliness": ATTR_CLEANLINESS,
                "energy": ATTR_ENERGY,
            }
            for attr_key in ["mood", "cleanliness"]:
                if attr_key in eff and self._attr_manager:
                    self._attr_manager.update_attribute(attr_map_effects[attr_key], eff[attr_key])

        msg = f"打工完成！获得 🍊 × {final_earnings}"
        if event_triggered:
            msg += f"\n{event_triggered['name']}"

        self._selected_job = None
        self._refresh_ui()
        self.work_completed.emit(final_earnings, msg)

    def _on_back(self):
        if self._working:
            return
        self._selected_job = None
        self._timer.stop()
        self.back_requested.emit()

    def refresh_data(self):
        pass


class WorkCompletionPopup(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(280, 100)
        self.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #FF8C00;
            background: rgba(255, 248, 225, 0.92);
            border: 2px solid #FF8C00;
            border-radius: 16px;
            padding: 10px;
        """)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_message(self, message: str):
        self.setText(message)
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.center().x() - 140,
                parent_rect.center().y() - 50,
            )
        self.show()
        self._hide_timer.start(3000)
