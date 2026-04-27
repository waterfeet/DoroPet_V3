import math
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient
from PyQt5.QtWidgets import QWidget


class MiniSpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._num_bars = 10
        self._bar_data = [0.0] * self._num_bars
        self._target_data = [0.0] * self._num_bars
        self._peak_data = [0.0] * self._num_bars
        self._peak_fall_speed = [0.0] * self._num_bars
        self._accent_color = QColor(96, 165, 250)
        self._is_playing = False
        self._idle_phase = 0.0
        self._bar_gap = 2
        self._use_real_data = False
        self._real_data_timeout = 0

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.setInterval(25)

        self.setFixedSize(80, 20)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()

    def set_playing(self, is_playing: bool):
        self._is_playing = is_playing
        if is_playing:
            self._target_data = [0.0] * self._num_bars
            self._use_real_data = False
        else:
            self._target_data = [0.0] * self._num_bars
        if not self._animation_timer.isActive():
            self._animation_timer.start()
        self.update()

    def set_spectrum_data(self, data: list):
        if len(data) >= self._num_bars:
            step = len(data) / self._num_bars
            self._target_data = [data[int(i * step)] for i in range(self._num_bars)]
            self._use_real_data = True
            self._real_data_timeout = 0
        self.update()

    def _animate(self):
        if self._is_playing:
            if self._use_real_data:
                self._real_data_timeout += 1
                if self._real_data_timeout > 10:
                    self._use_real_data = False
                    self._real_data_timeout = 0
            else:
                import random
                self._idle_phase += 0.15
                beat = math.sin(self._idle_phase * 0.5) * 0.15 + 0.85
                for i in range(self._num_bars):
                    if random.random() < 0.3:
                        self._target_data[i] = random.uniform(0.1, 0.85) * beat
                    elif random.random() < 0.4:
                        self._target_data[i] *= random.uniform(0.75, 0.95)

            smoothing = 0.25
            for i in range(self._num_bars):
                self._bar_data[i] += (self._target_data[i] - self._bar_data[i]) * smoothing
                if self._bar_data[i] < 0.01:
                    self._bar_data[i] = 0.0
                if self._bar_data[i] > self._peak_data[i]:
                    self._peak_data[i] = self._bar_data[i]
                    self._peak_fall_speed[i] = 0.0
                else:
                    self._peak_fall_speed[i] += 0.008
                    self._peak_data[i] -= self._peak_fall_speed[i]
                    if self._peak_data[i] < 0:
                        self._peak_data[i] = 0.0
        else:
            self._idle_phase += 0.03
            for i in range(self._num_bars):
                breath = math.sin(self._idle_phase + i * 0.3) * 0.5 + 0.5
                self._bar_data[i] += (breath * 0.06 - self._bar_data[i]) * 0.05
                self._peak_data[i] *= 0.95

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total_gap = self._bar_gap * (self._num_bars - 1)
        bar_width = max(2, (self.width() - total_gap) / self._num_bars)
        max_bar_height = self.height() - 2

        for i in range(self._num_bars):
            x = i * (bar_width + self._bar_gap)
            value = self._bar_data[i]
            bar_height = max(2, value * max_bar_height)
            bar_y = self.height() - bar_height

            t = i / max(self._num_bars - 1, 1)
            if t < 0.5:
                r = int(self._accent_color.red() * 0.5 + 255 * 0.5)
                g = int(self._accent_color.green() * 0.5 + 200 * 0.5)
                b = int(self._accent_color.blue() * 0.5 + 255 * 0.5)
            else:
                r = self._accent_color.red()
                g = self._accent_color.green()
                b = self._accent_color.blue()

            intensity = 0.5 + value * 0.5
            r = min(255, int(r * intensity))
            g = min(255, int(g * intensity))
            b = min(255, int(b * intensity))
            color = QColor(r, g, b)

            gradient = QLinearGradient(x, bar_y, x, self.height())
            top_alpha = 220
            top_color = QColor(r, g, b, top_alpha)
            gradient.setColorAt(0.0, top_color)
            gradient.setColorAt(1.0, QColor(r, g, b, 60))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(int(x), int(bar_y), int(bar_width), int(bar_height), 1, 1)

        painter.end()
