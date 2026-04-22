from typing import List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSpinBox
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    ListWidget, LineEdit, PlainTextEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme
)

from ..models import Character


class CharacterDialog(QDialog):
    def __init__(self, characters: Optional[List[Character]] = None, parent=None):
        super().__init__(parent)
        self._characters = characters or []
        self._current_character = None
        self._current_item = None  # 当前正在编辑的列表项
        self.setWindowTitle("角色配置")
        self.setMinimumSize(600, 500)
        self.init_ui()
        self._load_data()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        left_panel = QFrame(self)
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(180)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        left_layout.addWidget(BodyLabel("角色列表", self))
        
        self.character_list = ListWidget(self)
        self.character_list.setWrapping(True)
        self.character_list.itemClicked.connect(self._on_character_selected)
        left_layout.addWidget(self.character_list)
        
        add_btn = PushButton(FluentIcon.ADD, "添加角色", self)
        add_btn.clicked.connect(self._add_character)
        left_layout.addWidget(add_btn)
        
        delete_btn = PushButton(FluentIcon.DELETE, "删除角色", self)
        delete_btn.clicked.connect(self._delete_character)
        left_layout.addWidget(delete_btn)
        
        layout.addWidget(left_panel)
        
        right_panel = QFrame(self)
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        right_layout.addWidget(TitleLabel("角色详情", self))
        
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)
        
        form_layout.addWidget(BodyLabel("角色名称 *", self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("角色名称")
        form_layout.addWidget(self.name_input)
        
        form_layout.addWidget(BodyLabel("性格描述", self))
        self.personality_input = PlainTextEdit(self)
        self.personality_input.setPlaceholderText("描述角色的性格特点...")
        self.personality_input.setMaximumHeight(60)
        form_layout.addWidget(self.personality_input)
        
        form_layout.addWidget(BodyLabel("背景故事", self))
        self.background_input = PlainTextEdit(self)
        self.background_input.setPlaceholderText("角色的背景故事...")
        self.background_input.setMaximumHeight(80)
        form_layout.addWidget(self.background_input)
        
        aff_layout = QHBoxLayout()
        aff_layout.addWidget(BodyLabel("初始好感度:", self))
        self.affection_spin = QSpinBox(self)
        self.affection_spin.setRange(0, 100)
        self.affection_spin.setValue(50)
        aff_layout.addWidget(self.affection_spin)
        aff_layout.addStretch()
        form_layout.addLayout(aff_layout)
        
        form_layout.addWidget(BodyLabel("与主角关系", self))
        self.relationship_input = LineEdit(self)
        self.relationship_input.setPlaceholderText("如：陌生人、同学、青梅竹马...")
        form_layout.addWidget(self.relationship_input)
        
        right_layout.addLayout(form_layout)
        right_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = PushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存", self)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        right_layout.addLayout(btn_layout)
        
        layout.addWidget(right_panel)
        
        self.update_theme()
    
    def _load_data(self):
        self.character_list.clear()
        for idx, char in enumerate(self._characters):
            self.character_list.addItem(char.name)
            item = self.character_list.item(idx)
            item.setData(Qt.UserRole, char)
        
        if self._characters:
            self.character_list.setCurrentRow(0)
            self._on_character_selected(self.character_list.item(0))
    
    def _on_character_selected(self, item):
        # 先保存当前编辑的角色数据
        self._save_current_character()
        
        # 然后加载新选中的角色
        char = item.data(Qt.UserRole)
        self._current_character = char
        self._current_item = item  # 记录当前编辑的列表项
        
        self.name_input.setText(char.name)
        self.personality_input.setPlainText(char.personality)
        self.background_input.setPlainText(char.background)
        self.affection_spin.setValue(char.initial_affection)
        self.relationship_input.setText(char.relationship)
    
    def _add_character(self):
        self._save_current_character()
        
        new_char = Character(name=f"新角色{len(self._characters) + 1}")
        self._characters.append(new_char)
        
        self.character_list.addItem(new_char.name)
        idx = self.character_list.count() - 1
        item = self.character_list.item(idx)
        item.setData(Qt.UserRole, new_char)
        self.character_list.setCurrentRow(idx)
        self._current_character = new_char
        self._current_item = item  # 记录新添加的列表项
        
        self.name_input.setText(new_char.name)
        self.personality_input.clear()
        self.background_input.clear()
        self.affection_spin.setValue(50)
        self.relationship_input.clear()
    
    def _delete_character(self):
        current_item = self.character_list.currentItem()
        if not current_item:
            return
        
        char = current_item.data(Qt.UserRole)
        if char in self._characters:
            self._characters.remove(char)
        
        self.character_list.takeItem(self.character_list.row(current_item))
        self._current_character = None
        self._current_item = None  # 清除当前编辑的列表项引用
        
        if self.character_list.count() > 0:
            self.character_list.setCurrentRow(0)
            self._on_character_selected(self.character_list.item(0))
        else:
            self.name_input.clear()
            self.personality_input.clear()
            self.background_input.clear()
            self.affection_spin.setValue(50)
            self.relationship_input.clear()
    
    def _save_current_character(self):
        if self._current_character is None:
            return
        
        self._current_character.name = self.name_input.text().strip() or "未命名角色"
        self._current_character.personality = self.personality_input.toPlainText().strip()
        self._current_character.background = self.background_input.toPlainText().strip()
        self._current_character.initial_affection = self.affection_spin.value()
        self._current_character.relationship = self.relationship_input.text().strip() or "陌生人"
        
        # 更新当前编辑的列表项（使用保存的引用，而不是 currentItem()）
        if self._current_item:
            self._current_item.setText(self._current_character.name)
            self._current_item.setData(Qt.UserRole, self._current_character)
    
    def _save(self):
        self._save_current_character()
        self.accept()
    
    def get_characters(self) -> List[Character]:
        return self._characters
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        panel_bg = "#3d3d3d" if is_dark else "#f5f5f5"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#404040" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            #leftPanel, #rightPanel {{
                background-color: {panel_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
            }}
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
            }}
            QListWidget::item:selected {{
                background-color: #0078d4;
                color: #ffffff;
            }}
            QListWidget::item:hover {{
                background-color: #3a3a3a;
            }}
        """)
