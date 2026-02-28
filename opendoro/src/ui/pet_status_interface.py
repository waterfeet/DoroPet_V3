from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QGridLayout

from qfluentwidgets import CardWidget, PrimaryPushButton, PushButton, setStyleSheet
from qfluentwidgets import FluentIcon as FIF

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_COLORS, RECOVERY_VALUES
)


class PetStatusInterface(QWidget):
    interaction_requested = pyqtSignal(str)

    def __init__(self, attr_manager, parent=None):
        super().__init__(parent)
        self.attr_manager = attr_manager
        
        self.setObjectName("PetStatusInterface")
        self._init_ui()
        self._connect_signals()
        self._update_all_attributes()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        title = QLabel("桌宠状态")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        main_layout.addWidget(title)
        
        self.attribute_cards = {}
        
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            card = self._create_attribute_card(attr_name)
            self.attribute_cards[attr_name] = card
            main_layout.addWidget(card)
        
        main_layout.addStretch()
        
        interaction_layout = QHBoxLayout()
        interaction_layout.setSpacing(15)
        
        self.btn_feed = PrimaryPushButton("投喂", self)
        self.btn_feed.setIcon(FIF.HOME)
        self.btn_feed.clicked.connect(lambda: self._on_interaction("feed"))
        
        self.btn_play = PrimaryPushButton("玩耍", self)
        self.btn_play.setIcon(FIF.PALETTE)
        self.btn_play.clicked.connect(lambda: self._on_interaction("play"))
        
        self.btn_clean = PrimaryPushButton("清洁", self)
        self.btn_clean.setIcon(FIF.SYNC)
        self.btn_clean.clicked.connect(lambda: self._on_interaction("clean"))
        
        self.btn_rest = PrimaryPushButton("休息", self)
        self.btn_rest.setIcon(FIF.BRUSH)
        self.btn_rest.clicked.connect(lambda: self._on_interaction("rest"))
        
        for btn in [self.btn_feed, self.btn_play, self.btn_clean, self.btn_rest]:
            btn.setFixedHeight(40)
            interaction_layout.addWidget(btn)
        
        interaction_widget = QWidget()
        interaction_widget.setLayout(interaction_layout)
        main_layout.addWidget(interaction_widget)

    def _create_attribute_card(self, attr_name: str) -> CardWidget:
        card = CardWidget(self)
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(10)
        
        name_label = QLabel(ATTR_NAMES[attr_name])
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        
        value_label = QLabel()
        value_label.setObjectName(f"value_{attr_name}")
        value_label.setStyleSheet("font-size: 14px; color: #666;")
        
        status_label = QLabel()
        status_label.setObjectName(f"status_{attr_name}")
        status_label.setStyleSheet("font-size: 12px; padding: 2px 8px; border-radius: 4px;")
        
        progress_bar = QProgressBar()
        progress_bar.setObjectName(f"bar_{attr_name}")
        progress_bar.setRange(0, 100)
        progress_bar.setFixedHeight(20)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("%v")
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 10px;
                background-color: #f5f5f5;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 9px;
            }
        """)
        
        card_layout.addWidget(name_label, 0, 0)
        card_layout.addWidget(value_label, 0, 1, Qt.AlignRight)
        card_layout.addWidget(status_label, 0, 2, Qt.AlignRight)
        card_layout.addWidget(progress_bar, 1, 0, 1, 3)
        
        return card

    def _connect_signals(self):
        if self.attr_manager is None:
            return
        self.attr_manager.attribute_changed.connect(self._on_attribute_changed)
        self.attr_manager.status_changed.connect(self._on_status_changed)

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
            value_label.setText(f"{value:.0f} / 100")
        
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
                font-size: 12px; 
                padding: 2px 8px; 
                border-radius: 4px;
                background-color: {bg_color};
                color: {text_color};
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
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    background-color: #f5f5f5;
                    text-align: center;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 9px;
                }}
            """)

    def _update_all_attributes(self):
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            self._update_single_attribute(attr_name)

    def set_attr_manager(self, attr_manager):
        """设置属性管理器（用于后期初始化）"""
        self.attr_manager = attr_manager
        self._connect_signals()
        self._update_all_attributes()

    def _on_interaction(self, interaction_type: str):
        self.attr_manager.perform_interaction(interaction_type)
        self.interaction_requested.emit(interaction_type)
