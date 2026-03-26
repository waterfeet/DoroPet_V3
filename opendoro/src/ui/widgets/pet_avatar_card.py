import os
import psutil
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt5.QtGui import QPixmap, QFont

from qfluentwidgets import CardWidget


class PetAvatarCard(CardWidget):
    def __init__(self, quotes_manager, attr_manager=None, parent=None):
        super().__init__(parent)
        self.quotes_manager = quotes_manager
        self.attr_manager = attr_manager
        self._current_attributes = {}
        self._avatar_path = self._get_avatar_path()

        self._init_ui()
        self._connect_signals()
        self._start_system_monitor()

    def _get_avatar_path(self) -> str:
        current_file = os.path.abspath(__file__)
        widgets_dir = os.path.dirname(current_file)
        ui_dir = os.path.dirname(widgets_dir)
        src_dir = os.path.dirname(ui_dir)
        base_dir = os.path.dirname(src_dir)
        avatar_path = os.path.join(base_dir, "data", "icons", "app.ico")
        if os.path.exists(avatar_path):
            return avatar_path
        return ""

    def _init_ui(self):
        self.setObjectName("petAvatarCard")
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(20)

        avatar_section = QWidget()
        avatar_layout = QVBoxLayout(avatar_section)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(8)
        avatar_layout.setAlignment(Qt.AlignCenter)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(90, 90)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self._load_avatar()

        self.name_label = QLabel("Doro")
        self.name_label.setObjectName("petAvatarNameLabel")
        self.name_label.setAlignment(Qt.AlignCenter)

        avatar_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)
        avatar_layout.addWidget(self.name_label, alignment=Qt.AlignCenter)

        quote_section = QWidget()
        quote_layout = QVBoxLayout(quote_section)
        quote_layout.setContentsMargins(0, 0, 0, 0)
        quote_layout.setSpacing(12)

        self.quote_bubble = QWidget()
        self.quote_bubble.setObjectName("petAvatarQuoteBubble")
        bubble_layout = QVBoxLayout(self.quote_bubble)
        bubble_layout.setContentsMargins(15, 12, 15, 12)

        self.quote_label = QLabel()
        self.quote_label.setObjectName("petAvatarQuoteLabel")
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignCenter)
        self.quote_label.setText("今天心情怎么样呢？")

        bubble_layout.addWidget(self.quote_label)

        self.status_label = QLabel()
        self.status_label.setObjectName("petAvatarStatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setText("状态良好")

        system_section = QWidget()
        system_layout = QVBoxLayout(system_section)
        system_layout.setContentsMargins(0, 8, 0, 0)
        system_layout.setSpacing(6)

        cpu_row = QWidget()
        cpu_layout = QHBoxLayout(cpu_row)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(8)

        self.cpu_label = QLabel("CPU")
        self.cpu_label.setObjectName("petAvatarCpuLabel")
        self.cpu_label.setFixedWidth(35)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setObjectName("petAvatarCpuBar")
        self.cpu_bar.setFixedHeight(8)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setRange(0, 100)

        self.cpu_value = QLabel("0%")
        self.cpu_value.setObjectName("petAvatarCpuValue")
        self.cpu_value.setFixedWidth(40)

        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_bar)
        cpu_layout.addWidget(self.cpu_value)

        mem_row = QWidget()
        mem_layout = QHBoxLayout(mem_row)
        mem_layout.setContentsMargins(0, 0, 0, 0)
        mem_layout.setSpacing(8)

        self.mem_label = QLabel("内存")
        self.mem_label.setObjectName("petAvatarMemLabel")
        self.mem_label.setFixedWidth(35)

        self.mem_bar = QProgressBar()
        self.mem_bar.setObjectName("petAvatarMemBar")
        self.mem_bar.setFixedHeight(8)
        self.mem_bar.setTextVisible(False)
        self.mem_bar.setRange(0, 100)

        self.mem_value = QLabel("0%")
        self.mem_value.setObjectName("petAvatarMemValue")
        self.mem_value.setFixedWidth(40)

        mem_layout.addWidget(self.mem_label)
        mem_layout.addWidget(self.mem_bar)
        mem_layout.addWidget(self.mem_value)

        system_layout.addWidget(cpu_row)
        system_layout.addWidget(mem_row)

        quote_layout.addWidget(self.quote_bubble)
        quote_layout.addWidget(self.status_label)
        quote_layout.addWidget(system_section)
        quote_layout.addStretch()

        main_layout.addWidget(avatar_section)
        main_layout.addWidget(quote_section, 1)

    def _load_avatar(self):
        if self._avatar_path and os.path.exists(self._avatar_path):
            pixmap = QPixmap(self._avatar_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(86, 86, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.avatar_label.setPixmap(scaled)
                self.avatar_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                    }
                """)
                return

        self.avatar_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                background-color: #f0f0f0;
            }
        """)
        self.avatar_label.setText("🐱")

    def _connect_signals(self):
        if self.quotes_manager:
            self.quotes_manager.quote_changed.connect(self._on_quote_changed)
            self.quotes_manager.status_description_changed.connect(self._on_status_changed)

    def _start_system_monitor(self):
        self._system_timer = QTimer(self)
        self._system_timer.timeout.connect(self._update_system_info)
        self._system_timer.start(2000)
        self._update_system_info()

    def _update_system_info(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_percent = mem.percent

        self.cpu_bar.setValue(int(cpu_percent))
        self.cpu_value.setText(f"{cpu_percent:.1f}%")

        self.mem_bar.setValue(int(mem_percent))
        self.mem_value.setText(f"{mem_percent:.1f}%")

        if cpu_percent > 80:
            bar_color = "#ef5350"
        elif cpu_percent > 60:
            bar_color = "#ffa726"
        else:
            bar_color = "#66bb6a"

        self.cpu_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {'#3a3a3a' if self._is_dark_theme() else '#e0e0e0'};
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 4px;
            }}
        """)

        if mem_percent > 80:
            bar_color = "#ef5350"
        elif mem_percent > 60:
            bar_color = "#ffa726"
        else:
            bar_color = "#66bb6a"

        self.mem_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {'#3a3a3a' if self._is_dark_theme() else '#e0e0e0'};
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 4px;
            }}
        """)

    def _is_dark_theme(self):
        from qfluentwidgets import isDarkTheme
        return isDarkTheme()

    def _on_quote_changed(self, quote: str):
        self.quote_label.setText(quote)

    def _on_status_changed(self, description: str):
        self.status_label.setText(description)

    def set_attr_manager(self, attr_manager):
        self.attr_manager = attr_manager
        if attr_manager:
            attr_manager.attribute_changed.connect(self._on_attribute_changed)
            self._refresh_quote()

    def _on_attribute_changed(self, attr_name: str, new_value: float, old_value: float):
        self._current_attributes[attr_name] = new_value
        self._refresh_quote()

    def _refresh_quote(self):
        if self.quotes_manager and self.attr_manager:
            attrs = self.attr_manager.get_all_attributes()
            self._current_attributes = attrs
            self.quotes_manager.refresh_quote(attrs)
            description = self.quotes_manager.get_status_description(attrs)
            self.status_label.setText(description)

    def update_theme(self, is_dark: bool):
        self._update_system_info()
