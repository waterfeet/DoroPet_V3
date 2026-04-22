from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    LineEdit, PlainTextEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme
)

from ..models import Protagonist


class ProtagonistDialog(QDialog):
    def __init__(self, protagonist: Optional[Protagonist] = None, parent=None):
        super().__init__(parent)
        self._protagonist = protagonist or Protagonist()
        self.setWindowTitle("主角配置")
        self.setMinimumSize(450, 400)
        self.init_ui()
        self._load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = TitleLabel("主角配置", self)
        layout.addWidget(title)
        
        layout.addWidget(BodyLabel("主角名称", self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("输入主角名称")
        layout.addWidget(self.name_input)
        
        layout.addWidget(BodyLabel("性格描述", self))
        self.personality_input = PlainTextEdit(self)
        self.personality_input.setPlaceholderText("描述主角的性格特点，如：勇敢、善良、有些内向...")
        self.personality_input.setMaximumHeight(80)
        layout.addWidget(self.personality_input)
        
        layout.addWidget(BodyLabel("背景故事", self))
        self.background_input = PlainTextEdit(self)
        self.background_input.setPlaceholderText("描述主角的背景故事...")
        self.background_input.setMaximumHeight(100)
        layout.addWidget(self.background_input)
        
        layout.addWidget(BodyLabel("特殊特点 (用逗号分隔)", self))
        self.traits_input = LineEdit(self)
        self.traits_input.setPlaceholderText("如：善于观察, 有领导力, 擅长魔法")
        layout.addWidget(self.traits_input)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = PushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存", self)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        self.update_theme()
    
    def _load_data(self):
        self.name_input.setText(self._protagonist.name)
        self.personality_input.setPlainText(self._protagonist.personality)
        self.background_input.setPlainText(self._protagonist.background)
        self.traits_input.setText(", ".join(self._protagonist.traits))
    
    def _save(self):
        self._protagonist.name = self.name_input.text().strip() or "主角"
        self._protagonist.personality = self.personality_input.toPlainText().strip()
        self._protagonist.background = self.background_input.toPlainText().strip()
        
        traits_text = self.traits_input.text().strip()
        self._protagonist.traits = [
            t.strip() for t in traits_text.split(",") if t.strip()
        ]
        
        self.accept()
    
    def get_protagonist(self) -> Protagonist:
        return self._protagonist
    
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
        """)
