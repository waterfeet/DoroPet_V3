from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QButtonGroup, QFrame
from qfluentwidgets import (
    PrimaryPushButton, PushButton, RadioButton, CardWidget,
    TitleLabel, SubtitleLabel, BodyLabel, StrongBodyLabel, isDarkTheme
)

from .pomodoro_timer import PomodoroTimer, TimerState
from .database import PomodoroDatabase
from .widgets import TimerRing
from src.core.orange_manager import OrangeManager
from src.core.logger import logger


class OrangeBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(26)
        self._update_style(False)

    def set_count(self, count: int):
        self.setText(f"🍊 × {count}")

    def _update_style(self, is_dark: bool):
        bg = "#3d2e1a" if is_dark else "#fff3e0"
        color = "#ffb74d" if is_dark else "#e65100"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                font-size: 13px;
                font-weight: bold;
                border-radius: 12px;
                padding: 2px 12px;
            }}
        """)

    def update_theme(self, is_dark: bool):
        self._update_style(is_dark)


class OrangeInfoCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("orangeInfoCard")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        self._title = StrongBodyLabel("🍊 奖励规则")
        layout.addWidget(self._title)

        self._rule_label = BodyLabel(
            "15m → 100🍊    25m → 150🍊\n"
            "45m → 300🍊    60m → 500🍊\n"
            "每日首次 +100  |  连击额外奖励"
        )
        self._rule_label.setStyleSheet("font-size: 11px; color: #888; line-height: 1.4;")
        layout.addWidget(self._rule_label)

    def update_theme(self, is_dark: bool):
        title_color = "#e0e0e0" if is_dark else "#333"
        text_color = "#aaa" if is_dark else "#777"
        self._title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {title_color};")
        self._rule_label.setStyleSheet(f"font-size: 11px; color: {text_color}; line-height: 1.4;")


class OrangeEarnedPopup(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #FF8C00;
            background: transparent;
        """)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_earned(self, amount: int, reason: str = ""):
        self.setText(f"+{amount} 🍊")
        self.adjustSize()
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2 - 40
            )
        self.show()
        self._hide_timer.start(2000)


class PomodoroInterface(QWidget):
    doro_focus_started = pyqtSignal()
    doro_pomodoro_completed = pyqtSignal(int)
    doro_focus_interrupted = pyqtSignal()
    doro_streak_warning = pyqtSignal(int)
    doro_idle_reminder = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PomodoroInterface")
        self.setMinimumSize(280, 300)

        self._db = PomodoroDatabase()
        self._timer = PomodoroTimer(self)
        self._orange_manager = None

        self._first_open_today = True

        self._init_ui()
        self._connect_signals()
        self._refresh_stats()

    def set_orange_manager(self, orange_manager: OrangeManager):
        self._orange_manager = orange_manager
        self._orange_manager.orange_changed.connect(self._on_orange_changed)
        self._refresh_orange_display()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self._title_label = TitleLabel("🍊 欧润吉钟")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        self._orange_badge = OrangeBadge()
        self._orange_badge.setFixedWidth(90)
        header_layout.addWidget(self._orange_badge)

        main_layout.addLayout(header_layout)

        timer_card = CardWidget()
        timer_card_layout = QVBoxLayout(timer_card)
        timer_card_layout.setContentsMargins(12, 14, 12, 14)
        timer_card_layout.setSpacing(6)

        timer_section = QWidget()
        timer_layout = QHBoxLayout(timer_section)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        timer_layout.setSpacing(0)

        self._timer_ring = TimerRing()
        self._timer_ring.setMinimumSize(140, 140)
        self._timer_ring.setMaximumSize(170, 170)
        timer_layout.addStretch()
        timer_layout.addWidget(self._timer_ring)
        timer_layout.addStretch()

        timer_card_layout.addWidget(timer_section)

        self._status_label = SubtitleLabel("点击「开始」开始一个欧润吉钟")
        self._status_label.setAlignment(Qt.AlignCenter)
        timer_card_layout.addWidget(self._status_label)

        status_line = QWidget()
        status_line_layout = QHBoxLayout(status_line)
        status_line_layout.setContentsMargins(0, 0, 0, 0)
        status_line_layout.setSpacing(6)

        self._today_badge = BodyLabel("今日🍊 × 0")
        self._today_badge.setAlignment(Qt.AlignCenter)
        status_line_layout.addWidget(self._today_badge)

        self._combo_badge = BodyLabel("")
        self._combo_badge.setAlignment(Qt.AlignCenter)
        self._combo_badge.setVisible(False)
        status_line_layout.addWidget(self._combo_badge)
        status_line_layout.addStretch()

        self._doro_level_label = BodyLabel("⭐ Lv.1")
        self._doro_level_label.setAlignment(Qt.AlignCenter)
        status_line_layout.addWidget(self._doro_level_label)

        timer_card_layout.addWidget(status_line)

        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)

        self._start_btn = PrimaryPushButton("▶ 开始")
        self._start_btn.setFixedHeight(30)
        self._pause_btn = PushButton("⏸ 暂停")
        self._pause_btn.setFixedHeight(30)
        self._stop_btn = PushButton("⏹ 停止")
        self._stop_btn.setFixedHeight(30)

        control_layout.addStretch()
        control_layout.addWidget(self._start_btn)
        control_layout.addWidget(self._pause_btn)
        control_layout.addWidget(self._stop_btn)
        control_layout.addStretch()

        timer_card_layout.addWidget(control_widget)

        main_layout.addWidget(timer_card, 1)

        self._start_btn.clicked.connect(self._on_start)
        self._pause_btn.clicked.connect(self._on_pause)
        self._stop_btn.clicked.connect(self._on_stop)

        self._update_button_states()

        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(2)

        dur_label = BodyLabel("时长")
        dur_label.setStyleSheet("font-size: 11px;")
        duration_layout.addWidget(dur_label)

        self._duration_group = QButtonGroup(self)
        self._duration_radios = {}
        duration_options = [15, 25, 45, 60]
        for mins in duration_options:
            radio = RadioButton(f"{mins}m")
            radio.setStyleSheet("""
                RadioButton {
                    font-size: 11px;
                    padding: 2px 6px;
                }
            """)
            if mins == 25:
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, m=mins: self._on_duration_changed(m, checked))
            self._duration_group.addButton(radio)
            self._duration_radios[mins] = radio
            duration_layout.addWidget(radio)

        duration_layout.addStretch()

        main_layout.addWidget(duration_widget)

        self._orange_info = OrangeInfoCard()
        main_layout.addWidget(self._orange_info)

        main_layout.addStretch()

        self._orange_popup = OrangeEarnedPopup(self)

        self._refresh_orange_display()

    def _connect_signals(self):
        self._timer.state_changed.connect(self._on_state_changed)
        self._timer.tick.connect(self._on_tick)
        self._timer.pomodoro_completed.connect(self._on_pomodoro_completed)
        self._timer.pomodoro_interrupted.connect(self._on_pomodoro_interrupted)
        self._timer.streak_warning.connect(self._on_streak_warning)

    def _on_duration_changed(self, minutes: int, checked: bool):
        if checked:
            self._timer.set_focus_duration(minutes)
            if self._timer.is_idle:
                mins = self._timer.get_focus_duration_minutes()
                self._timer_ring.set_time(mins * 60, mins * 60, "就绪")

    def _on_start(self):
        if self._timer.state == TimerState.IDLE:
            self._first_open_today = False
            self._timer.start_focus()
            self.doro_focus_started.emit()
        elif self._timer.is_paused:
            self._timer.resume()

    def _on_pause(self):
        if self._timer.is_focusing or self._timer.is_on_break:
            self._timer.pause()
        elif self._timer.is_paused:
            self._timer.resume()

    def _on_stop(self):
        if not self._timer.is_idle:
            was_focusing = self._timer.is_focusing or self._timer._state == TimerState.PAUSED_FOCUS
            self._timer.stop()
            if was_focusing and self._orange_manager:
                self._orange_manager.interrupt_focus()
            if was_focusing:
                self.doro_focus_interrupted.emit()
                self._combo_badge.setVisible(False)

    def _on_state_changed(self, new_state: TimerState, old_state: TimerState):
        self._update_button_states()

        if new_state == TimerState.FOCUSING:
            self._timer_ring.set_time(self._timer.remaining, self._timer.total, "专注中...")
            self._status_label.setText("🔴 专注中... 加油！")
        elif new_state == TimerState.BREAK:
            self._timer_ring.set_time(self._timer.remaining, self._timer.total, "休息中...")
            self._status_label.setText("☕ 休息时间，放松一下~")
        elif new_state == TimerState.PAUSED_FOCUS:
            self._status_label.setText("⏸ 专注已暂停")
        elif new_state == TimerState.PAUSED_BREAK:
            self._status_label.setText("⏸ 休息已暂停")
        elif new_state == TimerState.IDLE:
            mins = self._timer.get_focus_duration_minutes()
            self._timer_ring.set_time(mins * 60, mins * 60, "就绪")
            if old_state == TimerState.FOCUSING:
                self._status_label.setText("🍊 欧润吉get！太棒了！")
            elif old_state == TimerState.BREAK:
                self._status_label.setText("☕ 休息结束，可以开始新的欧润吉了")
            else:
                self._status_label.setText("点击「开始」开始一个欧润吉钟")

    def _on_tick(self, remaining: int):
        self._timer_ring.set_time(remaining, self._timer.total, self._timer.state.value)

    def _on_pomodoro_completed(self, total_seconds: int):
        self._db.add_completed_pomodoro(total_seconds)
        self._refresh_stats()

        focus_minutes = total_seconds // 60

        if self._orange_manager:
            earned = self._orange_manager.earn_oranges(focus_minutes)
            self._refresh_orange_display()
            self._refresh_combo_display()
            self._orange_popup.show_earned(earned)

        logger.info(f"Orange clock completed! Total: {self._db.get_total_pomodoros()}")
        self.doro_pomodoro_completed.emit(focus_minutes)

    def _on_pomodoro_interrupted(self, elapsed: int):
        self._db.add_interrupted_pomodoro(elapsed)
        logger.info(f"Orange clock interrupted after {elapsed}s")

    def _on_streak_warning(self, minutes: int):
        self.doro_streak_warning.emit(minutes)

    def _on_orange_changed(self, balance: int, today: int):
        self._refresh_orange_display()

    def _update_button_states(self):
        if self._timer.is_idle:
            self._start_btn.setText("▶ 开始")
            self._start_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)
        elif self._timer.is_focusing:
            self._start_btn.setEnabled(False)
            self._pause_btn.setText("⏸ 暂停")
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        elif self._timer.is_on_break:
            self._start_btn.setEnabled(False)
            self._pause_btn.setText("⏸ 暂停")
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        elif self._timer.is_paused:
            self._start_btn.setText("▶ 继续")
            self._start_btn.setEnabled(True)
            self._pause_btn.setText("▶ 继续")
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)

    def _refresh_stats(self):
        today = self._db.get_today_stats()
        self._refresh_today_badge(today)

    def _refresh_today_badge(self, today: dict = None):
        if today is None:
            today = self._db.get_today_stats()
        orange_today = self._orange_manager.today_earned if self._orange_manager else 0
        self._today_badge.setText(f"今日🍊 × {orange_today}")

    def _refresh_orange_display(self):
        if self._orange_manager:
            self._orange_badge.set_count(self._orange_manager.balance)
            self._refresh_today_badge()
            self._refresh_doro_status()

    def _refresh_combo_display(self):
        if self._orange_manager and self._orange_manager.current_combo >= 2:
            combo = self._orange_manager.current_combo
            self._combo_badge.setText(f"🔥x{combo}")
            self._combo_badge.setVisible(True)
            dark = isDarkTheme()
            self._combo_badge.setStyleSheet(f"""
                font-size: 12px;
                font-weight: bold;
                color: {'#ffb74d' if dark else '#e65100'};
            """)
        else:
            self._combo_badge.setVisible(False)

    def _refresh_doro_status(self):
        if not self._orange_manager:
            return

        level = self._orange_manager.doro_level
        title = self._orange_manager.doro_title
        self._doro_level_label.setText(f"⭐ Lv.{level} {title}")

        dark = isDarkTheme()
        self._doro_level_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {'#ffb74d' if dark else '#e65100'};
        """)

    def set_doro_attribute_display(self, hunger: float = None, mood: float = None):
        pass

    def update_theme(self, is_dark: bool = None):
        if is_dark is None:
            is_dark = isDarkTheme()
        self._orange_badge.update_theme(is_dark)
        self._orange_info.update_theme(is_dark)
        self._refresh_combo_display()
        self._refresh_doro_status()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_stats()
        self._refresh_orange_display()
        if self._first_open_today and self._timer.is_idle:
            today = self._db.get_today_stats()
            if today["pomodoro_count"] == 0:
                self.doro_idle_reminder.emit()
                self._first_open_today = False
