from typing import Optional
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    LineEdit, PlainTextEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme
)

from ..models import WorldSetting


class WorldDialog(QDialog):
    def __init__(self, world_setting: Optional[WorldSetting] = None, parent=None):
        super().__init__(parent)
        self._world_setting = world_setting or WorldSetting()
        self.setWindowTitle("世界观配置")
        self.setMinimumSize(500, 520)
        self.init_ui()
        self._load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = TitleLabel("世界观配置", self)
        layout.addWidget(title)
        
        layout.addWidget(BodyLabel("世界名称", self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("如：魔法学院、未来都市、奇幻大陆...")
        layout.addWidget(self.name_input)
        
        layout.addWidget(BodyLabel("时代背景", self))
        self.era_input = LineEdit(self)
        self.era_input.setPlaceholderText("如：中世纪、现代、未来、架空...")
        layout.addWidget(self.era_input)
        
        layout.addWidget(BodyLabel("世界规则/设定", self))
        self.rules_input = PlainTextEdit(self)
        self.rules_input.setPlaceholderText(
            "描述这个世界的基本规则和设定...\n"
            "例如：这是一个魔法与科技共存的世界，人们通过魔力水晶获得魔法力量..."
        )
        self.rules_input.setMaximumHeight(100)
        layout.addWidget(self.rules_input)
        
        layout.addWidget(BodyLabel("特殊元素 (用逗号分隔)", self))
        self.elements_input = LineEdit(self)
        self.elements_input.setPlaceholderText("如：魔法, 魔物, 神秘遗迹, 古老预言")
        layout.addWidget(self.elements_input)
        
        layout.addWidget(BodyLabel("写作风格", self))
        self.style_input = LineEdit(self)
        self.style_input.setPlaceholderText("如：轻松幽默、沉重悲伤、浪漫甜蜜...")
        self.style_input.setReadOnly(True)
        layout.addWidget(self.style_input)
        
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
        self.name_input.setText(self._world_setting.name)
        self.era_input.setText(self._world_setting.era)
        self.rules_input.setPlainText(self._world_setting.rules)
        self.elements_input.setText(", ".join(self._world_setting.special_elements))
        self.style_input.setText(self._world_setting.writing_style)
    
    def _save(self):
        self._world_setting.name = self.name_input.text().strip() or "未知世界"
        self._world_setting.era = self.era_input.text().strip() or "未知时代"
        self._world_setting.rules = self.rules_input.toPlainText().strip()
        
        elements_text = self.elements_input.text().strip()
        self._world_setting.special_elements = [
            e.strip() for e in elements_text.split(",") if e.strip()
        ]
        
        self.accept()
    
    def get_world_setting(self) -> WorldSetting:
        return self._world_setting
    
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
