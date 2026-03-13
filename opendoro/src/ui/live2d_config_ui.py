import os
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem, QFrame, QLabel, QGridLayout, QFileDialog
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
from qfluentwidgets import (ScrollArea, PlainTextEdit, PrimaryPushButton, PushButton,
                            TitleLabel, BodyLabel, FluentIcon, LineEdit, ListWidget, MessageBox,
                            StrongBodyLabel, isDarkTheme, CheckBox, ProgressRing, CardWidget,
                            SubtitleLabel, ComboBox)
from src.core.database import ChatDatabase
from src.core.live2d_model_manager import Live2DModelManager, Live2DModelInfo
from src.ui.model_selector_dialog import ModelSelectorDialog
from src.resource_utils import resource_path
from src.core.logger import logger


class ModelPreviewCard(CardWidget):
    def __init__(self, model_info: Live2DModelInfo = None, parent=None):
        super().__init__(parent)
        self.model_info = model_info
        self.setFixedSize(280, 160)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(100, 100)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.icon_label)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        self.name_label = BodyLabel("未选择模型")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 15px;")
        info_layout.addWidget(self.name_label)
        
        self.path_label = BodyLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #888; font-size: 11px;")
        info_layout.addWidget(self.path_label)
        
        self.desc_label = BodyLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(self.desc_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        self._update_display()
    
    def set_model(self, model_info: Live2DModelInfo):
        self.model_info = model_info
        self._update_display()
    
    def _update_display(self):
        if not self.model_info:
            self.name_label.setText("未选择模型")
            self.path_label.setText("点击下方按钮选择模型")
            self.desc_label.setText("")
            self.icon_label.setText("🎭")
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: #2a2a2a;
                    border-radius: 10px;
                    font-size: 40px;
                }
            """)
            return
        
        self.name_label.setText(self.model_info.name)
        
        display_path = self.model_info.model_path
        if len(display_path) > 50:
            display_path = "..." + display_path[-47:]
        self.path_label.setText(display_path)
        
        if self.model_info.description:
            desc = self.model_info.description
            if len(desc) > 60:
                desc = desc[:57] + "..."
            self.desc_label.setText(desc)
        else:
            self.desc_label.setText("")
        
        if self.model_info.icon_path and os.path.exists(self.model_info.icon_path):
            pixmap = QPixmap(self.model_info.icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    90, 90, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.icon_label.setPixmap(scaled_pixmap)
                self.icon_label.setStyleSheet("""
                    QLabel {
                        background-color: #2a2a2a;
                        border-radius: 10px;
                    }
                """)
                return
        
        self.icon_label.setText("🎭")
        self.icon_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border-radius: 10px;
                font-size: 40px;
            }
        """)


class Live2DConfigInterface(QWidget):
    def __init__(self, db=None, parent=None, live2d_widget=None):
        super().__init__(parent)
        self.db = db if db else ChatDatabase()
        self.live2d_widget = live2d_widget
        self.current_model_path = ""
        self.model_manager = Live2DModelManager()
        
        self.setObjectName("Live2DConfigInterface")
        self.init_ui()
        self.load_current_model()

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        if widget and hasattr(widget, 'path'):
            self.current_model_path = widget.path
            model_info = self.model_manager.get_model_by_path(self.current_model_path)
            self.model_preview_card.set_model(model_info)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("live2dConfigLeftPanel")
        self.left_panel.setFixedWidth(280)
        
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(16, 20, 16, 20)
        left_layout.setSpacing(12)

        left_title = StrongBodyLabel("模型列表", self.left_panel)
        left_layout.addWidget(left_title)

        self.model_list = ListWidget(self.left_panel)
        self.model_list.setObjectName("live2dModelList")
        self.model_list.itemClicked.connect(self.on_model_selected)
        self.model_list.itemDoubleClicked.connect(self.on_model_double_clicked)
        left_layout.addWidget(self.model_list)

        refresh_btn = PushButton(FluentIcon.SYNC, "刷新模型列表", self.left_panel)
        refresh_btn.clicked.connect(self.load_model_list)
        left_layout.addWidget(refresh_btn)

        import_btn = PushButton(FluentIcon.FOLDER, "从本地导入...", self.left_panel)
        import_btn.clicked.connect(self._on_import_model)
        left_layout.addWidget(import_btn)

        main_layout.addWidget(self.left_panel)

        right_panel = ScrollArea(self)
        right_panel.setWidgetResizable(True)
        
        self.edit_widget = QWidget()
        self.edit_widget.setObjectName("live2dConfigEditWidget")
        
        right_layout = QVBoxLayout(self.edit_widget)
        right_layout.setContentsMargins(36, 36, 36, 36)
        right_layout.setSpacing(20)

        title_label = TitleLabel("Live2D 模型配置", self.edit_widget)
        title_label.setMaximumHeight(48)
        right_layout.addWidget(title_label)

        current_section = QWidget()
        current_section.setObjectName("currentModelSection")
        current_layout = QVBoxLayout(current_section)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.setSpacing(12)

        current_title = SubtitleLabel("当前模型", current_section)
        current_title.setStyleSheet("font-weight: bold; font-size: 15px; color: #0078d4;")
        current_layout.addWidget(current_title)

        self._add_separator(current_layout)

        self.model_preview_card = ModelPreviewCard()
        current_layout.addWidget(self.model_preview_card)
        
        model_btn_layout = QHBoxLayout()
        model_btn_layout.setSpacing(10)
        
        self.select_model_btn = PrimaryPushButton(FluentIcon.PHOTO, "选择模型", current_section)
        self.select_model_btn.clicked.connect(self._on_select_model)
        model_btn_layout.addWidget(self.select_model_btn)
        
        self.reload_model_btn = PushButton(FluentIcon.SYNC, "重新加载", current_section)
        self.reload_model_btn.clicked.connect(self._on_reload_model)
        model_btn_layout.addWidget(self.reload_model_btn)
        
        self.clear_model_btn = PushButton(FluentIcon.DELETE, "清除模型", current_section)
        self.clear_model_btn.clicked.connect(self._on_clear_model)
        model_btn_layout.addWidget(self.clear_model_btn)
        
        model_btn_layout.addStretch()
        current_layout.addLayout(model_btn_layout)
        
        right_layout.addWidget(current_section)

        info_section = QWidget()
        info_section.setObjectName("live2dInfoSection")
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(0, 20, 0, 0)
        info_layout.setSpacing(12)

        info_title = SubtitleLabel("模型信息", info_section)
        info_title.setStyleSheet("font-weight: bold; font-size: 15px; color: #0078d4;")
        info_layout.addWidget(info_title)

        self._add_separator(info_layout)

        self.info_name_label = BodyLabel("模型名称: -", info_section)
        info_layout.addWidget(self.info_name_label)

        self.info_path_label = BodyLabel("模型路径: -", info_section)
        self.info_path_label.setWordWrap(True)
        info_layout.addWidget(self.info_path_label)

        self.info_expressions_label = BodyLabel("表情数量: -", info_section)
        info_layout.addWidget(self.info_expressions_label)

        self.info_motions_label = BodyLabel("动作数量: -", info_section)
        info_layout.addWidget(self.info_motions_label)

        info_layout.addStretch()
        
        right_layout.addWidget(info_section)
        right_layout.addStretch()

        right_panel.setWidget(self.edit_widget)
        main_layout.addWidget(right_panel)

        self.load_model_list()

    def _add_separator(self, layout):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgba(0, 0, 0, 0.08);")
        layout.addWidget(separator)

    def load_model_list(self):
        self.model_list.clear()
        models = self.model_manager.get_all_models()
        for model in models:
            item = QListWidgetItem(model.name)
            item.setData(Qt.UserRole, model.model_path)
            item.setData(Qt.UserRole + 1, model.description or "")
            if model.icon_path and os.path.exists(model.icon_path):
                pixmap = QPixmap(model.icon_path)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self.model_list.addItem(item)

    def load_current_model(self):
        if self.live2d_widget and hasattr(self.live2d_widget, 'path'):
            self.current_model_path = self.live2d_widget.path
            model_info = self.model_manager.get_model_by_path(self.current_model_path)
            self.model_preview_card.set_model(model_info)
            self._update_model_info()

    def on_model_selected(self, item):
        model_path = item.data(Qt.UserRole)
        model_info = self.model_manager.get_model_by_path(model_path)
        if model_info:
            self.model_preview_card.set_model(model_info)
            self.current_model_path = model_path

    def on_model_double_clicked(self, item):
        model_path = item.data(Qt.UserRole)
        self._apply_model(model_path)

    def _on_select_model(self):
        dialog = ModelSelectorDialog(self.current_model_path, self)
        if dialog.exec_():
            selected_path = dialog.get_selected_model_path()
            if selected_path:
                self._apply_model(selected_path)

    def _apply_model(self, model_path):
        self.current_model_path = model_path
        model_info = self.model_manager.get_model_by_path(model_path)
        self.model_preview_card.set_model(model_info)
        
        if self.live2d_widget:
            success = self.live2d_widget.reload_model(model_path)
            if success:
                self._update_model_info()
                logger.info(f"Live2D model applied: {model_path}")
            else:
                MessageBox("失败", "模型加载失败，请检查模型文件", self).exec_()

    def _on_reload_model(self):
        if not self.current_model_path:
            MessageBox("提示", "请先选择一个 Live2D 模型", self).exec_()
            return
        
        if self.live2d_widget:
            success = self.live2d_widget.reload_model(self.current_model_path)
            if success:
                self._update_model_info()
                MessageBox("成功", "模型已重新加载", self).exec_()
            else:
                MessageBox("失败", "模型重新加载失败，请检查模型文件", self).exec_()
        else:
            MessageBox("提示", "Live2D 组件未初始化", self).exec_()

    def _on_clear_model(self):
        default_model_path = resource_path("models/Doro/Doro.model3.json")
        if os.path.exists(default_model_path):
            self._apply_model(default_model_path)
        else:
            self.current_model_path = ""
            self.model_preview_card.set_model(None)
            self._clear_model_info()

    def _on_import_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 Live2D 模型文件", "", "Model3 Files (*.model3.json)"
        )
        if file_path:
            self._apply_model(file_path)
            self.load_model_list()

    def _update_model_info(self):
        if not self.live2d_widget:
            return
        
        model_info = self.model_manager.get_model_by_path(self.current_model_path)
        if model_info:
            self.info_name_label.setText(f"模型名称: {model_info.name}")
            self.info_path_label.setText(f"模型路径: {model_info.model_path}")
        
        if hasattr(self.live2d_widget, 'expression_ids'):
            expr_count = len(self.live2d_widget.expression_ids) if self.live2d_widget.expression_ids else 0
            self.info_expressions_label.setText(f"表情数量: {expr_count}")
        
        if hasattr(self.live2d_widget, 'motion_groups'):
            motion_groups = self.live2d_widget.motion_groups
            if motion_groups:
                motion_count = 0
                for v in motion_groups.values():
                    if isinstance(v, int):
                        motion_count += v
                    elif isinstance(v, (list, tuple)):
                        motion_count += len(v)
                self.info_motions_label.setText(f"动作数量: {motion_count}")
            else:
                self.info_motions_label.setText("动作数量: 0")

    def _clear_model_info(self):
        self.info_name_label.setText("模型名称: -")
        self.info_path_label.setText("模型路径: -")
        self.info_expressions_label.setText("表情数量: -")
        self.info_motions_label.setText("动作数量: -")

    def update_theme(self):
        pass
