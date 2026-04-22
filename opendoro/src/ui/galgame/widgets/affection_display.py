from typing import List
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar
from PyQt5.QtCore import Qt
from qfluentwidgets import isDarkTheme

from ..models import AffectionState, RELATIONSHIP_LEVELS


class AffectionDisplay(QFrame):
    def __init__(self, affections: List[AffectionState] = None, parent=None):
        super().__init__(parent)
        self._affections = affections or []
        self.setObjectName("affectionDisplay")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        title = QLabel("角色好感度", self)
        title.setObjectName("title")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        layout.addWidget(self.cards_container)
        
        self._update_cards()
        self.update_theme()
    
    def set_affections(self, affections: List[AffectionState]):
        self._affections = affections
        self._update_cards()
    
    def _update_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for aff in self._affections:
            card = self._create_affection_card(aff)
            self.cards_layout.addWidget(card)
    
    def _create_affection_card(self, aff: AffectionState) -> QFrame:
        card = QFrame()
        card.setObjectName("affectionCard")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        header = QHBoxLayout()
        
        name_label = QLabel(aff.character_name, card)
        name_label.setObjectName("characterName")
        header.addWidget(name_label)
        
        header.addStretch()
        
        relation_label = QLabel(aff.relationship, card)
        relation_label.setObjectName("relationLabel")
        header.addWidget(relation_label)
        
        layout.addLayout(header)
        
        progress = QProgressBar(card)
        progress.setRange(0, 100)
        progress.setValue(aff.affection)
        progress.setTextVisible(True)
        progress.setFormat(f"{aff.affection}%")
        progress.setObjectName("affectionProgress")
        progress.setFixedHeight(8)
        layout.addWidget(progress)
        
        return card
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        card_bg = "#3d3d3d" if is_dark else "#f8f8f8"
        border_color = "#404040" if is_dark else "#e0e0e0"
        text_color = "#e0e0e0" if is_dark else "#333333"
        name_color = "#63b3ed" if is_dark else "#3182ce"
        
        self.setStyleSheet(f"""
            #affectionDisplay {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            #title {{
                color: {text_color};
                font-size: 14px;
            }}
            #affectionCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            #characterName {{
                color: {name_color};
                font-size: 12px;
                font-weight: bold;
            }}
            #relationLabel {{
                color: #a0aec0;
                font-size: 11px;
            }}
            #affectionProgress {{
                border: none;
                border-radius: 4px;
                background-color: {"#4a5568" if is_dark else "#e2e8f0"};
            }}
            #affectionProgress::chunk {{
                background-color: #f687b3;
                border-radius: 4px;
            }}
            #affectionProgress::text {{
                color: transparent;
            }}
        """)
