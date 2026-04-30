from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from qfluentwidgets import CardWidget, isDarkTheme


class StatsPanel(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self._labels = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self._today_widget = self._create_stat_group("📅 今日统计", [
            ("pomodoro", "🍅 番茄", "0"),
            ("focus", "⏱️ 专注", "0min"),
            ("chat", "💬 对话", "0"),
            ("interaction", "🎮 互动", "0"),
        ])
        layout.addWidget(self._today_widget)

        divider = QWidget()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(divider)

        self._total_widget = self._create_stat_group("🏆 累计统计", [
            ("total_pomodoros", "🍅 总番茄", "0"),
            ("best_streak", "🔥 最佳连胜", "0天"),
            ("total_focus", "⏱️ 总专注", "0h"),
        ])
        layout.addWidget(self._total_widget)

    def _create_stat_group(self, title: str, items: list):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #555;")
        layout.addWidget(title_label)

        for key, name, default_val in items:
            row = QHBoxLayout()
            row.setSpacing(6)
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 12px; color: #888;")
            val_label = QLabel(default_val)
            val_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #333;")
            val_label.setObjectName(f"stat_{key}")
            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(val_label)
            layout.addLayout(row)
            self._labels[key] = val_label

        return widget

    def update_today(self, pomodoro_count: int, focus_seconds: int, chat_count: int, interaction_count: int):
        self._set_label("pomodoro", str(pomodoro_count))
        if focus_seconds >= 3600:
            self._set_label("focus", f"{focus_seconds / 3600:.1f}h")
        else:
            self._set_label("focus", f"{focus_seconds // 60}min")
        self._set_label("chat", str(chat_count))
        self._set_label("interaction", str(interaction_count))

    def update_total(self, total_pomodoros: int, best_streak: int, total_focus_seconds: int):
        self._set_label("total_pomodoros", str(total_pomodoros))
        self._set_label("best_streak", f"{best_streak}天")
        if total_focus_seconds >= 3600:
            self._set_label("total_focus", f"{total_focus_seconds / 3600:.1f}h")
        else:
            self._set_label("total_focus", f"{total_focus_seconds // 60}min")

    def _set_label(self, key: str, value: str):
        if key in self._labels:
            self._labels[key].setText(value)

    def update_theme(self, is_dark: bool):
        text_color = "#e0e0e0" if is_dark else "#333"
        dim_text = "#aaa" if is_dark else "#888"
        title_color = "#ccc" if is_dark else "#555"
        for label in self.findChildren(QLabel):
            if hasattr(label, 'objectName') and label.objectName() and label.objectName().startswith("stat_"):
                label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {text_color};")
            elif label.text() and ("统计" in label.text()):
                label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {title_color};")
            elif label.text() and any(k in label.text() for k in ["🍅", "⏱️", "💬", "🎮", "🔥"]):
                label.setStyleSheet(f"font-size: 12px; color: {dim_text};")
