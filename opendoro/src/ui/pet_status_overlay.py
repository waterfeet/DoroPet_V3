from PyQt5.QtCore import Qt, QTimer, QPoint, QSize
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_COLORS
)


class PetStatusOverlay(QWidget):
    def __init__(self, attr_manager, parent=None):
        super().__init__(parent)
        self.attr_manager = attr_manager
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setFixedSize(220, 70)
        self.setStyleSheet("background: transparent;")
        
        self._init_ui()
        self._connect_signals()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
        self._update_display()

    def _init_ui(self):
        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("statusOverlayMain")
        self.main_widget.setFixedSize(200, 60)
        
        bg_color = "rgba(255, 255, 255, 220)"
        if False:
            bg_color = "rgba(40, 40, 40, 220)"
        
        self.main_widget.setStyleSheet(f"""
            QWidget#statusOverlayMain {{
                background: {bg_color};
                border-radius: 10px;
                border: 2px solid #888;
            }}
        """)
        
        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        self.progress_bars = {}
        
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            
            label = QLabel(ATTR_NAMES[attr_name][:2])
            label.setFixedWidth(16)
            label.setStyleSheet("font-size: 10px; font-weight: bold; color: #333;")
            
            bar = QProgressBar()
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            bar.setRange(0, 100)
            bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #888;
                    border-radius: 4px;
                    background-color: #eee;
                }
                QProgressBar::chunk {
                    border-radius: 3px;
                }
            """)
            
            row_layout.addWidget(label)
            row_layout.addWidget(bar)
            
            self.progress_bars[attr_name] = bar
            layout.addWidget(row)

    def _connect_signals(self):
        self.attr_manager.attribute_changed.connect(self._on_attribute_changed)

    def _on_attribute_changed(self, attr_name: str, new_value: float, old_value: float):
        if attr_name in self.progress_bars:
            self._update_bar_style(attr_name, new_value)
            self.progress_bars[attr_name].setValue(int(new_value))

    def _update_bar_style(self, attr_name: str, value: float):
        bar = self.progress_bars[attr_name]
        
        if value < 20:
            color = STATUS_COLORS["critical"]
        elif value < 50:
            color = STATUS_COLORS["warning"]
        else:
            color = STATUS_COLORS["good"]
        
        bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #888;
                border-radius: 4px;
                background-color: #eee;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)

    def _update_display(self):
        all_attrs = self.attr_manager.get_all_attributes()
        for attr_name, value in all_attrs.items():
            if attr_name in self.progress_bars:
                self.progress_bars[attr_name].setValue(int(value))
                self._update_bar_style(attr_name, value)

    def follow_pet(self, pet_pos: QPoint, pet_size: QSize):
        x = pet_pos.x() + (pet_size.width() - self.width()) // 2
        y = pet_pos.y() + pet_size.height() + 10
        self.move(x, y)

    def show_with_auto_hide(self):
        self.show()
        self.hide_timer.stop()
        self.hide_timer.start(3000)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.hide_timer.stop()
        self.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hide_timer.start(2000)
