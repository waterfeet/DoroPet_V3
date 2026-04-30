from typing import List, Tuple
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import isDarkTheme


class DailyChart(QWidget):
    WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._data: List[Tuple[str, int]] = []

    def set_data(self, data: List[Tuple[str, int]]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin_left = 36
        margin_right = 16
        margin_top = 10
        margin_bottom = 32
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        is_dark = self._is_dark()
        bg_color = QColor("#252525") if is_dark else QColor("#f5f5f5")
        text_color = QColor("#ccc") if is_dark else QColor("#666")
        bar_color = QColor("#FF6B6B") if is_dark else QColor("#E53935")
        today_bar_color = QColor("#FF8A65") if is_dark else QColor("#FF7043")

        today_idx = -1
        from datetime import date
        today_str = date.today().isoformat()
        for i, (d, _) in enumerate(self._data):
            if d == today_str:
                today_idx = i
                break

        painter.fillRect(0, 0, w, h, bg_color)
        painter.setPen(QPen(QColor("#444") if is_dark else QColor("#ddd"), 1))
        painter.drawLine(margin_left, h - margin_bottom, w - margin_right, h - margin_bottom)

        max_count = 1
        for _, count in self._data:
            if count > max_count:
                max_count = count
        max_count = max(max_count, 1)

        n = len(self._data)
        if n == 0:
            return

        bar_width = max(chart_w / n * 0.6, 10)
        gap = chart_w / n

        for i, (date_str, count) in enumerate(self._data):
            bar_h = (count / max_count) * chart_h if max_count > 0 else 0
            x = margin_left + gap * i + (gap - bar_width) / 2
            y = h - margin_bottom - bar_h

            color = today_bar_color if i == today_idx else bar_color
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_h), 4, 4)

            if count > 0:
                num_font = QFont("Segoe UI", 9, QFont.Bold)
                painter.setFont(num_font)
                painter.setPen(QPen(text_color))
                painter.drawText(QRectF(x - 5, y - 18, bar_width + 10, 16), Qt.AlignCenter, str(count))

            day_font = QFont("Segoe UI", 10)
            painter.setFont(day_font)
            day_text = self.WEEKDAY_NAMES[i] if i < 7 else "?"
            painter.setPen(QPen(text_color))
            painter.drawText(QRectF(x - 5, h - margin_bottom + 4, bar_width + 10, 22), Qt.AlignCenter, day_text)

        title_font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QPen(text_color))
        painter.drawText(QRectF(margin_left, 0, chart_w, margin_top + 8), Qt.AlignLeft, "📊 本周趋势")

    def _is_dark(self):
        try:
            return isDarkTheme()
        except Exception:
            return False
