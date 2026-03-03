import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QBrush, QFont

from qfluentwidgets import CardWidget


def create_round_pixmap(pixmap: QPixmap, size: int) -> QPixmap:
    rounded = QPixmap(size, size)
    rounded.fill(Qt.transparent)
    
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    
    return rounded


class PetAvatarCard(CardWidget):
    def __init__(self, quotes_manager, attr_manager=None, parent=None):
        super().__init__(parent)
        self.quotes_manager = quotes_manager
        self.attr_manager = attr_manager
        self._current_attributes = {}
        self._avatar_path = self._get_avatar_path()
        
        self._init_ui()
        self._connect_signals()

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
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
            }
        """)
        
        avatar_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)
        avatar_layout.addWidget(self.name_label, alignment=Qt.AlignCenter)
        
        quote_section = QWidget()
        quote_layout = QVBoxLayout(quote_section)
        quote_layout.setContentsMargins(0, 0, 0, 0)
        quote_layout.setSpacing(12)
        
        self.quote_bubble = QWidget()
        self.quote_bubble.setStyleSheet("""
            QWidget {
                background-color: #e3f2fd;
                border-radius: 12px;
                border: 1px solid #bbdefb;
            }
        """)
        bubble_layout = QVBoxLayout(self.quote_bubble)
        bubble_layout.setContentsMargins(15, 12, 15, 12)
        
        self.quote_label = QLabel()
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignCenter)
        self.quote_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #1565c0;
                background: transparent;
            }
        """)
        self.quote_label.setText("今天心情怎么样呢？")
        
        bubble_layout.addWidget(self.quote_label)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #666;
            }
        """)
        self.status_label.setText("状态良好")
        
        quote_layout.addWidget(self.quote_bubble)
        quote_layout.addWidget(self.status_label)
        quote_layout.addStretch()
        
        main_layout.addWidget(avatar_section)
        main_layout.addWidget(quote_section, 1)

    def _load_avatar(self):
        if self._avatar_path and os.path.exists(self._avatar_path):
            pixmap = QPixmap(self._avatar_path)
            if not pixmap.isNull():
                rounded = create_round_pixmap(pixmap, 86)
                self.avatar_label.setPixmap(rounded)
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
                border-radius: 45px;
                border: 3px solid #e0e0e0;
            }
        """)
        self.avatar_label.setText("🐱")

    def _connect_signals(self):
        if self.quotes_manager:
            self.quotes_manager.quote_changed.connect(self._on_quote_changed)
            self.quotes_manager.status_description_changed.connect(self._on_status_changed)

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
        if is_dark:
            if self._avatar_path and os.path.exists(self._avatar_path):
                self.avatar_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                    }
                """)
            else:
                self.avatar_label.setStyleSheet("""
                    QLabel {
                        font-size: 48px;
                        background-color: #2d2d2d;
                        border-radius: 45px;
                        border: 3px solid #404040;
                    }
                """)
            self.name_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: #e0e0e0;
                }
            """)
            self.quote_bubble.setStyleSheet("""
                QWidget {
                    background-color: #1e3a5f;
                    border-radius: 12px;
                    border: 1px solid #2e5a8f;
                }
            """)
            self.quote_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #90caf9;
                    background: transparent;
                }
            """)
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #aaa;
                }
            """)
        else:
            if self._avatar_path and os.path.exists(self._avatar_path):
                self.avatar_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                    }
                """)
            else:
                self.avatar_label.setStyleSheet("""
                    QLabel {
                        font-size: 48px;
                        background-color: #f0f0f0;
                        border-radius: 45px;
                        border: 3px solid #e0e0e0;
                    }
                """)
            self.name_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                }
            """)
            self.quote_bubble.setStyleSheet("""
                QWidget {
                    background-color: #e3f2fd;
                    border-radius: 12px;
                    border: 1px solid #bbdefb;
                }
            """)
            self.quote_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #1565c0;
                    background: transparent;
                }
            """)
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #666;
                }
            """)
