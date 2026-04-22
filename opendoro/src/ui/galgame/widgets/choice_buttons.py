from typing import List, Dict
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import PushButton, isDarkTheme


class ChoiceButtonsPanel(QFrame):
    choice_clicked = pyqtSignal(int)
    
    def __init__(self, choices: List[Dict], parent=None):
        super().__init__(parent)
        self._choices = choices
        self._selected_id = None
        self._buttons = []
        self.setObjectName("choiceButtonsPanel")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        for choice in self._choices:
            choice_id = choice.get('id', 0)
            choice_text = choice.get('text', '')
            
            btn = PushButton(f"[{choice_id}] {choice_text}", self)
            btn.setObjectName(f"choiceBtn_{choice_id}")
            btn.clicked.connect(lambda checked, cid=choice_id: self._on_click(cid))
            
            self._buttons.append((choice_id, btn))
            layout.addWidget(btn)
        
        self.update_theme()
    
    def _on_click(self, choice_id: int):
        self._selected_id = choice_id
        self.choice_clicked.emit(choice_id)
    
    def set_enabled(self, enabled: bool):
        for _, btn in self._buttons:
            btn.setEnabled(enabled)
    
    def set_selected(self, choice_id: int):
        for cid, btn in self._buttons:
            if cid == choice_id:
                btn.setProperty("selected", True)
                btn.setStyle(btn.style())
            btn.setEnabled(False)
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#f0f0f0"
        border_color = "#404040" if is_dark else "#d0d0d0"
        btn_bg = "#3d3d3d" if is_dark else "#ffffff"
        btn_hover = "#4d4d4d" if is_dark else "#e8e8e8"
        btn_text = "#e0e0e0" if is_dark else "#333333"
        selected_bg = "#2b6cb0" if is_dark else "#3182ce"
        
        self.setStyleSheet(f"""
            #choiceButtonsPanel {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px 16px;
                color: {btn_text};
                font-size: 13px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: #63b3ed;
            }}
            QPushButton:disabled {{
                background-color: {bg_color};
                color: #718096;
            }}
            QPushButton[selected="true"] {{
                background-color: {selected_bg};
                color: white;
                border-color: {selected_bg};
            }}
        """)
