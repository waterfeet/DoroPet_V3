from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QGridLayout

from qfluentwidgets import CardWidget, PrimaryPushButton, PushButton, ScrollArea, isDarkTheme
from qfluentwidgets import FluentIcon as FIF

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_COLORS, ORANGE_INTERACTION_COST,
    DORO_LEVEL_THRESHOLDS, DORO_LEVEL_TITLES
)
from src.core.pet_quotes_manager import PetQuotesManager
from src.ui.widgets.greeting_banner import GreetingBanner
from src.ui.widgets.pet_avatar_card import PetAvatarCard
from src.ui.widgets.music_player_card import MusicPlayerCard


class AttributeCard(CardWidget):
    def __init__(self, attr_name: str, parent=None):
        super().__init__(parent)
        self.attr_name = attr_name
        self.setMinimumWidth(160)
        
        self._init_ui()
    
    def _init_ui(self):
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(10, 7, 10, 7)
        card_layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        attr_icons = {
            ATTR_HUNGER: "🍖",
            ATTR_MOOD: "💖",
            ATTR_CLEANLINESS: "✨",
            ATTR_ENERGY: "⚡",
        }
        
        icon_label = QLabel(attr_icons.get(self.attr_name, "📊"))
        icon_label.setObjectName("petAttrIcon")
        icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        
        name_label = QLabel(ATTR_NAMES[self.attr_name])
        name_label.setObjectName("petAttrNameLabel")
        name_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        self.value_label = QLabel()
        self.value_label.setObjectName(f"value_{self.attr_name}")
        self.value_label.setAlignment(Qt.AlignRight)
        self.value_label.setStyleSheet("font-size: 12px;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.value_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName(f"bar_{self.attr_name}")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        
        self.status_label = QLabel()
        self.status_label.setObjectName(f"status_{self.attr_name}")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(18)
        self.status_label.setStyleSheet("font-size: 10px;")
        
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


class OrangeStatusCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("orangeStatusCard")
        self.setMinimumHeight(62)
        self.setMaximumHeight(62)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        self._orange_label = QLabel("🍊 × 0")
        self._orange_label.setObjectName("orangeStatusCountLabel")

        level_widget = QWidget()
        level_layout = QHBoxLayout(level_widget)
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.setSpacing(6)

        self._level_label = QLabel("⭐ Lv.1  Doro崽")
        self._level_label.setObjectName("orangeStatusLevelLabel")

        self._level_bar = QProgressBar()
        self._level_bar.setObjectName("orangeStatusLevelBar")
        self._level_bar.setRange(0, 100)
        self._level_bar.setFixedHeight(5)
        self._level_bar.setTextVisible(False)
        self._level_bar.setFixedWidth(80)

        level_layout.addWidget(self._level_label)
        level_layout.addWidget(self._level_bar)

        left_layout.addWidget(self._orange_label)
        left_layout.addWidget(level_widget)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._combo_label = QLabel("")
        self._combo_label.setObjectName("orangeStatusComboLabel")
        self._combo_label.setAlignment(Qt.AlignRight)

        self._total_label = QLabel("累计 0 🍊")
        self._total_label.setObjectName("orangeStatusTotalLabel")
        self._total_label.setAlignment(Qt.AlignRight)

        right_layout.addWidget(self._combo_label)
        right_layout.addWidget(self._total_label)

        layout.addWidget(left)
        layout.addStretch()
        layout.addWidget(right)

    def update_display(self, balance: int, total_earned: int, level: int, 
                       total_pomodoros: int, combo: int, is_dark: bool = False):
        self._orange_label.setText(f"🍊 × {balance}")
        title = DORO_LEVEL_TITLES.get(level, "Doro崽")
        self._level_label.setText(f"⭐ Lv.{level} {title}")

        next_level = level + 1
        if next_level in DORO_LEVEL_THRESHOLDS:
            current_threshold = DORO_LEVEL_THRESHOLDS.get(level, 0)
            next_threshold = DORO_LEVEL_THRESHOLDS[next_level]
            progress = ((total_pomodoros - current_threshold) / 
                        (next_threshold - current_threshold) * 100)
            self._level_bar.setValue(int(min(max(progress, 0), 100)))
        else:
            self._level_bar.setValue(100)

        self._total_label.setText(f"累计 {total_earned} 🍊")

        if combo >= 2:
            self._combo_label.setText(f"🔥x{combo}")
            self._combo_label.setVisible(True)
        else:
            self._combo_label.setVisible(False)

        self._apply_theme(is_dark)

    def _apply_theme(self, is_dark: bool):
        orange_primary = "#ffb74d" if is_dark else "#e65100"
        orange_secondary = "#ffa726" if is_dark else "#f57c00"
        dim = "#999" if is_dark else "#888"

        self._orange_label.setStyleSheet(f"""
            font-size: 16px; font-weight: bold; color: {orange_primary}; background: transparent;
        """)
        self._level_label.setStyleSheet(f"""
            font-size: 12px; font-weight: bold; color: {orange_secondary}; background: transparent;
        """)
        self._total_label.setStyleSheet(f"""
            font-size: 11px; color: {dim}; background: transparent;
        """)
        self._combo_label.setStyleSheet(f"""
            font-size: 12px; font-weight: bold; color: {orange_primary}; background: transparent;
        """)
        bar_bg = "#3d2e1a" if is_dark else "#ffe0b2"
        self._level_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none; border-radius: 2px; background-color: {bar_bg};
            }}
            QProgressBar::chunk {{
                background-color: {orange_secondary}; border-radius: 2px;
            }}
        """)

    def update_theme(self, is_dark: bool):
        self._apply_theme(is_dark)


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
        self._orange_manager = None
        
        self.setObjectName("PetStatusInterface")
        self.setWidgetResizable(True)
        
        self._container = QWidget()
        self._container.setObjectName("petStatusContainer")
        self.setWidget(self._container)
        
        self._init_ui()
        self._connect_signals()

    def set_orange_manager(self, orange_manager):
        self._orange_manager = orange_manager
        self._orange_manager.orange_changed.connect(self._on_orange_changed)
        self._orange_manager.level_changed.connect(self._on_level_changed)
        self._refresh_orange_card()
        self._refresh_interaction_buttons()

    def _init_ui(self):
        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)
        
        self.greeting_banner = GreetingBanner(self.quotes_manager, self)
        main_layout.addWidget(self.greeting_banner)
        
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)
        top_layout.setAlignment(Qt.AlignTop)
        
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        
        self.avatar_card = PetAvatarCard(self.quotes_manager, self.attr_manager, self)
        left_layout.addWidget(self.avatar_card)
        
        self._orange_card = OrangeStatusCard()
        left_layout.addWidget(self._orange_card)
        
        self.music_player_card = MusicPlayerCard(self)
        left_layout.addWidget(self.music_player_card)
        
        self._init_attribute_section(left_layout)
        
        self._init_interaction_buttons(left_layout)
        
        left_layout.addStretch()
        
        top_layout.addWidget(left_section, 3)
        
        if self.pomodoro_interface:
            self.pomodoro_interface.setMinimumWidth(260)
            top_layout.addWidget(self.pomodoro_interface, 2)
        
        main_layout.addWidget(top_section)
        
        main_layout.addStretch()

    def _init_attribute_section(self, parent_layout):
        self.attribute_cards = {}
        
        attrs_container = QWidget()
        attrs_layout = QGridLayout(attrs_container)
        attrs_layout.setSpacing(5)
        attrs_layout.setContentsMargins(0, 0, 0, 0)
        
        attrs_order = [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]
        for i, attr_name in enumerate(attrs_order):
            card = AttributeCard(attr_name, self)
            card.setMinimumWidth(130)
            self.attribute_cards[attr_name] = card
            attrs_layout.addWidget(card, i // 2, i % 2)
        
        parent_layout.addWidget(attrs_container)

    def _init_interaction_buttons(self, parent_layout):
        grid = QGridLayout()
        grid.setSpacing(5)
        grid.setContentsMargins(0, 0, 0, 0)
        
        button_configs = [
            ("feed", "🍖", "投喂"),
            ("play", "🎮", "玩耍"),
            ("clean", "🧹", "清洁"),
            ("rest", "😴", "休息"),
        ]
        
        self.buttons = {}
        for i, (action, emoji, text) in enumerate(button_configs):
            btn = PrimaryPushButton(f"{emoji} {text}", self)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda checked, a=action: self._on_interaction(a))
            grid.addWidget(btn, i // 2, i % 2)
            self.buttons[action] = btn
        
        random_btn = PushButton("💬 对话", self)
        random_btn.setFixedHeight(34)
        random_btn.clicked.connect(self._on_start_chat)
        grid.addWidget(random_btn, 2, 0, 1, 2)
        
        parent_layout.addLayout(grid)
        
        self._refresh_interaction_buttons()

    def _refresh_interaction_buttons(self):
        if not self._orange_manager:
            return
        
        for action, btn in self.buttons.items():
            cost = ORANGE_INTERACTION_COST.get(action, 1)
            can_afford = self._orange_manager.can_afford(action)
            btn.setEnabled(can_afford)
            
            emoji_map = {"feed": "🍖", "play": "🎮", "clean": "🧹", "rest": "😴"}
            text_map = {"feed": "投喂", "play": "玩耍", "clean": "清洁", "rest": "休息"}
            emoji = emoji_map.get(action, "")
            text = text_map.get(action, action)
            
            if can_afford:
                btn.setText(f"{emoji} {text} (-{cost}🍊)")
            else:
                btn.setText(f"{emoji} {text} (🍊不足)")

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

    def _on_orange_changed(self, balance: int, today: int):
        self._refresh_orange_card()
        self._refresh_interaction_buttons()
        self._update_pomodoro_doro_display()

    def _on_level_changed(self, level: int, title: str):
        self._refresh_orange_card()

    def _refresh_orange_card(self):
        if self._orange_manager:
            dark = isDarkTheme()
            self._orange_card.update_display(
                balance=self._orange_manager.balance,
                total_earned=self._orange_manager.total_earned,
                level=self._orange_manager.doro_level,
                total_pomodoros=self._orange_manager.total_pomodoros,
                combo=self._orange_manager.current_combo,
                is_dark=dark,
            )

    def _refresh_orange_display(self):
        self._refresh_orange_card()

    def _update_pomodoro_doro_display(self):
        if self.pomodoro_interface and self.attr_manager and self._orange_manager:
            hunger = self.attr_manager.get_attribute(ATTR_HUNGER)
            mood = self.attr_manager.get_attribute(ATTR_MOOD)
            self.pomodoro_interface.set_doro_attribute_display(hunger, mood)

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
        if attr_name in (ATTR_HUNGER, ATTR_MOOD):
            self._update_pomodoro_doro_display()

    def _on_status_changed(self, attr_name: str, new_status: str, old_status: str):
        pass

    def set_attr_manager(self, attr_manager):
        self.attr_manager = attr_manager
        self.avatar_card.set_attr_manager(attr_manager)
        self._connect_signals()
        self._bind_attributes()

    def _on_interaction(self, interaction_type: str):
        if self._orange_manager:
            cost = ORANGE_INTERACTION_COST.get(interaction_type, 1)
            if not self._orange_manager.spend_oranges(cost, interaction_type):
                return

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
        self._orange_card.update_theme(is_dark)
        self._refresh_orange_card()
        
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
