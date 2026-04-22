from typing import List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    PrimaryPushButton, PushButton, TitleLabel, BodyLabel,
    FluentIcon, isDarkTheme
)

from ..models import GameItem, GameState
from ..database import GalgameDatabase


class ShopDialog(QDialog):
    def __init__(self, db: GalgameDatabase, current_state: GameState, parent=None):
        super().__init__(parent)
        self._db = db
        self._current_state = current_state
        self._items = []
        self._purchased_items = []
        self.setWindowTitle("商店")
        self.setMinimumSize(500, 450)
        self.init_ui()
        self._load_items()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        title = TitleLabel("商店", self)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.currency_label = BodyLabel(f"💰 当前金币: {self._current_state.currency}", self)
        header_layout.addWidget(self.currency_label)
        
        layout.addLayout(header_layout)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        
        scroll.setWidget(self.items_container)
        layout.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = PushButton("关闭", self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.update_theme()
    
    def _load_items(self):
        self._items = self._db.get_items()
        
        for item in self._items:
            card = self._create_item_card(item)
            self.items_layout.addWidget(card)
        
        self.items_layout.addStretch()
    
    def _create_item_card(self, item: GameItem) -> QFrame:
        card = QFrame()
        card.setObjectName("itemCard")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = BodyLabel(item.name, card)
        name_label.setObjectName("itemName")
        font = name_label.font()
        font.setBold(True)
        name_label.setFont(font)
        info_layout.addWidget(name_label)
        
        desc_label = BodyLabel(item.description, card)
        desc_label.setObjectName("itemDesc")
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        price_label = BodyLabel(f"💰 {item.price}", card)
        price_label.setObjectName("itemPrice")
        layout.addWidget(price_label)
        
        buy_btn = PrimaryPushButton("购买", card)
        buy_btn.setProperty("item_id", item.id)
        buy_btn.setProperty("item_price", item.price)
        buy_btn.setProperty("item_name", item.name)
        buy_btn.clicked.connect(self._buy_item)
        
        if self._current_state.currency < item.price:
            buy_btn.setEnabled(False)
            buy_btn.setText("金币不足")
        
        layout.addWidget(buy_btn)
        
        return card
    
    def _buy_item(self):
        btn = self.sender()
        if not btn:
            return
        
        item_id = btn.property("item_id")
        item_price = btn.property("item_price")
        item_name = btn.property("item_name")
        
        if self._current_state.currency >= item_price:
            self._current_state.currency -= item_price
            self._purchased_items.append(item_id)
            
            item_data = None
            for item in self._items:
                if item.id == item_id:
                    item_data = {
                        'id': item.id,
                        'name': item.name,
                        'description': item.description,
                        'price': item.price,
                        'effect': item.effect,
                        'category': item.category,
                        'icon': item.icon
                    }
                    break
            
            if item_data:
                self._current_state.inventory.append(item_data)
            
            self.currency_label.setText(f"💰 当前金币: {self._current_state.currency}")
            
            btn.setEnabled(False)
            btn.setText("已购买")
            
            self._update_buttons()
    
    def _update_buttons(self):
        for i in range(self.items_layout.count()):
            card = self.items_layout.itemAt(i).widget()
            if card and isinstance(card, QFrame):
                for child in card.findChildren(PushButton):
                    if child.text() == "购买":
                        price = child.property("item_price")
                        if self._current_state.currency < price:
                            child.setEnabled(False)
                            child.setText("金币不足")
    
    def get_purchased_items(self) -> List[int]:
        return self._purchased_items
    
    def get_updated_state(self) -> GameState:
        return self._current_state
    
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
            #itemCard {{
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
            #itemPrice {{
                color: #f6e05e;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
