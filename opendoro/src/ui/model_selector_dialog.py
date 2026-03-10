import os
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QFileDialog,
    QLabel, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPainterPath
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, BodyLabel, PushButton, PrimaryPushButton,
    FluentIcon, ProgressRing, CardWidget, IconWidget, isDarkTheme
)
from src.core.live2d_model_manager import Live2DModelManager, Live2DModelInfo
from src.resource_utils import resource_path


class ModelCard(CardWidget):
    model_clicked = pyqtSignal(str)
    model_double_clicked = pyqtSignal(str)
    
    def __init__(self, model_info: Live2DModelInfo, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self._is_selected = False
        self._is_hover = False
        
        self.setFixedSize(160, 200)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("modelCard")
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(140, 140)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border-radius: 8px;
            }
        """)
        
        if self.model_info.icon_path and os.path.exists(self.model_info.icon_path):
            pixmap = QPixmap(self.model_info.icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    130, 130, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.icon_label.setPixmap(scaled_pixmap)
        else:
            self.icon_label.setText("🎭")
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #2a2a2a;
                    border-radius: 8px;
                    font-size: 48px;
                }
            """)
        
        layout.addWidget(self.icon_label)
        
        self.name_label = QLabel(self.model_info.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(self.name_label)
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update()
    
    def is_selected(self) -> bool:
        return self._is_selected
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.model_clicked.emit(self.model_info.model_path)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.model_double_clicked.emit(self.model_info.model_path)
        super().mouseDoubleClickEvent(event)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self._is_selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            pen = painter.pen()
            pen.setColor(QColor(0, 120, 212))
            pen.setWidth(3)
            painter.setPen(pen)
            
            painter.drawRoundedRect(1, 1, self.width() - 3, self.height() - 3, 8, 8)


class ModelSelectorDialog(MessageBoxBase):
    model_selected = pyqtSignal(str)
    
    def __init__(self, current_model_path: str = "", parent=None):
        super().__init__(parent)
        self.current_model_path = current_model_path
        self.selected_model_path = current_model_path
        self.model_manager = Live2DModelManager()
        
        self._init_ui()
        self._load_models()
    
    def _init_ui(self):
        self.titleLabel = SubtitleLabel("选择 Live2D 模型", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 10, 0, 0)
        content_layout.setSpacing(10)
        
        self.info_label = BodyLabel("点击选择模型，双击确认选择")
        content_layout.addWidget(self.info_label)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumSize(520, 350)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        self.cards_widget = QWidget()
        self.cards_layout = QGridLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(10, 10, 10, 10)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.cards_widget)
        content_layout.addWidget(self.scroll_area)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.refresh_btn = PushButton(FluentIcon.SYNC, "刷新模型列表")
        self.refresh_btn.clicked.connect(self._refresh_models)
        btn_layout.addWidget(self.refresh_btn)
        
        self.import_btn = PushButton(FluentIcon.FOLDER, "从本地导入...")
        self.import_btn.clicked.connect(self._import_model)
        btn_layout.addWidget(self.import_btn)
        
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)
        
        self.viewLayout.addWidget(self.content_widget)
        
        self.yesButton.setText("确认选择")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(580)
    
    def _load_models(self):
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        
        models = self.model_manager.get_all_models()
        
        if not models:
            empty_label = BodyLabel("未找到任何 Live2D 模型\n请将模型文件夹放入 models 目录")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #888; padding: 50px;")
            self.cards_layout.addWidget(empty_label, 0, 0)
            return
        
        for index, model in enumerate(models):
            row = index // 3
            col = index % 3
            
            card = ModelCard(model)
            card.model_clicked.connect(self._on_card_clicked)
            card.model_double_clicked.connect(self._on_card_double_clicked)
            
            if model.model_path == self.current_model_path:
                card.set_selected(True)
            
            self.cards_layout.addWidget(card, row, col)
    
    def _on_card_clicked(self, model_path: str):
        self.selected_model_path = model_path
        
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, ModelCard):
                    card.set_selected(card.model_info.model_path == model_path)
    
    def _on_card_double_clicked(self, model_path: str):
        self.selected_model_path = model_path
        self.accept()
    
    def _refresh_models(self):
        self.model_manager.refresh_models()
        self._load_models()
    
    def _import_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Live2D 模型配置文件",
            "",
            "Live2D 模型文件 (*.model3.json);;所有文件 (*.*)"
        )
        
        if file_path:
            is_valid, message = self.model_manager.validate_model(file_path)
            
            if is_valid:
                self.selected_model_path = file_path
                self.accept()
            else:
                from qfluentwidgets import MessageBox
                MessageBox("模型验证失败", message, self).exec_()
    
    def validate(self):
        self.model_selected.emit(self.selected_model_path)
        return True
    
    def get_selected_model_path(self) -> str:
        return self.selected_model_path
