from enum import Enum
from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class TimerState(Enum):
    IDLE = "idle"
    FOCUSING = "focusing"
    BREAK = "break"
    PAUSED_FOCUS = "paused_focus"
    PAUSED_BREAK = "paused_break"


class PomodoroTimer(QObject):
    state_changed = pyqtSignal(TimerState, TimerState)
    tick = pyqtSignal(int)
    pomodoro_completed = pyqtSignal(int)
    pomodoro_interrupted = pyqtSignal(int)
    streak_warning = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = TimerState.IDLE
        self._remaining = 0
        self._total = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._focus_duration = 25 * 60
        self._short_break_duration = 5 * 60
        self._long_break_duration = 15 * 60
        self._completed_count = 0

        self._continuous_focus_seconds = 0
        self._streak_warned = False

    @property
    def state(self):
        return self._state

    @property
    def remaining(self):
        return self._remaining

    @property
    def total(self):
        return self._total

    @property
    def completed_count(self):
        return self._completed_count

    @property
    def is_focusing(self):
        return self._state == TimerState.FOCUSING

    @property
    def is_on_break(self):
        return self._state == TimerState.BREAK

    @property
    def is_paused(self):
        return self._state in (TimerState.PAUSED_FOCUS, TimerState.PAUSED_BREAK)

    @property
    def is_idle(self):
        return self._state == TimerState.IDLE

    def set_focus_duration(self, minutes: int):
        self._focus_duration = minutes * 60

    def set_break_duration(self, short_minutes: int, long_minutes: int):
        self._short_break_duration = short_minutes * 60
        self._long_break_duration = long_minutes * 60

    def get_focus_duration_minutes(self):
        return self._focus_duration // 60

    def start_focus(self):
        if self._state != TimerState.IDLE:
            return
        old_state = self._state
        self._state = TimerState.FOCUSING
        self._remaining = self._focus_duration
        self._total = self._focus_duration
        self._continuous_focus_seconds = 0
        self._streak_warned = False
        self._timer.start()
        self.state_changed.emit(TimerState.FOCUSING, old_state)

    def start_break(self):
        if self._state != TimerState.IDLE:
            return
        old_state = self._state
        self._state = TimerState.BREAK
        if self._completed_count > 0 and self._completed_count % 4 == 0:
            self._remaining = self._long_break_duration
            self._total = self._long_break_duration
        else:
            self._remaining = self._short_break_duration
            self._total = self._short_break_duration
        self._timer.start()
        self.state_changed.emit(TimerState.BREAK, old_state)

    def pause(self):
        if self._state == TimerState.FOCUSING:
            self._state = TimerState.PAUSED_FOCUS
        elif self._state == TimerState.BREAK:
            self._state = TimerState.PAUSED_BREAK
        else:
            return
        old_state = self._state
        self._timer.stop()
        self.state_changed.emit(self._state, old_state)

    def resume(self):
        old_state = self._state
        if self._state == TimerState.PAUSED_FOCUS:
            self._state = TimerState.FOCUSING
        elif self._state == TimerState.PAUSED_BREAK:
            self._state = TimerState.BREAK
        else:
            return
        self._timer.start()
        self.state_changed.emit(self._state, old_state)

    def stop(self):
        old_state = self._state
        if self._state in (TimerState.FOCUSING, TimerState.PAUSED_FOCUS):
            elapsed = self._total - self._remaining
            self._state = TimerState.IDLE
            self._timer.stop()
            self.pomodoro_interrupted.emit(elapsed)
        else:
            self._state = TimerState.IDLE
            self._timer.stop()
        self.state_changed.emit(TimerState.IDLE, old_state)

    def skip_current(self):
        if self._state == TimerState.FOCUSING:
            elapsed = self._total
            self._state = TimerState.IDLE
            self._timer.stop()
            self._completed_count += 1
            self.pomodoro_completed.emit(self._total)
        elif self._state == TimerState.BREAK:
            self._state = TimerState.IDLE
            self._timer.stop()

    def reset_completed_count(self):
        self._completed_count = 0

    def _on_tick(self):
        self._remaining -= 1

        if self._state == TimerState.FOCUSING:
            self._continuous_focus_seconds += 1
            if self._continuous_focus_seconds >= 120 * 60 and not self._streak_warned:
                self._streak_warned = True
                self.streak_warning.emit(self._continuous_focus_seconds // 60)
        else:
            self._continuous_focus_seconds = 0
            self._streak_warned = False

        self.tick.emit(self._remaining)

        if self._remaining <= 0:
            self._timer.stop()
            old_state = self._state
            if self._state == TimerState.FOCUSING:
                self._completed_count += 1
                self._state = TimerState.IDLE
                self.state_changed.emit(TimerState.IDLE, old_state)
                self.pomodoro_completed.emit(self._total)
            elif self._state == TimerState.BREAK:
                self._state = TimerState.IDLE
                self.state_changed.emit(TimerState.IDLE, old_state)
