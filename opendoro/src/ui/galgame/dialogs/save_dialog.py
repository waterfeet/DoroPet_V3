from typing import List, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QListWidget, QListWidgetItem, QFileDialog
)
from PyQt5.QtCore import Qt, QDateTime
from qfluentwidgets import (
    LineEdit, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme, MessageBox,
    InfoBar, InfoBarPosition
)

from ..models import GameState
from ..database import GalgameDatabase
from ..html_exporter import HTMLExporter


class SaveDialog(QDialog):
    def __init__(self, db: GalgameDatabase, current_state: Optional[GameState] = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._current_state = current_state
        self._selected_save_id = None
        self.setWindowTitle("存档管理")
        self.setMinimumSize(500, 450)
        self.init_ui()
        self._load_saves()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = TitleLabel("存档管理", self)
        layout.addWidget(title)
        
        save_layout = QHBoxLayout()
        save_layout.addWidget(BodyLabel("新存档名称:", self))
        
        self.save_name_input = LineEdit(self)
        self.save_name_input.setPlaceholderText("输入存档名称...")
        save_layout.addWidget(self.save_name_input)
        
        new_save_btn = PrimaryPushButton(FluentIcon.SAVE, "新建存档", self)
        new_save_btn.clicked.connect(self._create_save)
        save_layout.addWidget(new_save_btn)
        
        layout.addLayout(save_layout)
        
        layout.addWidget(BodyLabel("已有存档:", self))
        
        self.save_list = QListWidget(self)
        self.save_list.itemDoubleClicked.connect(self._load_save)
        layout.addWidget(self.save_list)
        
        btn_layout = QHBoxLayout()
        
        load_btn = PushButton(FluentIcon.DOWNLOAD, "读取存档", self)
        load_btn.clicked.connect(self._load_selected_save)
        btn_layout.addWidget(load_btn)
        
        delete_btn = PushButton(FluentIcon.DELETE, "删除存档", self)
        delete_btn.clicked.connect(self._delete_save)
        btn_layout.addWidget(delete_btn)
        
        export_btn = PushButton(FluentIcon.DOCUMENT, "导出HTML", self)
        export_btn.clicked.connect(self._export_html)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = PushButton("取消", self)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.update_theme()
    
    def _load_saves(self):
        self.save_list.clear()
        saves = self._db.get_saves()
        
        for save in saves:
            item_text = f"{save['name']} - {save['updated_at']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, save['id'])
            self.save_list.addItem(item)
    
    def _create_save(self):
        name = self.save_name_input.text().strip()
        if not name:
            name = f"存档 {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}"
        
        save_id = self._db.create_save(name)
        self._selected_save_id = save_id
        
        if self._current_state:
            self._current_state.save_id = save_id
            self._db.save_state(self._current_state)
            self.accept()
        else:
            InfoBar.warning(
                title="警告",
                content="当前没有游戏状态，无法保存",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _load_selected_save(self):
        current_item = self.save_list.currentItem()
        if not current_item:
            return
        
        self._selected_save_id = current_item.data(Qt.UserRole)
        self.accept()
    
    def _load_save(self, item: QListWidgetItem):
        self._selected_save_id = item.data(Qt.UserRole)
        self.accept()
    
    def _delete_save(self):
        current_item = self.save_list.currentItem()
        if not current_item:
            return
        
        save_id = current_item.data(Qt.UserRole)
        
        msg = MessageBox("确认删除", "确定要删除这个存档吗？此操作无法撤销。", self)
        if msg.exec_():
            self._db.delete_save(save_id)
            self._load_saves()
    
    def _export_html(self):
        state_to_export = None
        story_title = "未命名故事"
        
        current_item = self.save_list.currentItem()
        if current_item:
            save_id = current_item.data(Qt.UserRole)
            state_to_export = self._db.load_state(save_id)
            save_name = current_item.text().split(' - ')[0]
            story_title = save_name
        elif self._current_state:
            state_to_export = self._current_state
            story_title = "当前游戏"
        
        if not state_to_export:
            InfoBar.warning(
                title="警告",
                content="请选择一个存档或先开始游戏",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        if not state_to_export.messages:
            InfoBar.warning(
                title="警告",
                content="该存档没有故事内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出HTML",
            f"{story_title}.html",
            "HTML文件 (*.html)"
        )
        
        if file_path:
            if HTMLExporter.export_to_html(state_to_export, file_path, story_title):
                InfoBar.success(
                    title="成功",
                    content=f"已导出到: {file_path}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                InfoBar.error(
                    title="错误",
                    content="导出失败，请重试",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
    
    def get_selected_save_id(self) -> Optional[int]:
        return self._selected_save_id
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#ffffff"
        text_color = "#e0e0e0" if is_dark else "#333333"
        border_color = "#404040" if is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel {{
                color: {text_color};
            }}
            QListWidget {{
                background-color: {"#3d3d3d" if is_dark else "#f5f5f5"};
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
            }}
            QListWidget::item:selected {{
                background-color: #3182ce;
            }}
        """)
