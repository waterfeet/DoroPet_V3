from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from qfluentwidgets import isDarkTheme
from typing import Optional

from ..models import StoryMessage


class StoryMessageCard(QFrame):
    def __init__(
        self,
        message: StoryMessage,
        parent=None,
        is_streaming: bool = False
    ):
        super().__init__(parent)
        self.message = message
        self._is_streaming = is_streaming
        self._font_size = 14
        self.setObjectName("storyMessageCard")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        if self.message.character_name:
            name_label = QLabel(self.message.character_name, self)
            name_label.setObjectName("characterName")
            font = QFont()
            font.setBold(True)
            name_label.setFont(font)
            header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        if self.message.timestamp:
            time_label = QLabel(self.message.timestamp, self)
            time_label.setObjectName("timeLabel")
            header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        self.content_label = QLabel(self.message.content, self)
        self.content_label.setObjectName("contentLabel")
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.content_label)
        
        effects_layout = QHBoxLayout()
        effects_layout.setSpacing(16)
        
        if self.message.affection_changes:
            for char_name, change in self.message.affection_changes.items():
                sign = "+" if change >= 0 else ""
                aff_label = QLabel(f"💕 {char_name} {sign}{change}", self)
                aff_label.setObjectName("affectionLabel")
                effects_layout.addWidget(aff_label)
        
        if self.message.currency_change != 0:
            sign = "+" if self.message.currency_change >= 0 else ""
            curr_label = QLabel(f"💰 {sign}{self.message.currency_change}", self)
            curr_label.setObjectName("currencyLabel")
            effects_layout.addWidget(curr_label)
        
        effects_layout.addStretch()
        
        if self.message.affection_changes or self.message.currency_change != 0:
            layout.addLayout(effects_layout)
        
        self.update_theme()
    
    def set_font_size(self, size: int):
        self._font_size = size
        self.update_theme()
    
    def update_content(self, content: str):
        self.message.content = content
        self.content_label.setText(content)
    
    def set_choices_visible(self, visible: bool):
        pass
    
    def update_theme(self):
        is_dark = isDarkTheme()
        
        # Handle both enum and string role
        role_value = self.message.role.value if hasattr(self.message.role, 'value') else self.message.role
        
        if role_value == "narrator":
            bg_color = "#2a2a2a" if is_dark else "#f8f8f8"
            text_color = "#cccccc" if is_dark else "#333333"
            border_color = "#404040" if is_dark else "#e0e0e0"
        else:
            bg_color = "#2d3748" if is_dark else "#e8f4f8"
            text_color = "#e2e8f0" if is_dark else "#2d3748"
            border_color = "#4a5568" if is_dark else "#bee3f8"
        
        name_color = "#63b3ed" if is_dark else "#3182ce"
        time_color = "#718096" if is_dark else "#a0aec0"
        
        content_size = self._font_size
        name_size = self._font_size - 1
        time_size = self._font_size - 2
        
        self.setStyleSheet(f"""
            #storyMessageCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #characterName {{
                color: {name_color};
                font-size: {name_size}px;
                font-weight: bold;
            }}
            #roleLabel {{
                color: {time_color};
                font-size: {time_size}px;
            }}
            #contentLabel {{
                color: {text_color};
                font-size: {content_size}px;
                line-height: 1.5;
            }}
            #timeLabel {{
                color: {time_color};
                font-size: {time_size}px;
            }}
            #affectionLabel {{
                color: #f687b3;
                font-size: {time_size}px;
            }}
            #currencyLabel {{
                color: #f6e05e;
                font-size: {time_size}px;
            }}
        """)
