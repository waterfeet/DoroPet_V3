from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QConicalGradient, QPainterPath
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class TimerRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._remaining = 0
        self._total = 1
        self._label_text = "就绪"
        self.setMinimumSize(200, 200)

    def set_time(self, remaining: int, total: int, label: str = ""):
        self._remaining = remaining
        self._total = max(total, 1)
        self._label_text = label
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h) - 20
        cx = w / 2
        cy = h / 2
        radius = side / 2

        bg_color = QColor("#2d2d2d") if self._is_dark() else QColor("#e8e8e8")
        pen = QPen(bg_color, 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(QRectF(cx - radius, cy - radius, side, side))

        if self._total > 0:
            ratio = self._remaining / self._total
        else:
            ratio = 0

        if self._remaining > 0:
            ratio = min(max(ratio, 0), 1)
            progress_color = QColor("#FF6B6B") if self._is_dark() else QColor("#E53935")
        else:
            progress_color = QColor("#66BB6A")

        progress_pen = QPen(progress_color, 12, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(progress_pen)

        start_angle = 90 * 16
        span_angle = int(-360 * 16 * ratio)
        painter.drawArc(QRectF(cx - radius, cy - radius, side, side), start_angle, span_angle)

        time_font = QFont("Segoe UI", 28, QFont.Bold)
        painter.setFont(time_font)
        time_color = QColor("#e0e0e0") if self._is_dark() else QColor("#333333")
        painter.setPen(QPen(time_color))

        mins = self._remaining // 60
        secs = self._remaining % 60
        time_str = f"{mins:02d}:{secs:02d}"
        painter.drawText(QRectF(0, cy - 30, w, 40), Qt.AlignCenter, time_str)

        label_font = QFont("Segoe UI", 11)
        painter.setFont(label_font)
        label_color = QColor("#888888") if self._is_dark() else QColor("#888888")
        painter.setPen(QPen(label_color))
        painter.drawText(QRectF(0, cy + 15, w, 25), Qt.AlignCenter, self._label_text)

    def _is_dark(self):
        try:
            from qfluentwidgets import isDarkTheme
            return isDarkTheme()
        except Exception:
            return False


class DigitalTimer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._remaining = 0
        self._label_text = "就绪"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #333;")

        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #888;")

        layout.addStretch()
        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def set_time(self, remaining: int, total: int, label: str = ""):
        self._remaining = remaining
        self._label_text = label
        mins = remaining // 60
        secs = remaining % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")
        self.status_label.setText(label)

    def update_theme(self, is_dark: bool):
        if is_dark:
            self.time_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #e0e0e0;")
            self.status_label.setStyleSheet("font-size: 14px; color: #aaa;")
        else:
            self.time_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #333;")
            self.status_label.setStyleSheet("font-size: 14px; color: #888;")
