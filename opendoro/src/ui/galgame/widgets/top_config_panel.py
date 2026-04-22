from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    PushButton, PrimaryPushButton, ComboBox, ToolButton,
    FluentIcon, isDarkTheme
)
from src.core.logger import logger


class TopConfigPanel(QFrame):
    protagonist_clicked = pyqtSignal()
    characters_clicked = pyqtSignal()
    world_clicked = pyqtSignal()
    smart_generate_clicked = pyqtSignal()
    start_clicked = pyqtSignal()
    model_changed = pyqtSignal(str)
    font_settings_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topConfigPanel")
        self._models = []
        self._current_model_id = None
        self.init_ui()
    
    def init_ui(self):
        self.setFixedHeight(60)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 8)
        main_layout.setSpacing(12)
        
        self.protagonist_btn = PushButton(FluentIcon.PEOPLE, "主角配置", self)
        self.protagonist_btn.clicked.connect(self.protagonist_clicked)
        main_layout.addWidget(self.protagonist_btn)
        
        self.characters_btn = PushButton(FluentIcon.SPEAKERS, "角色配置", self)
        self.characters_btn.clicked.connect(self.characters_clicked)
        main_layout.addWidget(self.characters_btn)
        
        self.world_btn = PushButton(FluentIcon.GLOBE, "世界观", self)
        self.world_btn.clicked.connect(self.world_clicked)
        main_layout.addWidget(self.world_btn)
        
        main_layout.addStretch()
        
        self.smart_generate_btn = PushButton(FluentIcon.ROBOT, "✨ 智能生成", self)
        self.smart_generate_btn.clicked.connect(self.smart_generate_clicked)
        main_layout.addWidget(self.smart_generate_btn)
        
        main_layout.addStretch()
        
        self.font_settings_btn = ToolButton(FluentIcon.FONT_SIZE, self)
        self.font_settings_btn.setToolTip("字体设置")
        self.font_settings_btn.clicked.connect(self.font_settings_clicked)
        main_layout.addWidget(self.font_settings_btn)
        
        model_label = QLabel("模型:", self)
        main_layout.addWidget(model_label)
        
        self.model_combo = ComboBox(self)
        self.model_combo.setFixedWidth(150)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        main_layout.addWidget(self.model_combo)
        
        self.start_btn = PrimaryPushButton(FluentIcon.PLAY, "开始游戏", self)
        self.start_btn.clicked.connect(self.start_clicked)
        main_layout.addWidget(self.start_btn)
        
        self.update_theme()
    
    def set_models(self, models: list):
        self._models = models
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        
        default_index = 0
        for i, model in enumerate(models):
            model_id = str(model[0])
            model_name = model[1]
            self.model_combo.addItem(model_name, model_id)
            
            if model[6]:
                default_index = i
                self._current_model_id = model_id
        
        self.model_combo.blockSignals(False)
        self.model_combo.setCurrentIndex(default_index)
    
    def _on_model_changed(self, index):
        if index >= 0:
            model_id = self.model_combo.itemData(index)
            if model_id:
                self._current_model_id = str(model_id)
                self.model_changed.emit(self._current_model_id)
    
    def get_current_model_id(self) -> str:
        # 直接从下拉框的当前选中项获取模型 ID
        current_index = self.model_combo.currentIndex()
        if current_index >= 0:
            model_id = self.model_combo.itemData(current_index)
            if model_id:
                return str(model_id)
        # 如果下拉框没有选中项，返回缓存的值
        return self._current_model_id or ""
    
    def set_current_model(self, model_id: str):
        if not model_id:
            return
        
        for i in range(self.model_combo.count()):
            if str(self.model_combo.itemData(i)) == str(model_id):
                self.model_combo.blockSignals(True)
                self.model_combo.setCurrentIndex(i)
                self.model_combo.blockSignals(False)
                self._current_model_id = str(model_id)
                break
    
    def set_start_enabled(self, enabled: bool):
        self.start_btn.setEnabled(enabled)
        if enabled:
            self.start_btn.setText("开始游戏")
        else:
            self.start_btn.setText("生成中...")
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#f5f5f5"
        border_color = "#404040" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            #topConfigPanel {{
                background-color: {bg_color};
                border-bottom: 1px solid {border_color};
            }}
        """)
