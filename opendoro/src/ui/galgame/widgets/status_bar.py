from typing import List
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import PushButton, isDarkTheme, FluentIcon, ComboBox

from ..models import AffectionState


class GalgameStatusBar(QFrame):
    shop_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    inventory_clicked = pyqtSignal()
    chapter_selected = pyqtSignal(int)
    memory_clicked = pyqtSignal()
    ending_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("galgameStatusBar")
        self._affections = []
        self._currency = 0
        self._current_chapter = 1
        self._chapters = []
        self._inventory_count = 0
        self.init_ui()
    
    def init_ui(self):
        self.setFixedHeight(40)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(16)
        
        self.chapter_combo = ComboBox(self)
        self.chapter_combo.setFixedWidth(150)
        self.chapter_combo.currentIndexChanged.connect(self._on_chapter_changed)
        layout.addWidget(self.chapter_combo)
        
        layout.addWidget(self._create_separator())
        
        self.currency_label = QLabel("💰 100", self)
        self.currency_label.setObjectName("currencyLabel")
        layout.addWidget(self.currency_label)
        
        layout.addWidget(self._create_separator())
        
        self.affection_container = QWidget(self)
        self.affection_layout = QHBoxLayout(self.affection_container)
        self.affection_layout.setContentsMargins(0, 0, 0, 0)
        self.affection_layout.setSpacing(12)
        layout.addWidget(self.affection_container)
        
        layout.addStretch()
        
        self.memory_btn = PushButton(FluentIcon.BOOK_SHELF, "记忆", self)
        self.memory_btn.setFixedHeight(28)
        self.memory_btn.clicked.connect(self.memory_clicked)
        layout.addWidget(self.memory_btn)
        
        self.ending_btn = PushButton(FluentIcon.ALBUM, "结局", self)
        self.ending_btn.setFixedHeight(28)
        self.ending_btn.clicked.connect(self.ending_clicked)
        layout.addWidget(self.ending_btn)
        
        self.inventory_btn = PushButton(FluentIcon.APPLICATION, "背包", self)
        self.inventory_btn.setFixedHeight(28)
        self.inventory_btn.clicked.connect(self.inventory_clicked)
        layout.addWidget(self.inventory_btn)
        
        self.shop_btn = PushButton(FluentIcon.SHOPPING_CART, "商店", self)
        self.shop_btn.setFixedHeight(28)
        self.shop_btn.clicked.connect(self.shop_clicked)
        layout.addWidget(self.shop_btn)
        
        self.save_btn = PushButton(FluentIcon.SAVE, "存档", self)
        self.save_btn.setFixedHeight(28)
        self.save_btn.clicked.connect(self.save_clicked)
        layout.addWidget(self.save_btn)
        
        self.update_theme()
    
    def _on_chapter_changed(self, index: int):
        if 0 <= index < len(self._chapters):
            chapter_num = self._chapters[index]
            self._current_chapter = chapter_num
            self.chapter_selected.emit(chapter_num)
    
    def _create_separator(self) -> QFrame:
        sep = QFrame(self)
        sep.setFrameShape(QFrame.VLine)
        sep.setObjectName("separator")
        return sep
    
    def update_chapters(self, chapters: List[int], current_chapter: int = 1):
        self._chapters = chapters
        self._current_chapter = current_chapter
        
        self.chapter_combo.clear()
        for chapter_num in chapters:
            self.chapter_combo.addItem(f"第{chapter_num}章")
        
        if current_chapter in chapters:
            index = chapters.index(current_chapter)
            self.chapter_combo.setCurrentIndex(index)
    
    def set_current_chapter(self, chapter_num: int):
        if chapter_num in self._chapters:
            index = self._chapters.index(chapter_num)
            self.chapter_combo.blockSignals(True)
            self.chapter_combo.setCurrentIndex(index)
            self.chapter_combo.blockSignals(False)
            self._current_chapter = chapter_num
    
    def update_state(self, chapter_name: str, currency: int, affections: List[AffectionState]):
        self._currency = currency
        self._affections = affections
        
        self.currency_label.setText(f"💰 {currency}")
        
        self._update_affection_display()
    
    def _update_affection_display(self):
        while self.affection_layout.count():
            item = self.affection_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for aff in self._affections[:5]:
            label = QLabel(f"💕 {aff.character_name}: {aff.affection}", self)
            label.setObjectName("affectionLabel")
            
            if aff.affection >= 80:
                label.setStyleSheet("color: #f687b3;")
            elif aff.affection >= 50:
                label.setStyleSheet("color: #63b3ed;")
            else:
                label.setStyleSheet("color: #a0aec0;")
            
            self.affection_layout.addWidget(label)
    
    def set_currency(self, currency: int):
        self._currency = currency
        self.currency_label.setText(f"💰 {currency}")
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#f5f5f5"
        border_color = "#404040" if is_dark else "#e0e0e0"
        text_color = "#cccccc" if is_dark else "#333333"
        sep_color = "#404040" if is_dark else "#d0d0d0"
        
        self.setStyleSheet(f"""
            #galgameStatusBar {{
                background-color: {bg_color};
                border-top: 1px solid {border_color};
            }}
            #currencyLabel {{
                color: #f6e05e;
                font-size: 12px;
            }}
            #separator {{
                color: {sep_color};
            }}
            #affectionLabel {{
                font-size: 11px;
            }}
        """)
