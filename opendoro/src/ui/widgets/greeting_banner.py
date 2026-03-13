from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtGui import QFont

from qfluentwidgets import CardWidget


class GreetingBanner(CardWidget):
    def __init__(self, quotes_manager, parent=None):
        super().__init__(parent)
        self.quotes_manager = quotes_manager
        self._init_ui()
        self._update_greeting()
        
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._update_greeting)
        self._refresh_timer.start(60000)

    def _init_ui(self):
        self.setFixedHeight(50)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        self.greeting_label = QLabel()
        self.greeting_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.greeting_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
            }
        """)
        
        layout.addWidget(self.greeting_label)
        layout.addStretch()

    def _update_greeting(self):
        if self.quotes_manager:
            greeting = self.quotes_manager.get_greeting()
            self.greeting_label.setText(greeting)

    def update_theme(self, is_dark: bool):
        if is_dark:
            self.greeting_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #e0e0e0;
                }
            """)
        else:
            self.greeting_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #333;
                }
            """)
