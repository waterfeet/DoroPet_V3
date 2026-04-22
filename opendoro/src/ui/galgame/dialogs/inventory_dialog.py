from typing import List, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    PrimaryPushButton, PushButton, TitleLabel, BodyLabel,
    FluentIcon, isDarkTheme, InfoBar, InfoBarPosition
)

from ..models import GameState


class InventoryDialog(QDialog):
    item_used = pyqtSignal(dict)
    
    def __init__(self, state: GameState, parent=None):
        super().__init__(parent)
        self._state = state
        self._used_item = None
        self.setWindowTitle("背包")
        self.setMinimumSize(450, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        title = TitleLabel("背包", self)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        currency_label = BodyLabel(f"💰 金币: {self._state.currency}", self)
        header_layout.addWidget(currency_label)
        
        layout.addLayout(header_layout)
        
        if not self._state.inventory:
            empty_label = BodyLabel("背包空空如也...\n\n可以在商店购买物品，或在冒险中获得！", self)
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #7f8c8d; font-size: 14px;")
            layout.addWidget(empty_label)
        else:
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            self.items_container = QWidget()
            self.items_layout = QVBoxLayout(self.items_container)
            self.items_layout.setContentsMargins(0, 0, 0, 0)
            self.items_layout.setSpacing(8)
            
            for item in self._state.inventory:
                card = self._create_item_card(item)
                self.items_layout.addWidget(card)
            
            self.items_layout.addStretch()
            
            scroll.setWidget(self.items_container)
            layout.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = PushButton("关闭", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.update_theme()
    
    def _create_item_card(self, item: Dict) -> QFrame:
        card = QFrame()
        card.setObjectName("inventoryCard")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = BodyLabel(item.get('name', '未知物品'), card)
        name_label.setObjectName("itemName")
        font = name_label.font()
        font.setBold(True)
        name_label.setFont(font)
        info_layout.addWidget(name_label)
        
        desc_label = BodyLabel(item.get('description', '无描述'), card)
        desc_label.setObjectName("itemDesc")
        info_layout.addWidget(desc_label)
        
        effect = item.get('effect', {})
        effect_text = self._get_effect_description(effect)
        if effect_text:
            effect_label = BodyLabel(f"效果: {effect_text}", card)
            effect_label.setObjectName("itemEffect")
            effect_label.setStyleSheet("color: #63b3ed; font-size: 12px;")
            info_layout.addWidget(effect_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        use_btn = PrimaryPushButton("使用", card)
        use_btn.setProperty("item_data", item)
        use_btn.clicked.connect(self._use_item)
        layout.addWidget(use_btn)
        
        return card
    
    def _get_effect_description(self, effect: Dict) -> str:
        if not effect:
            return ""
        
        effect_type = effect.get('type', '')
        
        if effect_type == 'affection_all':
            return f"所有角色好感度+{effect.get('value', 0)}"
        elif effect_type == 'affection_single':
            return f"单个角色好感度+{effect.get('value', 0)}"
        elif effect_type == 'protect_affection':
            return "防止一次好感度下降"
        elif effect_type == 'unlock_story':
            return "解锁隐藏剧情"
        elif effect_type == 'rollback':
            return "回退到上一个选择点"
        elif effect_type == 'currency':
            return f"获得{effect.get('value', 0)}金币"
        
        return ""
    
    def _use_item(self):
        btn = self.sender()
        if not btn:
            return
        
        item_data = btn.property("item_data")
        if not item_data:
            return
        
        effect = item_data.get('effect', {})
        effect_type = effect.get('type', '')
        
        if effect_type == 'affection_all':
            value = effect.get('value', 5)
            for aff in self._state.affections:
                aff.affection = min(100, aff.affection + value)
            
            self._state.inventory.remove(item_data)
            self._used_item = item_data
            
            InfoBar.success(
                title="使用成功",
                content=f"所有角色好感度+{value}！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            self.item_used.emit(item_data)
            self.accept()
            
        elif effect_type == 'currency':
            value = effect.get('value', 50)
            self._state.currency += value
            self._state.inventory.remove(item_data)
            self._used_item = item_data
            
            InfoBar.success(
                title="使用成功",
                content=f"获得{value}金币！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            self.item_used.emit(item_data)
            self.accept()
            
        elif effect_type == 'affection_single':
            from PyQt5.QtWidgets import QInputDialog
            char_names = [aff.character_name for aff in self._state.affections]
            if char_names:
                name, ok = QInputDialog.getItem(
                    self, "选择角色", "选择要增加好感度的角色：", char_names, 0, False
                )
                if ok and name:
                    value = effect.get('value', 10)
                    for aff in self._state.affections:
                        if aff.character_name == name:
                            aff.affection = min(100, aff.affection + value)
                            break
                    
                    self._state.inventory.remove(item_data)
                    self._used_item = item_data
                    
                    InfoBar.success(
                        title="使用成功",
                        content=f"{name}的好感度+{value}！",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    
                    self.item_used.emit(item_data)
                    self.accept()
        else:
            InfoBar.warning(
                title="提示",
                content="该物品需要在特定场景中使用",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def get_updated_state(self) -> GameState:
        return self._state
    
    def get_used_item(self) -> Dict:
        return self._used_item
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        card_bg = "#3d3d3d" if is_dark else "#f8f8f8"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#404040" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            #inventoryCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #itemName {{
                color: {text_color};
                font-size: 14px;
            }}
            #itemDesc {{
                color: #a0aec0;
                font-size: 12px;
            }}
        """)
