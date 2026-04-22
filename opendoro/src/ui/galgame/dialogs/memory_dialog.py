from typing import List, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QGridLayout, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    PushButton, PrimaryPushButton, TitleLabel, BodyLabel,
    StrongBodyLabel, CaptionLabel, CardWidget, isDarkTheme
)

from ..models import CharacterMemory
from ..memory_manager import CharacterMemoryManager


class MemoryCard(CardWidget):
    def __init__(self, memory: CharacterMemory, parent=None):
        super().__init__(parent)
        self.memory = memory
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        header_layout = QHBoxLayout()
        
        type_icons = {
            "interaction": "💭",
            "promise": "🤝",
            "gift": "🎁",
            "conflict": "⚡",
            "special": "⭐"
        }
        icon = type_icons.get(self.memory.memory_type, "•")
        
        type_label = StrongBodyLabel(f"{icon} {self._get_type_name()}", self)
        header_layout.addWidget(type_label)
        
        header_layout.addStretch()
        
        importance_stars = "★" * self.memory.importance + "☆" * (10 - self.memory.importance)
        importance_label = CaptionLabel(importance_stars, self)
        importance_label.setStyleSheet("color: #f6e05e;")
        header_layout.addWidget(importance_label)
        
        layout.addLayout(header_layout)
        
        content_label = BodyLabel(self.memory.content, self)
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        
        if self.memory.context:
            context_texts = []
            if "chapter" in self.memory.context:
                context_texts.append(f"第{self.memory.context['chapter']}章")
            if context_texts:
                context_label = CaptionLabel(" | ".join(context_texts), self)
                layout.addWidget(context_label)
        
        self.update_theme()
    
    def _get_type_name(self) -> str:
        type_names = {
            "interaction": "互动",
            "promise": "约定",
            "gift": "礼物",
            "conflict": "冲突",
            "special": "特殊"
        }
        return type_names.get(self.memory.memory_type, self.memory.memory_type)
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#3d3d3d" if is_dark else "#f8f8f8"
        border_color = "#505050" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            MemoryCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)


class CharacterMemoryTab(QWidget):
    def __init__(self, character_name: str, memory_manager: CharacterMemoryManager, parent=None):
        super().__init__(parent)
        self.character_name = character_name
        self.memory_manager = memory_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 统计信息
        summary = self.memory_manager.get_memory_summary(self.character_name)
        summary_layout = QHBoxLayout()
        
        total_label = BodyLabel(f"总计: {summary['total']}条记忆", self)
        summary_layout.addWidget(total_label)
        
        for mem_type, count in summary.items():
            if mem_type != "total" and count > 0:
                type_names = {
                    "interaction": "互动", "promise": "约定",
                    "gift": "礼物", "conflict": "冲突", "special": "特殊"
                }
                label = CaptionLabel(f"{type_names.get(mem_type, mem_type)}: {count}", self)
                summary_layout.addWidget(label)
        
        summary_layout.addStretch()
        layout.addLayout(summary_layout)
        
        # 记忆列表
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.memory_container = QWidget()
        self.memory_layout = QVBoxLayout(self.memory_container)
        self.memory_layout.setContentsMargins(0, 0, 0, 0)
        self.memory_layout.setSpacing(8)
        
        self._load_memories()
        
        self.memory_layout.addStretch()
        scroll.setWidget(self.memory_container)
        layout.addWidget(scroll)
    
    def _load_memories(self):
        memories = self.memory_manager.get_all_memories(self.character_name)
        for memory in memories:
            card = MemoryCard(memory, self)
            self.memory_layout.addWidget(card)


class MemoryDialog(QDialog):
    def __init__(self, memory_manager: CharacterMemoryManager, character_names: List[str], parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.character_names = character_names
        self.setWindowTitle("记忆回顾")
        self.setMinimumSize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = TitleLabel("💭 记忆回顾", self)
        layout.addWidget(title)
        
        desc = BodyLabel("查看角色们记得的事情，这些都是你们共同经历的回忆。", self)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 创建标签页
        self.tab_widget = QTabWidget(self)
        
        for char_name in self.character_names:
            tab = CharacterMemoryTab(char_name, self.memory_manager, self)
            self.tab_widget.addTab(tab, char_name)
        
        layout.addWidget(self.tab_widget)
        
        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = PushButton("关闭", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.update_theme()
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#e0e0e0" if is_dark else "#333333"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QTabWidget::pane {{
                border: 1px solid {"#505050" if is_dark else "#e0e0e0"};
                background-color: {bg_color};
            }}
            QTabBar::tab {{
                background-color: {"#3d3d3d" if is_dark else "#f0f0f0"};
                color: {text_color};
                padding: 8px 16px;
                border: 1px solid {"#505050" if is_dark else "#e0e0e0"};
            }}
            QTabBar::tab:selected {{
                background-color: {"#0078d4" if is_dark else "#3182ce"};
                color: white;
            }}
        """)
