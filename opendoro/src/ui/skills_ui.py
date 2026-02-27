import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QStackedWidget, QLabel, QMessageBox, QFrame, QListWidgetItem,
                             QTextEdit, QLineEdit, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
                            FluentIcon, CardWidget, LineEdit, InfoBar, InfoBarPosition,
                            ComboBox, TextEdit, ProgressRing, SwitchButton, SegmentedWidget)
from PyQt5.QtCore import QSettings

from src.core.skill_manager import SkillManager, SkillType
from src.core.logger import logger


class SkillCard(CardWidget):
    def __init__(self, skill_info, parent=None):
        super().__init__(parent)
        self.skill_info = skill_info
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        name_label = SubtitleLabel(self.skill_info.get("name", "Unknown"), self)
        layout.addWidget(name_label)
        
        desc_text = self.skill_info.get("description", "无描述")
        if len(desc_text) > 100:
            desc_text = desc_text[:100] + "..."
        desc_label = BodyLabel(desc_text, self)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        info_layout = QHBoxLayout()
        
        skill_type = self.skill_info.get("type", "unknown")
        type_label = BodyLabel(f"类型: {skill_type}", self)
        type_label.setStyleSheet("color: #666;")
        info_layout.addWidget(type_label)
        
        version = self.skill_info.get("version", "N/A")
        ver_label = BodyLabel(f"版本: {version}", self)
        ver_label.setStyleSheet("color: #666;")
        info_layout.addWidget(ver_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)


class SkillDetailWidget(QWidget):
    skillRemoved = pyqtSignal(str)
    skillToggled = pyqtSignal(str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_skill = None
        self.skill_manager = SkillManager()
        self.settings = QSettings("DoroPet", "Settings")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        self.empty_label = SubtitleLabel("请从左侧选择一个技能查看详情", self)
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)
        
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)
        
        name_row = QHBoxLayout()
        self.name_label = SubtitleLabel("", self)
        name_row.addWidget(self.name_label)
        
        self.enable_switch = SwitchButton("启用", self)
        self.enable_switch.setOnText("启用")
        self.enable_switch.setOffText("禁用")
        self.enable_switch.checkedChanged.connect(self.on_enable_toggled)
        name_row.addWidget(self.enable_switch)
        name_row.addStretch()
        detail_layout.addLayout(name_row)
        
        self.type_label = BodyLabel("", self)
        self.type_label.setStyleSheet("color: #666;")
        detail_layout.addWidget(self.type_label)
        
        self.desc_label = BodyLabel("", self)
        self.desc_label.setWordWrap(True)
        detail_layout.addWidget(self.desc_label)
        
        content_header = BodyLabel("技能内容:", self)
        detail_layout.addWidget(content_header)
        
        self.content_text = TextEdit(self)
        self.content_text.setReadOnly(True)
        self.content_text.setMaximumHeight(300)
        detail_layout.addWidget(self.content_text)
        
        btn_layout = QHBoxLayout()
        
        self.btn_view = PushButton("查看完整内容", self)
        self.btn_view.setIcon(FluentIcon.VIEW)
        self.btn_view.clicked.connect(self.view_full_content)
        btn_layout.addWidget(self.btn_view)
        
        self.btn_execute = PrimaryPushButton("执行技能", self)
        self.btn_execute.setIcon(FluentIcon.PLAY)
        self.btn_execute.clicked.connect(self.execute_skill)
        btn_layout.addWidget(self.btn_execute)
        
        self.btn_remove = PushButton("删除技能", self)
        self.btn_remove.setIcon(FluentIcon.DELETE)
        self.btn_remove.clicked.connect(self.remove_skill)
        btn_layout.addWidget(self.btn_remove)
        
        btn_layout.addStretch()
        detail_layout.addLayout(btn_layout)
        
        detail_layout.addStretch()
        
        self.detail_widget.hide()
        layout.addWidget(self.detail_widget)
    
    def set_skill(self, skill_info):
        self.current_skill = skill_info
        if not skill_info:
            self.empty_label.show()
            self.detail_widget.hide()
            return
        
        self.empty_label.hide()
        self.detail_widget.show()
        
        skill_name = skill_info.get("name", "Unknown")
        self.name_label.setText(skill_name)
        
        is_enabled = self.settings.value(f"skill_{skill_name}_enabled", True, type=bool)
        self.enable_switch.blockSignals(True)
        self.enable_switch.setChecked(is_enabled)
        self.enable_switch.blockSignals(False)
        
        skill_type = skill_info.get("type", "unknown")
        type_map = {
            "document": "文档型 (提供指导)",
            "executable": "可执行型 (可运行)",
            "hybrid": "混合型"
        }
        self.type_label.setText(f"类型: {type_map.get(skill_type, skill_type)}")
        
        self.desc_label.setText(skill_info.get("description", "无描述"))
        
        content = skill_info.get("content", "")
        if len(content) > 500:
            content = content[:500] + "..."
        self.content_text.setPlainText(content)
        
        is_executable = skill_type in ("executable", "hybrid")
        self.btn_execute.setVisible(is_executable)
    
    def on_enable_toggled(self, checked):
        if not self.current_skill:
            return
        
        skill_name = self.current_skill.get("name")
        self.settings.setValue(f"skill_{skill_name}_enabled", checked)
        self.skillToggled.emit(skill_name, checked)
        
        status = "已启用" if checked else "已禁用"
        InfoBar.success(
            title="状态更新",
            content=f"技能 {skill_name} {status}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def view_full_content(self):
        if not self.current_skill:
            return
        
        skill_name = self.current_skill.get("name")
        content = self.skill_manager.get_skill_content(skill_name)
        
        if content:
            self.content_text.setPlainText(content)
    
    def execute_skill(self):
        if not self.current_skill:
            return
        
        skill_name = self.current_skill.get("name")
        try:
            result = self.skill_manager.execute_skill(skill_name)
            
            InfoBar.success(
                title="执行成功",
                content=f"技能 {skill_name} 执行完成",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="执行失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def remove_skill(self):
        if not self.current_skill:
            return
        
        skill_name = self.current_skill.get("name")
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除技能 '{skill_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.skill_manager.remove_skill(skill_name)
                result_data = json.loads(result)
                
                if result_data.get("status") == "success":
                    InfoBar.success(
                        title="删除成功",
                        content=f"技能 {skill_name} 已删除",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    self.skillRemoved.emit(skill_name)
                else:
                    InfoBar.error(
                        title="删除失败",
                        content=result_data.get("message", "未知错误"),
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
            except Exception as e:
                InfoBar.error(
                    title="删除失败",
                    content=str(e),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )


class InstallSkillWorker(QThread):
    finished = pyqtSignal(str)
    
    def __init__(self, skill_manager, source, skill_name=None):
        super().__init__()
        self.skill_manager = skill_manager
        self.source = source
        self.skill_name = skill_name
    
    def run(self):
        try:
            result = self.skill_manager.install_skill(self.source, self.skill_name)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(json.dumps({"status": "error", "message": str(e)}))


class InstallSkillWidget(CardWidget):
    installCompleted = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.skill_manager = SkillManager()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title = SubtitleLabel("安装新技能", self)
        layout.addWidget(title)
        
        source_layout = QHBoxLayout()
        source_label = BodyLabel("来源:", self)
        self.source_combo = ComboBox(self)
        self.source_combo.addItems(["GitHub", "GitLab", "ZIP URL", "本地路径"])
        self.source_combo.setCurrentIndex(0)
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo)
        source_layout.addStretch()
        layout.addLayout(source_layout)
        
        input_layout = QHBoxLayout()
        self.source_input = LineEdit(self)
        self.source_input.setPlaceholderText("例如: owner/repo 或 https://github.com/owner/repo")
        self.source_input.setClearButtonEnabled(True)
        input_layout.addWidget(self.source_input)
        layout.addLayout(input_layout)
        
        name_layout = QHBoxLayout()
        name_label = BodyLabel("名称 (可选):", self)
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("自定义技能名称，留空则自动检测")
        self.name_input.setClearButtonEnabled(True)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        self.help_label = BodyLabel("", self)
        self.help_label.setStyleSheet("color: #666; font-size: 12px;")
        self.help_label.setWordWrap(True)
        layout.addWidget(self.help_label)
        
        btn_layout = QHBoxLayout()
        self.btn_install = PrimaryPushButton("安装", self)
        self.btn_install.setIcon(FluentIcon.DOWNLOAD)
        self.btn_install.clicked.connect(self.install_skill)
        
        self.progress_ring = ProgressRing(self)
        self.progress_ring.setFixedSize(24, 24)
        self.progress_ring.setStrokeWidth(3)
        self.progress_ring.hide()
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.progress_ring)
        btn_layout.addWidget(self.btn_install)
        layout.addLayout(btn_layout)
        
        self.update_help_text()
    
    def on_source_changed(self, index):
        self.update_help_text()
    
    def update_help_text(self):
        source_type = self.source_combo.currentText()
        help_texts = {
            "GitHub": "格式: owner/repo 或完整URL\n支持指定分支: owner/repo/tree/branch\n支持子目录: owner/repo/tree/branch/path",
            "GitLab": "输入 GitLab 仓库的完整 URL",
            "ZIP URL": "输入技能 ZIP 包的下载链接",
            "本地路径": "输入包含 SKILL.md 或 manifest.json 的本地目录路径"
        }
        placeholder_texts = {
            "GitHub": "owner/repo 或 https://github.com/owner/repo",
            "GitLab": "https://gitlab.com/owner/repo",
            "ZIP URL": "https://example.com/skill.zip",
            "本地路径": "C:\\path\\to\\skill 或 ./skills/my-skill"
        }
        
        self.help_label.setText(help_texts.get(source_type, ""))
        self.source_input.setPlaceholderText(placeholder_texts.get(source_type, ""))
    
    def install_skill(self):
        source = self.source_input.text().strip()
        if not source:
            InfoBar.warning(
                title="输入错误",
                content="请输入来源地址",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        skill_name = self.name_input.text().strip() or None
        
        self.btn_install.setEnabled(False)
        self.progress_ring.show()
        
        self.install_worker = InstallSkillWorker(self.skill_manager, source, skill_name)
        self.install_worker.finished.connect(self._on_install_finished)
        self.install_worker.start()
    
    def _on_install_finished(self, result):
        self.btn_install.setEnabled(True)
        self.progress_ring.hide()
        
        try:
            result_data = json.loads(result)
            
            if result_data.get("status") == "success":
                InfoBar.success(
                    title="安装成功",
                    content=f"技能 {result_data.get('skill_name', 'Unknown')} 已安装",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.source_input.clear()
                self.name_input.clear()
                self.installCompleted.emit()
            else:
                InfoBar.error(
                    title="安装失败",
                    content=result_data.get("message", "未知错误"),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
        except Exception as e:
            logger.error(f"Install skill error: {e}")
            InfoBar.error(
                title="安装失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )


class SkillsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SkillsInterface")
        self.skill_manager = SkillManager()
        self.settings = QSettings("DoroPet", "Settings")
        self.setup_ui()
        self.load_skills()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        self.segmented_widget = SegmentedWidget(self)
        self.segmented_widget.addItem("installed", "已安装技能", lambda: self.stacked_widget.setCurrentIndex(0))
        self.segmented_widget.addItem("install", "安装技能", lambda: self.stacked_widget.setCurrentIndex(1))
        main_layout.addWidget(self.segmented_widget)
        
        self.stacked_widget = QStackedWidget(self)
        
        installed_page = self._create_installed_page()
        self.stacked_widget.addWidget(installed_page)
        
        install_page = self._create_install_page()
        self.stacked_widget.addWidget(install_page)
        
        main_layout.addWidget(self.stacked_widget)
    
    def _create_installed_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        splitter = QSplitter(Qt.Horizontal, page)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        title_layout = QHBoxLayout()
        lbl_title = SubtitleLabel("已安装技能", self)
        title_layout.addWidget(lbl_title)
        
        self.btn_refresh = PushButton(self)
        self.btn_refresh.setIcon(FluentIcon.SYNC)
        self.btn_refresh.setToolTip("刷新列表")
        self.btn_refresh.clicked.connect(self.load_skills)
        title_layout.addWidget(self.btn_refresh)
        left_layout.addLayout(title_layout)
        
        self.skill_list = QListWidget()
        self.skill_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                background-color: transparent;
            }
            QListWidget::item {
                height: 60px;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #009FAA;
                color: white;
                border-radius: 4px;
            }
            QListWidget::item:hover:!selected {
                background-color: #F0F0F0;
                border-radius: 4px;
            }
        """)
        self.skill_list.currentRowChanged.connect(self.on_skill_selected)
        left_layout.addWidget(self.skill_list)
        
        left_widget.setFixedWidth(350)
        
        self.detail_widget = SkillDetailWidget(self)
        self.detail_widget.skillRemoved.connect(self.on_skill_removed)
        self.detail_widget.skillToggled.connect(self.on_skill_toggled)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(self.detail_widget)
        splitter.setSizes([350, 550])
        
        layout.addWidget(splitter)
        return page
    
    def _create_install_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        self.install_widget = InstallSkillWidget(page)
        self.install_widget.installCompleted.connect(self._on_install_completed)
        layout.addWidget(self.install_widget)
        
        layout.addStretch()
        return page
    
    def _on_install_completed(self):
        self.load_skills()
        self.stacked_widget.setCurrentIndex(0)
    
    def load_skills(self):
        self.skill_list.clear()
        
        self.skill_manager.reload_skills()
        
        try:
            skills = self.skill_manager.list_skills()
            
            if not skills:
                item = QListWidgetItem("暂无已安装的技能")
                item.setFlags(Qt.NoItemFlags)
                self.skill_list.addItem(item)
                return
            
            for skill in skills:
                item = QListWidgetItem()
                
                name = skill.get("name", "Unknown")
                desc = skill.get("description", "无描述")
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                skill_type = skill.get("type", "unknown")
                
                is_enabled = self.settings.value(f"skill_{name}_enabled", True, type=bool)
                status_text = "✓" if is_enabled else "✗"
                
                display_text = f"[{status_text}] {name}\n{desc}"
                item.setText(display_text)
                item.setData(Qt.UserRole, skill)
                item.setData(Qt.UserRole + 1, is_enabled)
                
                type_colors = {
                    "document": "#4CAF50",
                    "executable": "#2196F3",
                    "hybrid": "#9C27B0"
                }
                color = type_colors.get(skill_type, "#666")
                if not is_enabled:
                    color = "#999999"
                item.setForeground(QColor(color))
                
                self.skill_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Load skills error: {e}")
            item = QListWidgetItem(f"加载失败: {str(e)}")
            item.setFlags(Qt.NoItemFlags)
            self.skill_list.addItem(item)
    
    def on_skill_selected(self, row):
        if row < 0:
            self.detail_widget.set_skill(None)
            return
        
        item = self.skill_list.item(row)
        if item.flags() & Qt.NoItemFlags:
            return
        
        skill_info = item.data(Qt.UserRole)
        self.detail_widget.set_skill(skill_info)
    
    def on_skill_removed(self, skill_name):
        self.load_skills()
        self.detail_widget.set_skill(None)
    
    def on_skill_toggled(self, skill_name, enabled):
        current_row = self.skill_list.currentRow()
        self.load_skills()
        if current_row >= 0 and current_row < self.skill_list.count():
            self.skill_list.setCurrentRow(current_row)
