from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QButtonGroup, QFrame
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, RadioButton,
    TitleLabel, SubtitleLabel, BodyLabel, isDarkTheme
)
from qfluentwidgets import FluentIcon as FIF

from .pomodoro_timer import PomodoroTimer, TimerState
from .database import PomodoroDatabase
from .widgets import TimerRing, StatsPanel, DailyChart
from src.core.logger import logger


class PomodoroInterface(QWidget):
    doro_focus_started = pyqtSignal()
    doro_pomodoro_completed = pyqtSignal()
    doro_focus_interrupted = pyqtSignal()
    doro_streak_warning = pyqtSignal(int)
    doro_idle_reminder = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PomodoroInterface")
        self.setMinimumSize(260, 300)

        self._db = PomodoroDatabase()
        self._timer = PomodoroTimer(self)

        self._first_open_today = True

        self._init_ui()
        self._connect_signals()
        self._refresh_stats()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        self._title_label = TitleLabel("🍅 专注陪伴")
        main_layout.addWidget(self._title_label)

        timer_section = QWidget()
        timer_layout = QHBoxLayout(timer_section)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        timer_layout.setSpacing(0)

        self._timer_ring = TimerRing()
        self._timer_ring.setMinimumSize(160, 160)
        self._timer_ring.setMaximumSize(200, 200)
        timer_layout.addStretch()
        timer_layout.addWidget(self._timer_ring)
        timer_layout.addStretch()

        main_layout.addWidget(timer_section)

        self._status_label = SubtitleLabel("点击「开始专注」开始一个番茄钟")
        self._status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self._status_label)

        self._today_badge = BodyLabel("今日：🍅 0")
        self._today_badge.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self._today_badge)

        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(6)

        self._start_btn = PrimaryPushButton("▶ 开始")
        self._start_btn.setMinimumHeight(32)
        self._pause_btn = PushButton("⏸ 暂停")
        self._pause_btn.setMinimumHeight(32)
        self._stop_btn = PushButton("⏹ 停止")
        self._stop_btn.setMinimumHeight(32)

        control_layout.addStretch()
        control_layout.addWidget(self._start_btn)
        control_layout.addWidget(self._pause_btn)
        control_layout.addWidget(self._stop_btn)
        control_layout.addStretch()

        main_layout.addWidget(control_widget)

        self._start_btn.clicked.connect(self._on_start)
        self._pause_btn.clicked.connect(self._on_pause)
        self._stop_btn.clicked.connect(self._on_stop)

        self._update_button_states()

        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(4)

        dur_label = BodyLabel("时长：")
        duration_layout.addWidget(dur_label)

        self._duration_group = QButtonGroup(self)
        duration_options = [15, 25, 45, 60]
        for mins in duration_options:
            radio = RadioButton(f"{mins}m")
            if mins == 25:
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, m=mins: self._on_duration_changed(m, checked))
            self._duration_group.addButton(radio)
            duration_layout.addWidget(radio)

        duration_layout.addStretch()
        main_layout.addWidget(duration_widget)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(divider)

        self._stats_panel = StatsPanel()
        main_layout.addWidget(self._stats_panel)

        self._chart = DailyChart()
        main_layout.addWidget(self._chart)

        main_layout.addStretch()

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
            if was_focusing:
                self.doro_focus_interrupted.emit()

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
                self._status_label.setText("✅ 番茄完成！太棒了！")
            elif old_state == TimerState.BREAK:
                self._status_label.setText("☕ 休息结束，可以开始新的番茄了")
            else:
                self._status_label.setText("点击「开始专注」开始一个番茄钟")

    def _on_tick(self, remaining: int):
        self._timer_ring.set_time(remaining, self._timer.total, self._timer.state.value)

    def _on_pomodoro_completed(self):
        self._db.add_completed_pomodoro(self._timer.total)
        self._refresh_stats()
        logger.info(f"Pomodoro completed! Total: {self._db.get_total_pomodoros()}")
        self.doro_pomodoro_completed.emit()

    def _on_pomodoro_interrupted(self, elapsed: int):
        self._db.add_interrupted_pomodoro(elapsed)
        logger.info(f"Pomodoro interrupted after {elapsed}s")

    def _on_streak_warning(self, minutes: int):
        self.doro_streak_warning.emit(minutes)

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
        self._stats_panel.update_today(
            today["pomodoro_count"],
            today["total_focus_seconds"],
            today["chat_count"],
            today["interaction_count"]
        )
        self._today_badge.setText(f"今日：🍅 × {today['pomodoro_count']}")

        total_pomodoros = self._db.get_total_pomodoros()
        best_streak = self._db.get_best_streak()
        total_focus = self._db.get_total_focus_seconds()
        self._stats_panel.update_total(total_pomodoros, best_streak, total_focus)

        week_data = self._db.get_week_stats()
        self._chart.set_data(week_data)

    def update_theme(self, is_dark: bool = None):
        if is_dark is None:
            is_dark = isDarkTheme()
        self._stats_panel.update_theme(is_dark)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_stats()
        if self._first_open_today and self._timer.is_idle:
            today = self._db.get_today_stats()
            if today["pomodoro_count"] == 0:
                self.doro_idle_reminder.emit()
                self._first_open_today = False
