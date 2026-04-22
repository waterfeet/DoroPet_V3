from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    PushButton, PrimaryPushButton, TitleLabel, BodyLabel,
    StrongBodyLabel, CaptionLabel, isDarkTheme
)

from ..models import GameEnding


class EndingDialog(QDialog):
    def __init__(self, ending: GameEnding, parent=None):
        super().__init__(parent)
        self.ending = ending
        self.setWindowTitle("游戏结局")
        self.setMinimumSize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # 结局类型图标
        type_icons = {
            "perfect": "💕",
            "harem": "🌸",
            "normal": "📖",
            "lonely": "💔"
        }
        icon = type_icons.get(self.ending.ending_type, "📖")
        
        # 结局标题
        title = TitleLabel(f"{icon} {self.ending.ending_title}", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 结局描述
        desc = BodyLabel(self.ending.ending_description, self)
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 分隔线
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("separator")
        layout.addWidget(line)
        
        # 结局故事
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        story_container = QWidget()
        story_layout = QVBoxLayout(story_container)
        story_layout.setContentsMargins(16, 16, 16, 16)
        
        story_label = BodyLabel(self.ending.ending_story, self)
        story_label.setWordWrap(True)
        story_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        story_layout.addWidget(story_label)
        
        story_layout.addStretch()
        scroll.setWidget(story_container)
        layout.addWidget(scroll, 1)
        
        # 统计信息
        stats_frame = QFrame(self)
        stats_frame.setObjectName("statsFrame")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(24)
        
        stats_layout.addWidget(self._create_stat_item("最终好感度", str(self.ending.final_affection)))
        stats_layout.addWidget(self._create_stat_item("总章节", str(self.ending.total_chapters)))
        stats_layout.addWidget(self._create_stat_item("游玩时长", self.ending.play_time))
        
        if self.ending.character_name:
            stats_layout.addWidget(self._create_stat_item("结局角色", self.ending.character_name))
        
        stats_layout.addStretch()
        layout.addWidget(stats_frame)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        continue_btn = PushButton("继续游戏", self)
        continue_btn.clicked.connect(self._on_continue)
        btn_layout.addWidget(continue_btn)
        
        new_game_btn = PrimaryPushButton("开始新游戏", self)
        new_game_btn.clicked.connect(self._on_new_game)
        btn_layout.addWidget(new_game_btn)
        
        layout.addLayout(btn_layout)
        
        self._continue_clicked = False
        self._new_game_clicked = False
        
        self.update_theme()
    
    def _create_stat_item(self, label: str, value: str) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label_widget = CaptionLabel(label, self)
        label_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_widget)
        
        value_widget = StrongBodyLabel(value, self)
        value_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_widget)
        
        return widget
    
    def _on_continue(self):
        self._continue_clicked = True
        self.accept()
    
    def _on_new_game(self):
        self._new_game_clicked = True
        self.accept()
    
    def should_continue(self) -> bool:
        return self._continue_clicked
    
    def should_start_new_game(self) -> bool:
        return self._new_game_clicked
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        card_bg = "#3d3d3d" if is_dark else "#f8f8f8"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#505050" if is_dark else "#e0e0e0"
        
        # 结局类型颜色
        type_colors = {
            "perfect": "#f687b3",
            "harem": "#f6e05e",
            "normal": "#63b3ed",
            "lonely": "#a0aec0"
        }
        accent_color = type_colors.get(self.ending.ending_type, "#63b3ed")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            #separator {{
                background-color: {border_color};
                max-height: 1px;
            }}
            #statsFrame {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QScrollArea {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: {card_bg};
            }}
        """)


class EndingListDialog(QDialog):
    def __init__(self, endings, parent=None):
        super().__init__(parent)
        self.endings = endings
        self.setWindowTitle("结局记录")
        self.setMinimumSize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = TitleLabel("🏆 结局记录", self)
        layout.addWidget(title)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        for ending in self.endings:
            card = self._create_ending_card(ending)
            container_layout.addWidget(card)
        
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        close_btn = PushButton("关闭", self)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        self.update_theme()
    
    def _create_ending_card(self, ending: GameEnding) -> QFrame:
        card = QFrame(self)
        card.setObjectName("endingCard")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        type_icons = {
            "perfect": "💕",
            "harem": "🌸",
            "normal": "📖",
            "lonely": "💔"
        }
        icon = type_icons.get(ending.ending_type, "📖")
        
        icon_label = QLabel(icon, self)
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        title_label = StrongBodyLabel(ending.ending_title, self)
        info_layout.addWidget(title_label)
        
        desc_label = CaptionLabel(ending.ending_description, self)
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, 1)
        
        stats_label = CaptionLabel(f"好感度: {ending.final_affection} | 章节: {ending.total_chapters}", self)
        layout.addWidget(stats_label)
        
        return card
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        card_bg = "#3d3d3d" if is_dark else "#f8f8f8"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#505050" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            #endingCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QScrollArea {{
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)
