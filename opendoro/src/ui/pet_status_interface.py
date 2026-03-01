from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QGridLayout, QSpacerItem, QSizePolicy, QScrollArea

from qfluentwidgets import CardWidget, PrimaryPushButton, PushButton, setStyleSheet, ScrollArea, BodyLabel
from qfluentwidgets import FluentIcon as FIF

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_COLORS, RECOVERY_VALUES
)
from src.core.pet_quotes_manager import PetQuotesManager
from src.core.pet_fun_manager import PetFunManager
from src.ui.widgets.greeting_banner import GreetingBanner
from src.ui.widgets.pet_avatar_card import PetAvatarCard
from src.ui.widgets.fun_games import FunInteractionPanel


class PetStatusInterface(ScrollArea):
    interaction_requested = pyqtSignal(str)
    fun_message_requested = pyqtSignal(str)

    def __init__(self, attr_manager=None, parent=None):
        super().__init__(parent)
        self.attr_manager = attr_manager
        self.quotes_manager = PetQuotesManager(self)
        self.fun_manager = PetFunManager(self)
        
        self.setObjectName("PetStatusInterface")
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._container = QWidget()
        self.setWidget(self._container)
        
        self._init_ui()
        self._connect_signals()
        self._update_all_attributes()

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
        
        self.avatar_card = PetAvatarCard(self.quotes_manager, self.attr_manager, self)
        top_layout.addWidget(self.avatar_card, 2)
        
        self.fun_panel = FunInteractionPanel(self.fun_manager, self)
        self.fun_panel.setMinimumWidth(260)
        self.fun_panel.event_triggered_with_bonuses = True
        top_layout.addWidget(self.fun_panel, 1)
        
        self._last_event_bonuses = {}
        
        main_layout.addWidget(top_section)
        
        self.event_notification = CardWidget(self._container)
        self.event_notification.setFixedHeight(50)
        event_layout = QHBoxLayout(self.event_notification)
        event_layout.setContentsMargins(15, 8, 15, 8)
        
        self.event_icon_label = QLabel("🎉")
        self.event_icon_label.setStyleSheet("font-size: 20px;")
        self.event_text_label = BodyLabel("点击「随机事件」看看会发生什么吧！")
        self.event_text_label.setStyleSheet("font-size: 14px; color: #666;")
        
        event_layout.addWidget(self.event_icon_label)
        event_layout.addWidget(self.event_text_label, 1)
        
        self.event_notification.hide()
        main_layout.addWidget(self.event_notification)
        
        self._event_hide_timer = QTimer(self)
        self._event_hide_timer.setSingleShot(True)
        self._event_hide_timer.timeout.connect(self._hide_event_notification)
        
        self._init_attribute_section(main_layout)
        
        self._init_interaction_buttons(main_layout)
        
        main_layout.addStretch()

    def _init_attribute_section(self, main_layout):
        attrs_title = QLabel("属性状态")
        attrs_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        main_layout.addWidget(attrs_title)
        
        self.attribute_cards = {}
        
        attrs_container = QWidget()
        attrs_layout = QGridLayout(attrs_container)
        attrs_layout.setSpacing(12)
        attrs_layout.setContentsMargins(0, 0, 0, 0)
        
        attrs_order = [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]
        for i, attr_name in enumerate(attrs_order):
            card = self._create_compact_attribute_card(attr_name)
            self.attribute_cards[attr_name] = card
            attrs_layout.addWidget(card, 0, i)
        
        main_layout.addWidget(attrs_container)

    def _create_compact_attribute_card(self, attr_name: str) -> CardWidget:
        card = CardWidget(self)
        card.setMinimumWidth(180)
        
        card_layout = QVBoxLayout(card)
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
        
        icon_label = QLabel(attr_icons.get(attr_name, "📊"))
        icon_label.setStyleSheet("font-size: 20px; background: transparent;")
        
        name_label = QLabel(ATTR_NAMES[attr_name])
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        
        value_label = QLabel()
        value_label.setObjectName(f"value_{attr_name}")
        value_label.setAlignment(Qt.AlignRight)
        value_label.setStyleSheet("font-size: 14px; color: #666;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(value_label)
        
        progress_bar = QProgressBar()
        progress_bar.setObjectName(f"bar_{attr_name}")
        progress_bar.setRange(0, 100)
        progress_bar.setFixedHeight(8)
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                border-radius: 4px;
            }
        """)
        
        status_label = QLabel()
        status_label.setObjectName(f"status_{attr_name}")
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setFixedHeight(22)
        status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                padding: 2px 10px;
                border-radius: 11px;
            }
        """)
        
        card_layout.addLayout(header_layout)
        card_layout.addWidget(progress_bar)
        card_layout.addWidget(status_label)
        
        return card

    def _init_interaction_buttons(self, main_layout):
        interaction_layout = QHBoxLayout()
        interaction_layout.setSpacing(12)
        
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
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, a=action: self._on_interaction(a))
            interaction_layout.addWidget(btn)
            self.buttons[action] = btn
        
        random_btn = PushButton("🎲 随机互动", self)
        random_btn.setFixedHeight(40)
        random_btn.clicked.connect(self._random_interaction)
        interaction_layout.addWidget(random_btn)
        
        interaction_widget = QWidget()
        interaction_widget.setLayout(interaction_layout)
        main_layout.addWidget(interaction_widget)

    def _connect_signals(self):
        if self.attr_manager is None:
            return
        self.attr_manager.attribute_changed.connect(self._on_attribute_changed)
        self.attr_manager.status_changed.connect(self._on_status_changed)
        
        self.fun_manager.fun_event_triggered.connect(self._on_fun_event)
        self.fun_manager.game_result.connect(self._on_game_result)
        self.fun_panel.fun_event_triggered.connect(self._on_fun_message)
        self.fun_panel.event_bonuses_ready.connect(self._apply_event_bonuses)
        self.fun_panel.event_with_type.connect(self._show_event_notification)

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
        self._update_single_attribute(attr_name)

    def _on_status_changed(self, attr_name: str, new_status: str, old_status: str):
        self._update_single_attribute(attr_name)

    def _update_single_attribute(self, attr_name: str):
        if attr_name not in self.attribute_cards:
            return
        
        if self.attr_manager is None:
            return
        
        value = self.attr_manager.get_attribute(attr_name)
        status = self.attr_manager.get_status(attr_name)
        
        card = self.attribute_cards[attr_name]
        
        value_label = card.findChild(QLabel, f"value_{attr_name}")
        if value_label:
            value_label.setText(f"{value:.0f}%")
        
        status_label = card.findChild(QLabel, f"status_{attr_name}")
        if status_label:
            if status == "critical":
                status_text = "危急"
                bg_color = "#ffebee"
                text_color = "#f44336"
            elif status == "warning":
                status_text = "警告"
                bg_color = "#fff3e0"
                text_color = "#ff9800"
            else:
                status_text = "良好"
                bg_color = "#e8f5e9"
                text_color = "#4caf50"
            status_label.setText(status_text)
            status_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 11px;
                    padding: 2px 10px;
                    border-radius: 11px;
                    background-color: {bg_color};
                    color: {text_color};
                }}
            """)
        
        bar = card.findChild(QProgressBar, f"bar_{attr_name}")
        if bar:
            bar.setValue(int(value))
            if status == "critical":
                color = STATUS_COLORS["critical"]
            elif status == "warning":
                color = STATUS_COLORS["warning"]
            else:
                color = STATUS_COLORS["good"]
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)

    def _update_all_attributes(self):
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            self._update_single_attribute(attr_name)

    def set_attr_manager(self, attr_manager):
        self.attr_manager = attr_manager
        self.avatar_card.set_attr_manager(attr_manager)
        self._connect_signals()
        self._update_all_attributes()

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

    def _on_fun_event(self, name: str, description: str):
        self.avatar_card.quote_label.setText(description)
        self.fun_message_requested.emit(description)

    def _on_game_result(self, game_type: str, message: str, result: int):
        pass

    def _on_fun_message(self, message: str):
        self.avatar_card.quote_label.setText(message)
        self.fun_message_requested.emit(message)
    
    def _show_event_notification(self, message: str, is_positive: bool = True):
        if is_positive:
            self.event_icon_label.setText("🎉")
            self.event_notification.setStyleSheet("""
                CardWidget {
                    background-color: #e8f5e9;
                    border: 1px solid #a5d6a7;
                    border-radius: 8px;
                }
            """)
            self.event_text_label.setStyleSheet("font-size: 14px; color: #2e7d32;")
        else:
            self.event_icon_label.setText("😅")
            self.event_notification.setStyleSheet("""
                CardWidget {
                    background-color: #fff3e0;
                    border: 1px solid #ffcc80;
                    border-radius: 8px;
                }
            """)
            self.event_text_label.setStyleSheet("font-size: 14px; color: #e65100;")
        
        self.event_text_label.setText(message)
        self.event_notification.show()
        self._event_hide_timer.start(5000)
    
    def _hide_event_notification(self):
        self.event_notification.hide()

    def update_theme(self, is_dark: bool):
        self.greeting_banner.update_theme(is_dark)
        self.avatar_card.update_theme(is_dark)
        
        title_style = f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {'#e0e0e0' if is_dark else '#333'};
            }}
        """
        for child in self.findChildren(QLabel):
            if child.objectName() == "":
                if child.text() == "属性状态":
                    child.setStyleSheet(title_style)
        
        for attr_name, card in self.attribute_cards.items():
            name_label = card.findChild(QLabel, f"name_{attr_name}")
            for label in card.findChildren(QLabel):
                if not label.objectName().startswith("value_") and not label.objectName().startswith("status_"):
                    if label.text() == ATTR_NAMES[attr_name]:
                        label.setStyleSheet(f"""
                            QLabel {{
                                font-size: 14px;
                                font-weight: bold;
                                color: {'#e0e0e0' if is_dark else '#333'};
                                background: transparent;
                            }}
                        """)
            
            value_label = card.findChild(QLabel, f"value_{attr_name}")
            if value_label:
                value_label.setStyleSheet(f"""
                    QLabel {{
                        font-size: 14px;
                        color: {'#aaa' if is_dark else '#666'};
                    }}
                """)
            
            bar = card.findChild(QProgressBar, f"bar_{attr_name}")
            if bar:
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: none;
                        border-radius: 4px;
                        background-color: {'#2d2d2d' if is_dark else '#f0f0f0'};
                    }}
                    QProgressBar::chunk {{
                        border-radius: 4px;
                    }}
                """)
                status = self.attr_manager.get_status(attr_name) if self.attr_manager else "good"
                if status == "critical":
                    color = STATUS_COLORS["critical"]
                elif status == "warning":
                    color = STATUS_COLORS["warning"]
                else:
                    color = STATUS_COLORS["good"]
                bar.setStyleSheet(bar.styleSheet().replace("}", f"background-color: {color};}}", 1))
