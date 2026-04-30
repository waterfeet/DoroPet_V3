from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QGridLayout

from qfluentwidgets import CardWidget, PrimaryPushButton, PushButton, ScrollArea
from qfluentwidgets import FluentIcon as FIF

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_COLORS
)
from src.core.pet_quotes_manager import PetQuotesManager
from src.ui.widgets.greeting_banner import GreetingBanner
from src.ui.widgets.pet_avatar_card import PetAvatarCard
from src.ui.widgets.music_player_card import MusicPlayerCard


class AttributeCard(CardWidget):
    def __init__(self, attr_name: str, parent=None):
        super().__init__(parent)
        self.attr_name = attr_name
        self.setMinimumWidth(180)
        
        self._init_ui()
    
    def _init_ui(self):
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        attr_icons = {
            ATTR_HUNGER: "🍖",
            ATTR_MOOD: "💖",
            ATTR_CLEANLINESS: "✨",
            ATTR_ENERGY: "⚡",
        }
        
        icon_label = QLabel(attr_icons.get(self.attr_name, "📊"))
        icon_label.setObjectName("petAttrIcon")
        icon_label.setStyleSheet("font-size: 20px; background: transparent;")
        
        name_label = QLabel(ATTR_NAMES[self.attr_name])
        name_label.setObjectName("petAttrNameLabel")
        
        self.value_label = QLabel()
        self.value_label.setObjectName(f"value_{self.attr_name}")
        self.value_label.setAlignment(Qt.AlignRight)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.value_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName(f"bar_{self.attr_name}")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        
        self.status_label = QLabel()
        self.status_label.setObjectName(f"status_{self.attr_name}")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(22)
        
        card_layout.addLayout(header_layout)
        card_layout.addWidget(self.progress_bar)
        card_layout.addWidget(self.status_label)
    
    def update_value(self, value: float):
        self.value_label.setText(f"{value:.0f}%")
        self.progress_bar.setValue(int(value))
    
    def update_status(self, status: str):
        if status == "critical":
            status_text = "危急"
            self.status_label.setObjectName("petStatusCritical")
        elif status == "warning":
            status_text = "警告"
            self.status_label.setObjectName("petStatusWarning")
        else:
            status_text = "良好"
            self.status_label.setObjectName("petStatusGood")
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet("")
        
        if status == "critical":
            color = STATUS_COLORS["critical"]
        elif status == "warning":
            color = STATUS_COLORS["warning"]
        else:
            color = STATUS_COLORS["good"]
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
    
    def update_theme(self, is_dark: bool):
        name_label_style = f"font-size: 14px; font-weight: bold; color: {'#e0e0e0' if is_dark else '#333'}; background: transparent;"
        value_label_style = f"font-size: 14px; color: {'#aaa' if is_dark else '#666'};"
        
        for label in self.findChildren(QLabel):
            if label.text() == ATTR_NAMES[self.attr_name]:
                label.setStyleSheet(name_label_style)
            if label.objectName() == f"value_{self.attr_name}":
                label.setStyleSheet(value_label_style)


class PetStatusInterface(ScrollArea):
    interaction_requested = pyqtSignal(str)
    fun_message_requested = pyqtSignal(str)
    start_chat_requested = pyqtSignal()

    def __init__(self, attr_manager=None, db=None, parent=None, pomodoro_interface=None):
        super().__init__(parent)
        self.attr_manager = attr_manager
        self.db = db
        self.pomodoro_interface = pomodoro_interface
        self.quotes_manager = PetQuotesManager(self)
        
        self.setObjectName("PetStatusInterface")
        self.setWidgetResizable(True)
        
        self._container = QWidget()
        self._container.setObjectName("petStatusContainer")
        self.setWidget(self._container)
        
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        self.greeting_banner = GreetingBanner(self.quotes_manager, self)
        main_layout.addWidget(self.greeting_banner)
        
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)
        top_layout.setAlignment(Qt.AlignTop)
        
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        self.avatar_card = PetAvatarCard(self.quotes_manager, self.attr_manager, self)
        left_layout.addWidget(self.avatar_card)
        
        self.music_player_card = MusicPlayerCard(self)
        left_layout.addWidget(self.music_player_card)
        
        self._init_attribute_section(left_layout)
        
        self._init_interaction_buttons(left_layout)
        
        left_layout.addStretch()
        
        top_layout.addWidget(left_section, 2)
        
        if self.pomodoro_interface:
            self.pomodoro_interface.setMinimumWidth(260)
            self.pomodoro_interface.setMaximumWidth(380)
            top_layout.addWidget(self.pomodoro_interface, 1)
        
        main_layout.addWidget(top_section)
        
        main_layout.addStretch()

    def _init_attribute_section(self, parent_layout):
        self.attribute_cards = {}
        
        attrs_container = QWidget()
        attrs_layout = QGridLayout(attrs_container)
        attrs_layout.setSpacing(8)
        attrs_layout.setContentsMargins(0, 0, 0, 0)
        
        attrs_order = [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]
        for i, attr_name in enumerate(attrs_order):
            card = AttributeCard(attr_name, self)
            card.setMinimumWidth(140)
            self.attribute_cards[attr_name] = card
            attrs_layout.addWidget(card, i // 2, i % 2)
        
        parent_layout.addWidget(attrs_container)

    def _init_interaction_buttons(self, parent_layout):
        interaction_layout = QHBoxLayout()
        interaction_layout.setSpacing(8)
        
        button_configs = [
            ("feed", "投喂", FIF.HOME),
            ("play", "玩耍", FIF.PALETTE),
            ("clean", "清洁", FIF.SYNC),
            ("rest", "休息", FIF.BRUSH),
        ]
        
        self.buttons = {}
        for action, text, icon in button_configs:
            btn = PrimaryPushButton(text, self)
            btn.setIcon(icon)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, a=action: self._on_interaction(a))
            interaction_layout.addWidget(btn)
            self.buttons[action] = btn
        
        random_btn = PushButton("💬 开始对话", self)
        random_btn.setFixedHeight(36)
        random_btn.clicked.connect(self._on_start_chat)
        interaction_layout.addWidget(random_btn)
        
        interaction_widget = QWidget()
        interaction_widget.setLayout(interaction_layout)
        parent_layout.addWidget(interaction_widget)

    def _connect_signals(self):
        if self.attr_manager is None:
            return
        self.attr_manager.attribute_changed.connect(self._on_attribute_changed)
        self.attr_manager.status_changed.connect(self._on_status_changed)
    
    def _bind_attributes(self):
        if self.attr_manager is None:
            return
        
        for attr_name, card in self.attribute_cards.items():
            self.attr_manager.bind_attribute_widget(
                attr_name,
                card.update_value,
                card.update_status
            )

    def _apply_event_bonuses(self, bonuses: dict):
        if not self.attr_manager or not bonuses:
            return
        
        from src.core.pet_constants import ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY
        
        attr_map = {
            "hunger": ATTR_HUNGER,
            "mood": ATTR_MOOD,
            "cleanliness": ATTR_CLEANLINESS,
            "energy": ATTR_ENERGY,
        }
        
        for key, value in bonuses.items():
            if key in attr_map:
                attr_name = attr_map[key]
                current = self.attr_manager.get_attribute(attr_name)
                new_value = max(0, min(100, current + value))
                self.attr_manager.set_attribute(attr_name, new_value)

    def _on_attribute_changed(self, attr_name: str, new_value: float, old_value: float):
        pass

    def _on_status_changed(self, attr_name: str, new_status: str, old_status: str):
        pass

    def set_attr_manager(self, attr_manager):
        self.attr_manager = attr_manager
        self.avatar_card.set_attr_manager(attr_manager)
        self._connect_signals()
        self._bind_attributes()

    def _on_interaction(self, interaction_type: str):
        if self.attr_manager:
            self.attr_manager.perform_interaction(interaction_type)
            
            if self.quotes_manager:
                response = self.quotes_manager.get_interaction_response(interaction_type)
                self.avatar_card.quote_label.setText(response)
        
        self.interaction_requested.emit(interaction_type)

    def _random_interaction(self):
        import random
        interactions = ["feed", "play", "clean", "rest"]
        weights = [0.3, 0.4, 0.15, 0.15]
        
        chosen = random.choices(interactions, weights=weights)[0]
        self._on_interaction(chosen)

    def _on_start_chat(self):
        self.start_chat_requested.emit()

    def update_theme(self, is_dark: bool):
        self.greeting_banner.update_theme(is_dark)
        self.avatar_card.update_theme(is_dark)
        self.music_player_card.update_theme(is_dark)
        
        for attr_name, card in self.attribute_cards.items():
            card.update_theme(is_dark)
            
            bar_bg = '#2d2d2d' if is_dark else '#f0f0f0'
            status = self.attr_manager.get_status(attr_name) if self.attr_manager else "good"
            if status == "critical":
                color = STATUS_COLORS["critical"]
            elif status == "warning":
                color = STATUS_COLORS["warning"]
            else:
                color = STATUS_COLORS["good"]
            card.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    border-radius: 4px;
                    background-color: {bar_bg};
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)
            
            if self.attr_manager:
                status = self.attr_manager.get_status(attr_name)
                if status == "critical":
                    status_text = "危急"
                    bg_color = "#4a1c1c" if is_dark else "#ffebee"
                    text_color = "#ef5350" if is_dark else "#f44336"
                elif status == "warning":
                    status_text = "警告"
                    bg_color = "#4a3a1c" if is_dark else "#fff3e0"
                    text_color = "#ffa726" if is_dark else "#ff9800"
                else:
                    status_text = "良好"
                    bg_color = "#1c4a2c" if is_dark else "#e8f5e9"
                    text_color = "#66bb6a" if is_dark else "#4caf50"
                card.status_label.setText(status_text)
                card.status_label.setStyleSheet(f"""
                    font-size: 11px;
                    padding: 2px 10px;
                    border-radius: 11px;
                    background-color: {bg_color};
                    color: {text_color};
                """)
