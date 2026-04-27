import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                             QStackedWidget, QLabel, QFrame, QListWidgetItem,
                             QTextEdit, QLineEdit, QSplitter, QScrollArea,
                             QMenu, QAction, QGridLayout, QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings, QSize, QPoint, QMimeData
from PyQt5.QtGui import QColor, QDrag, QFont, QPainter, QPen, QBrush, QCursor
from qfluentwidgets import (SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
                            FluentIcon, CardWidget, LineEdit, InfoBar, InfoBarPosition,
                            ComboBox, TextEdit, ProgressRing, SwitchButton, SegmentedWidget,
                            MessageBox, ToolButton, TransparentToolButton, FlowLayout,
                            IconWidget, ScrollArea, SmoothScrollArea, RoundMenu, Action,
                            isDarkTheme)
from PyQt5.QtCore import QTimer

from src.core.skill_manager import SkillManager, SkillType
from src.core.logger import logger




class SkillCardWidget(CardWidget):
    toggled = pyqtSignal(str, bool)
    rightClicked = pyqtSignal(str, QPoint)

    def __init__(self, skill_info, category="未分类", parent=None):
        super().__init__(parent)
        self.skill_info = skill_info
        self._category = category
        self.setup_ui()

    @staticmethod
    def _get_disabled_style():
        if isDarkTheme():
            return (
                "SkillCardWidget { background-color: #2d2d2d; border: 1px solid #404040; "
                "border-radius: 10px; } "
                "SkillCardWidget:hover { background-color: #3a3a3a; border: 1px solid #555; }"
            )
        else:
            return (
                "SkillCardWidget { background-color: #FAFAFA; border: 1px solid #E0E0E0; "
                "border-radius: 10px; } "
                "SkillCardWidget:hover { background-color: #F5F5F5; border: 1px solid #CCC; }"
            )

    @staticmethod
    def _get_enabled_style():
        if isDarkTheme():
            return (
                "SkillCardWidget { border: 1px solid #404040; border-radius: 10px; } "
                "SkillCardWidget:hover { border: 1px solid #666; background-color: #333; }"
            )
        else:
            return (
                "SkillCardWidget { border: 1px solid #E0E0E0; border-radius: 10px; } "
                "SkillCardWidget:hover { border: 1px solid #BDBDBD; background-color: #FAFAFA; }"
            )

    @staticmethod
    def _get_theme_colors():
        if isDarkTheme():
            return {
                "desc": "#aaa",
                "version": "#777",
            }
        else:
            return {
                "desc": "#666",
                "version": "#999",
            }

    def setup_ui(self):
        self.setMinimumWidth(300)
        self.setFixedWidth(300)
        self.setFixedHeight(140)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)

        is_builtin = self.skill_info.get("is_builtin", True)
        is_enabled = self.skill_info.get("is_enabled", True)

        try:
            from src.agent.skills.state import SkillCategory
            icon_text = SkillCategory.get_category_icon(self._category)
        except ImportError:
            icon_text = "📦"
        icon_label = QLabel(icon_text)
        icon_label.setFixedWidth(24)
        icon_label.setStyleSheet("font-size: 16px;")
        header.addWidget(icon_label)

        name = self.skill_info.get("name", "Unknown")
        display_name = name if len(name) <= 18 else name[:16] + "…"
        name_label = SubtitleLabel(display_name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        name_label.setFixedWidth(150)
        name_label.setToolTip(name)
        header.addWidget(name_label)
        header.addStretch()

        self.toggle_switch = SwitchButton()
        self.toggle_switch.setChecked(is_enabled)
        self.toggle_switch.checkedChanged.connect(self._on_toggle)
        header.addWidget(self.toggle_switch)

        layout.addLayout(header)

        desc = self.skill_info.get("description", "无描述")
        if len(desc) > 66:
            desc = desc[:63] + "..."
        theme_colors = self._get_theme_colors()
        desc_label = BodyLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {theme_colors['desc']}; font-size: 12px; line-height: 1.4; max-height: 36px;")
        desc_label.setFixedHeight(36)
        layout.addWidget(desc_label)

        footer = QHBoxLayout()
        footer.setSpacing(6)

        source_text = "[内置]" if is_builtin else "[用户]"
        source_color = "#4CAF50" if is_builtin else "#FF9800"
        source_label = QLabel(source_text)
        source_label.setStyleSheet(f"color: {source_color}; font-size: 10px; font-weight: bold;")
        footer.addWidget(source_label)

        version = self.skill_info.get("version", "")
        if version and version != "0.0.0":
            ver_label = QLabel(f"v{version}")
            ver_label.setStyleSheet(f"color: {theme_colors['version']}; font-size: 10px;")
            footer.addWidget(ver_label)

        footer.addStretch()

        status_text = "● 已启用" if is_enabled else "○ 已禁用"
        status_color = "#4CAF50" if is_enabled else "#F44336"
        self.status_label = QLabel(status_text)
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
        footer.addWidget(self.status_label)

        layout.addLayout(footer)

        if not is_enabled:
            self.setStyleSheet(self._get_disabled_style())
        else:
            self.setStyleSheet(self._get_enabled_style())

    def _on_toggle(self, checked):
        name = self.skill_info.get("name", "")
        self.skill_info["is_enabled"] = checked
        status_text = "● 已启用" if checked else "○ 已禁用"
        status_color = "#4CAF50" if checked else "#F44336"
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")

        if not checked:
            self.setStyleSheet(self._get_disabled_style())
        else:
            self.setStyleSheet(self._get_enabled_style())

        self.toggled.emit(name, checked)

        info = InfoBar.success if checked else InfoBar.warning
        info(
            title="技能状态更新",
            content=f"{'启用' if checked else '禁用'} {name} - 将在所有会话中{'生效' if checked else '禁用'}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            name = self.skill_info.get("name", "")
            self.rightClicked.emit(name, event.globalPos())
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._show_detail()
        super().mouseDoubleClickEvent(event)

    def _show_detail(self):
        name = self.skill_info.get("name", "")
        parent = self.window()
        if parent and hasattr(parent, 'show_skill_detail'):
            parent.show_skill_detail(self.skill_info)


class GroupedSkillScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._container = QWidget()
        self._container.setObjectName("cardContainer")
        self._container.setStyleSheet("#cardContainer { background: transparent; }")
        self.setWidget(self._container)

        self.root_layout = QVBoxLayout(self._container)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setSpacing(16)
        self.root_layout.setAlignment(Qt.AlignTop)

        self._group_flows: dict = {}
        self._group_headers: dict = {}
        self._group_wrappers: dict = {}

    def _clear_all(self):
        for flow in self._group_flows.values():
            for i in range(flow.count() - 1, -1, -1):
                item = flow.itemAt(i)
                w = item.widget() if item and hasattr(item, 'widget') else item
                if w:
                    flow.removeWidget(w)
                    w.setParent(None)
                    w.deleteLater()
        for wrapper in self._group_wrappers.values():
            self.root_layout.removeWidget(wrapper)
            wrapper.setParent(None)
            wrapper.deleteLater()
        for h in self._group_headers.values():
            self.root_layout.removeWidget(h)
            h.setParent(None)
            h.deleteLater()
        self._group_flows.clear()
        self._group_headers.clear()
        self._group_wrappers.clear()

    def clear_cards(self):
        self._clear_all()

    def set_categories(self, categories_order, grouped_cards):
        self._container.setUpdatesEnabled(False)
        self._clear_all()
        try:
            from src.agent.skills.state import SkillCategory
        except ImportError:
            SkillCategory = None

        for cat in categories_order:
            cards = grouped_cards.get(cat, [])
            if not cards:
                continue

            icon = SkillCategory.get_category_icon(cat) if SkillCategory else ""
            count = len(cards)
            header_color = "#aaa" if isDarkTheme() else "#333"
            header = QLabel(f"{icon} {cat} ({count})")
            header.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {header_color}; "
                "padding: 6px 8px; margin-top: 4px;"
            )
            self.root_layout.addWidget(header)
            self._group_headers[cat] = header

            flow = FlowLayout(needAni=False)
            flow.setContentsMargins(0, 0, 0, 0)
            flow.setSpacing(12)
            flow.setVerticalSpacing(12)
            self._group_flows[cat] = flow

            flow_wrapper = QWidget()
            flow_wrapper.setLayout(flow)
            self._group_wrappers[cat] = flow_wrapper
            self.root_layout.addWidget(flow_wrapper)

            for skill in cards:
                card = SkillCardWidget(skill, category=cat)
                flow.addWidget(card)

        self._container.setUpdatesEnabled(True)

    def all_cards(self):
        result = []
        for flow in self._group_flows.values():
            for i in range(flow.count()):
                w = flow.itemAt(i).widget()
                if isinstance(w, SkillCardWidget):
                    result.append(w)
        return result


class SkillDetailPanel(QWidget):
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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header_label = SubtitleLabel("技能详情")
        layout.addWidget(self.header_label)

        self.empty_label = BodyLabel("点击卡片或双击查看技能详情", self)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self._update_empty_label_color()
        layout.addWidget(self.empty_label)

        self.detail_widget = QWidget()
        dl = QVBoxLayout(self.detail_widget)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)

        name_row = QHBoxLayout()
        self.name_label = SubtitleLabel("")
        name_row.addWidget(self.name_label)

        self.enable_switch = SwitchButton("启用")
        self.enable_switch.checkedChanged.connect(self._on_toggle)
        name_row.addWidget(self.enable_switch)
        name_row.addStretch()
        dl.addLayout(name_row)

        self.meta_label = BodyLabel("")
        self.meta_label.setStyleSheet("color: #666; font-size: 12px;")
        self.meta_label.setWordWrap(True)
        dl.addWidget(self.meta_label)

        self.desc_label = BodyLabel("")
        self.desc_label.setWordWrap(True)
        dl.addWidget(self.desc_label)

        dl.addWidget(BodyLabel("完整内容:"))

        self.content_text = TextEdit(self)
        self.content_text.setReadOnly(True)
        self.content_text.setMinimumHeight(200)
        dl.addWidget(self.content_text)

        btn_row = QHBoxLayout()
        self.btn_view = PushButton("加载完整内容")
        self.btn_view.setIcon(FluentIcon.VIEW)
        self.btn_view.clicked.connect(self._load_full_content)
        btn_row.addWidget(self.btn_view)

        self.btn_execute = PrimaryPushButton("执行技能")
        self.btn_execute.setIcon(FluentIcon.PLAY)
        self.btn_execute.clicked.connect(self._execute)
        btn_row.addWidget(self.btn_execute)

        self.btn_remove = PushButton("删除技能")
        self.btn_remove.setIcon(FluentIcon.DELETE)
        self.btn_remove.clicked.connect(self._remove)
        btn_row.addWidget(self.btn_remove)
        btn_row.addStretch()
        dl.addLayout(btn_row)
        dl.addStretch()

        self.detail_widget.hide()
        layout.addWidget(self.detail_widget)
        layout.addStretch()

    def set_skill(self, skill_info):
        self.current_skill = skill_info
        if not skill_info:
            self.empty_label.show()
            self.detail_widget.hide()
            return

        self.empty_label.hide()
        self.detail_widget.show()

        name = skill_info.get("name", "Unknown")
        self.name_label.setText(name)

        is_enabled = skill_info.get("is_enabled", True)
        self.enable_switch.blockSignals(True)
        self.enable_switch.setChecked(is_enabled)
        self.enable_switch.blockSignals(False)

        skill_type = skill_info.get("type", "unknown")
        is_builtin = skill_info.get("is_builtin", True)
        version = skill_info.get("version", "")
        type_map = {"document": "文档型", "executable": "可执行型", "hybrid": "混合型"}
        source_text = "内置" if is_builtin else "用户安装"
        meta_parts = [f"类型: {type_map.get(skill_type, skill_type)}", f"来源: {source_text}"]
        if version and version != "0.0.0":
            meta_parts.append(f"版本: {version}")
        self.meta_label.setText(" | ".join(meta_parts))

        self.desc_label.setText(skill_info.get("description", "无描述"))

        content = skill_info.get("content", "")
        if len(content) > 400:
            content = content[:400] + "...\n\n[点击下方按钮加载完整内容]"
        self.content_text.setPlainText(content or "(无额外内容)")

        is_executable = skill_type in ("executable", "hybrid")
        self.btn_execute.setVisible(is_executable)
        self.btn_remove.setVisible(not is_builtin)
        if is_builtin:
            self.btn_remove.setToolTip("内置技能不可删除")

        if not is_enabled:
            self.btn_view.setToolTip("技能已禁用，无法加载内容")
            self.btn_execute.setToolTip("技能已禁用，无法执行")

    def _on_toggle(self, checked):
        if not self.current_skill:
            return
        name = self.current_skill.get("name")
        self.settings.setValue(f"skill_{name}_enabled", checked)
        self.current_skill["is_enabled"] = checked

        try:
            from src.agent.skills.state import SkillEnabledState
            SkillEnabledState.get_instance().set_enabled(name, checked)
        except ImportError:
            pass

        self.skillToggled.emit(name, checked)

    def _load_full_content(self):
        if not self.current_skill:
            return
        name = self.current_skill.get("name")
        content = self.skill_manager.get_skill_content(name)
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and parsed.get("status") == "error":
                    InfoBar.warning(
                        title="无法加载",
                        content=parsed.get("message", "技能已禁用"),
                        orient=Qt.Horizontal, isClosable=True,
                        position=InfoBarPosition.TOP, duration=3000, parent=self
                    )
                    return
            except (json.JSONDecodeError, TypeError):
                pass
            self.content_text.setPlainText(content)

    def _execute(self):
        if not self.current_skill:
            return
        name = self.current_skill.get("name")
        result = self.skill_manager.execute_skill(name)
        try:
            data = json.loads(result)
            if data.get("status") == "error":
                InfoBar.error(title="执行失败", content=data.get("message", "未知错误"),
                              orient=Qt.Horizontal, isClosable=True,
                              position=InfoBarPosition.TOP, duration=4000, parent=self)
                return
        except Exception:
            pass
        InfoBar.success(title="执行完成", content=f"技能 {name} 执行完成",
                        orient=Qt.Horizontal, isClosable=True,
                        position=InfoBarPosition.TOP, duration=2000, parent=self)

    def _remove(self):
        if not self.current_skill:
            return
        name = self.current_skill.get("name")
        if self.current_skill.get("is_builtin"):
            return

        box = MessageBox("确认删除", f"确定要删除技能 '{name}' 吗？", self)
        box.yesButton.setText("删除")
        box.cancelButton.setText("取消")
        if box.exec_():
            try:
                result = self.skill_manager.remove_skill(name)
                data = json.loads(result)
                if data.get("status") == "success":
                    InfoBar.success(title="删除成功", content=f"技能 {name} 已删除",
                                    orient=Qt.Horizontal, isClosable=True,
                                    position=InfoBarPosition.TOP, duration=3000, parent=self)
                    self.skillRemoved.emit(name)
                else:
                    InfoBar.error(title="删除失败", content=data.get("message", "未知错误"),
                                  orient=Qt.Horizontal, isClosable=True,
                                  position=InfoBarPosition.TOP, duration=3000, parent=self)
            except Exception as e:
                InfoBar.error(title="删除失败", content=str(e),
                              orient=Qt.Horizontal, isClosable=True,
                              position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _update_empty_label_color(self):
        color = "#777" if isDarkTheme() else "#999"
        self.empty_label.setStyleSheet(f"color: {color}; margin-top: 40px;")


class InstallSkillWidget(CardWidget):
    installCompleted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.skill_manager = SkillManager()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(SubtitleLabel("安装新技能"))

        source_row = QHBoxLayout()
        source_row.addWidget(BodyLabel("来源:"))
        self.source_combo = ComboBox()
        self.source_combo.addItems(["GitHub", "GitLab", "ZIP URL", "本地路径"])
        self.source_combo.currentIndexChanged.connect(self._update_help)
        source_row.addWidget(self.source_combo)
        source_row.addStretch()
        layout.addLayout(source_row)

        self.source_input = LineEdit()
        self.source_input.setPlaceholderText("owner/repo 或 https://github.com/owner/repo")
        self.source_input.setClearButtonEnabled(True)
        layout.addWidget(self.source_input)

        name_row = QHBoxLayout()
        name_row.addWidget(BodyLabel("名称 (可选):"))
        self.name_input = LineEdit()
        self.name_input.setPlaceholderText("自定义名称，留空自动检测")
        self.name_input.setClearButtonEnabled(True)
        name_row.addWidget(self.name_input)
        layout.addLayout(name_row)

        self.help_label = BodyLabel("")
        self.help_label.setStyleSheet("color: #666; font-size: 12px;")
        self.help_label.setWordWrap(True)
        layout.addWidget(self.help_label)

        btn_row = QHBoxLayout()
        self.btn_install = PrimaryPushButton("安装")
        self.btn_install.setIcon(FluentIcon.DOWNLOAD)
        self.btn_install.clicked.connect(self._install)

        self.progress_ring = ProgressRing(self)
        self.progress_ring.setFixedSize(24, 24)
        self.progress_ring.setStrokeWidth(3)
        self.progress_ring.hide()

        btn_row.addStretch()
        btn_row.addWidget(self.progress_ring)
        btn_row.addWidget(self.btn_install)
        layout.addLayout(btn_row)

        self._update_help()

    def _update_help(self):
        helps = {
            "GitHub": "格式: owner/repo 或完整URL\n支持分支: owner/repo/tree/branch",
            "GitLab": "输入 GitLab 仓库的完整 URL",
            "ZIP URL": "输入技能 ZIP 包的下载链接",
            "本地路径": "输入包含 SKILL.md 的本地目录路径"
        }
        places = {
            "GitHub": "owner/repo",
            "GitLab": "https://gitlab.com/owner/repo",
            "ZIP URL": "https://example.com/skill.zip",
            "本地路径": "./skills/my-skill"
        }
        t = self.source_combo.currentText()
        self.help_label.setText(helps.get(t, ""))
        self.source_input.setPlaceholderText(places.get(t, ""))

    def _install(self):
        source = self.source_input.text().strip()
        if not source:
            InfoBar.warning(title="输入错误", content="请输入来源地址",
                            orient=Qt.Horizontal, isClosable=True,
                            position=InfoBarPosition.TOP, duration=3000, parent=self)
            return

        self.btn_install.setEnabled(False)
        self.progress_ring.show()

        sn = self.name_input.text().strip() or None
        self.worker = _InstallWorker(self.skill_manager, source, sn)
        self.worker.finished.connect(self._done)
        self.worker.start()

    def _done(self, result):
        self.btn_install.setEnabled(True)
        self.progress_ring.hide()
        try:
            data = json.loads(result)
            if data.get("status") == "success":
                InfoBar.success(title="安装成功", content=f"技能 {data.get('skill_name', '')} 已安装",
                                orient=Qt.Horizontal, isClosable=True,
                                position=InfoBarPosition.TOP, duration=3000, parent=self)
                self.source_input.clear()
                self.name_input.clear()
                self.installCompleted.emit()
            else:
                InfoBar.error(title="安装失败", content=data.get("message", "未知错误"),
                              orient=Qt.Horizontal, isClosable=True,
                              position=InfoBarPosition.TOP, duration=5000, parent=self)
        except Exception as e:
            InfoBar.error(title="安装失败", content=str(e),
                          orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=5000, parent=self)


class _InstallWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, sm, source, name):
        super().__init__()
        self.sm = sm
        self.source = source
        self.name = name

    def run(self):
        try:
            result = self.sm.install_skill(self.source, self.name)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(json.dumps({"status": "error", "message": str(e)}))


class SkillsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SkillsInterface")
        self.skill_manager = SkillManager()
        self.settings = QSettings("DoroPet", "Settings")
        self._all_skills = []
        self._filter_enabled_only = False
        self._filter_category = "全部"
        self._search_text = ""

        try:
            from src.agent.skills.state import SkillEnabledState, SkillCategory
            self._state = SkillEnabledState.get_instance()
            self._state.load_from_settings()
        except ImportError:
            self._state = None

        self.setup_ui()
        self.load_skills()

    def setup_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("搜索技能名称或描述...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self._on_search)
        top_bar.addWidget(self.search_input)

        self.category_filter = ComboBox()
        self._category_items = ["全部"]
        self.category_filter.blockSignals(True)
        self.category_filter.addItem("全部", "全部")
        try:
            from src.agent.skills.state import SkillCategory
            SkillCategory.load_categories()
            for cat in SkillCategory.get_all_categories():
                icon = SkillCategory.get_category_icon(cat)
                self.category_filter.addItem(f"{icon} {cat}", cat)
                self._category_items.append(cat)
        except ImportError:
            pass
        self.category_filter.blockSignals(False)
        self.category_filter.setFixedWidth(130)
        self.category_filter.currentIndexChanged.connect(self._on_filter_changed)
        top_bar.addWidget(self.category_filter)

        self.enabled_only_btn = PushButton("仅启用")
        self.enabled_only_btn.setCheckable(True)
        self.enabled_only_btn.clicked.connect(self._toggle_enabled_filter)
        top_bar.addWidget(self.enabled_only_btn)

        top_bar.addStretch()

        self.btn_refresh = ToolButton(FluentIcon.SYNC)
        self.btn_refresh.setToolTip("刷新列表")
        self.btn_refresh.clicked.connect(self.load_skills)
        top_bar.addWidget(self.btn_refresh)

        self.btn_switch_page = PrimaryPushButton("安装技能")
        self.btn_switch_page.setIcon(FluentIcon.DOWNLOAD)
        self.btn_switch_page.clicked.connect(self._show_install)
        top_bar.addWidget(self.btn_switch_page)

        main.addLayout(top_bar)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stats_label = BodyLabel("")
        self._update_stats_label_color()
        stats_row.addWidget(self.stats_label)

        self.btn_batch_enable = PushButton("全部启用")
        self.btn_batch_enable.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        self.btn_batch_enable.clicked.connect(lambda: self._batch_toggle(True))
        stats_row.addWidget(self.btn_batch_enable)

        self.btn_batch_disable = PushButton("全部禁用")
        self.btn_batch_disable.setStyleSheet("font-size: 11px; padding: 2px 10px;")
        self.btn_batch_disable.clicked.connect(lambda: self._batch_toggle(False))
        stats_row.addWidget(self.btn_batch_disable)

        stats_row.addStretch()
        main.addLayout(stats_row)

        self.stack = QStackedWidget()

        cards_page = QWidget()
        cp = QVBoxLayout(cards_page)
        cp.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = GroupedSkillScrollArea()
        cp.addWidget(self.scroll_area)
        self.stack.addWidget(cards_page)

        install_page = QWidget()
        ip = QVBoxLayout(install_page)
        ip.setContentsMargins(0, 0, 0, 0)
        self.install_widget = InstallSkillWidget()
        self.install_widget.installCompleted.connect(lambda: (
            self.load_skills(),
            self.stack.setCurrentIndex(0),
            self.btn_switch_page.setText("安装技能")
        ))
        ip.addWidget(self.install_widget)
        ip.addStretch()
        self.stack.addWidget(install_page)

        self.detail_panel = SkillDetailPanel()
        self.detail_panel.skillRemoved.connect(self._on_skill_removed)
        self.detail_panel.skillToggled.connect(self._on_skill_toggled)
        self.detail_panel.hide()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.stack)
        splitter.addWidget(self.detail_panel)
        splitter.setSizes([600, 360])

        main.addWidget(splitter)

    def _on_search(self, text):
        self._search_text = text.lower()
        self._render_cards()

    def _on_filter_changed(self, idx):
        if idx < 0 or idx >= len(self._category_items):
            return
        self._filter_category = self._category_items[idx]
        self._render_cards()

    def _toggle_enabled_filter(self, checked):
        self._filter_enabled_only = checked
        self.enabled_only_btn.setText("全部" if checked else "仅启用")
        self._render_cards()

    def _batch_toggle(self, enabled):
        for skill in self._all_skills:
            name = skill.get("name", "")
            skill["is_enabled"] = enabled
            self.settings.setValue(f"skill_{name}_enabled", enabled)
            if self._state:
                self._state.set_enabled(name, enabled)
        self._render_cards()
        InfoBar.success(
            title="批量操作",
            content=f"已{'启用' if enabled else '禁用'}所有技能",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )

    def load_skills(self):
        self.skill_manager.reload_skills()
        try:
            raw = self.skill_manager.list_skills()
            self._all_skills = raw

            if self._state:
                self._state.load_from_settings()
                for s in self._all_skills:
                    s["is_enabled"] = self._state.is_enabled(s.get("name", ""))

            self._render_cards()
        except Exception as e:
            logger.error(f"Load skills error: {e}")

    def _render_cards(self):
        filtered = self._all_skills

        if self._search_text:
            filtered = [s for s in filtered
                        if self._search_text in s.get("name", "").lower()
                        or self._search_text in s.get("description", "").lower()]

        try:
            from src.agent.skills.state import SkillCategory
        except ImportError:
            SkillCategory = None

        if self._filter_category and self._filter_category != "全部" and SkillCategory:
            filtered = [s for s in filtered
                        if SkillCategory.categorize(s.get("name", ""), s.get("description", "")) == self._filter_category]

        if self._filter_enabled_only:
            filtered = [s for s in filtered if s.get("is_enabled", True)]

        enabled_count = sum(1 for s in filtered if s.get("is_enabled", True))
        total_count = len(filtered)
        total_all = len(self._all_skills)
        self.stats_label.setText(f"显示 {total_count} / 共 {total_all} 个技能  |  已启用 {enabled_count} 个")

        if SkillCategory:
            cat_order = SkillCategory.get_all_categories()
        else:
            cat_order = ["未分类"]

        grouped = {}
        for skill in filtered:
            cat = SkillCategory.categorize(skill.get("name", ""), skill.get("description", "")) if SkillCategory else "未分类"
            grouped.setdefault(cat, []).append(skill)

        visible_cats = [c for c in cat_order if c in grouped]
        self.scroll_area.set_categories(visible_cats, grouped)

        for card in self.scroll_area.all_cards():
            card.toggled.connect(self._on_card_toggled)
            card.rightClicked.connect(self._on_card_right_click)

    def _update_single_card(self, name, enabled):
        for card in self.scroll_area.all_cards():
            if card.skill_info.get("name") == name:
                card.skill_info["is_enabled"] = enabled
                card.toggle_switch.blockSignals(True)
                card.toggle_switch.setChecked(enabled)
                card.toggle_switch.blockSignals(False)
                status_text = "● 已启用" if enabled else "○ 已禁用"
                status_color = "#4CAF50" if enabled else "#F44336"
                card.status_label.setText(status_text)
                card.status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
                if enabled:
                    card.setStyleSheet(SkillCardWidget._get_enabled_style())
                else:
                    card.setStyleSheet(SkillCardWidget._get_disabled_style())
                return True
        return False

    def _on_skill_toggled(self, name, enabled):
        for s in self._all_skills:
            if s.get("name") == name:
                s["is_enabled"] = enabled
                break
        self._update_single_card(name, enabled)
        self._update_stats()

    def _on_card_toggled(self, name, enabled):
        self.settings.setValue(f"skill_{name}_enabled", enabled)
        if self._state:
            self._state.set_enabled(name, enabled)
        for s in self._all_skills:
            if s.get("name") == name:
                s["is_enabled"] = enabled
                break
        if self.detail_panel.current_skill and self.detail_panel.current_skill.get("name") == name:
            self.detail_panel.current_skill["is_enabled"] = enabled
            self.detail_panel.enable_switch.blockSignals(True)
            self.detail_panel.enable_switch.setChecked(enabled)
            self.detail_panel.enable_switch.blockSignals(False)
        self._update_stats()

    def _on_card_right_click(self, name, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { padding: 6px; } QMenu::item { padding: 6px 20px; }")

        detail_action = menu.addAction("📋 查看详情")
        detail_action.triggered.connect(lambda: self._show_detail_by_name(name))

        menu.addSeparator()

        cat_menu = menu.addMenu("📁 移动到分类")
        try:
            from src.agent.skills.state import SkillCategory
            current_cat = SkillCategory.categorize(name,
                next((s.get("description","") for s in self._all_skills if s.get("name")==name), ""))
            for cat in SkillCategory.get_all_categories():
                icon = SkillCategory.get_category_icon(cat)
                act = cat_menu.addAction(f"{icon} {cat}")
                act.setCheckable(True)
                act.setChecked(cat == current_cat)
                act.triggered.connect(lambda checked, c=cat: self._move_to_category(name, c))
        except ImportError:
            pass

        toggle_enable = menu.addAction(
            "🔓 启用" if not self._is_enabled(name) else "🔒 禁用"
        )
        toggle_enable.triggered.connect(lambda: self._toggle_skill(name))

        menu.addSeparator()
        info = menu.addAction("ℹ️ 技能信息")
        info.triggered.connect(lambda: self._show_skill_info(name))

        menu.exec_(pos)

    def _is_enabled(self, name):
        for s in self._all_skills:
            if s.get("name") == name:
                return s.get("is_enabled", True)
        return True

    def _toggle_skill(self, name):
        current = self._is_enabled(name)
        self.settings.setValue(f"skill_{name}_enabled", not current)
        if self._state:
            self._state.set_enabled(name, not current)
        for s in self._all_skills:
            if s.get("name") == name:
                s["is_enabled"] = not current
                break
        self._update_single_card(name, not current)
        self._update_stats()

    def _move_to_category(self, name, category):
        try:
            from src.agent.skills.state import SkillCategory
            SkillCategory.set_category(name, category)
            SkillCategory.save_category(name, category)
            self._render_cards()
            InfoBar.success(title="分类已更新", content=f"{name} → {category}",
                            orient=Qt.Horizontal, isClosable=True,
                            position=InfoBarPosition.TOP, duration=2000, parent=self)
        except ImportError:
            pass

    def _show_detail_by_name(self, name):
        for s in self._all_skills:
            if s.get("name") == name:
                self.show_skill_detail(s)
                return

    def show_skill_detail(self, skill_info):
        self.detail_panel.set_skill(skill_info)
        self.detail_panel.show()

    def _show_skill_info(self, name):
        for s in self._all_skills:
            if s.get("name") == name:
                import textwrap
                info_text = textwrap.dedent(f"""
                名称: {s.get('name', '')}
                类型: {s.get('type', '')}
                版本: {s.get('version', 'N/A')}
                来源: {'内置' if s.get('is_builtin', True) else '用户安装'}
                状态: {'已启用' if s.get('is_enabled', True) else '已禁用'}
                路径: {s.get('path', '')}
                """).strip()
                msg = MessageBox("技能信息", info_text, self)
                msg.cancelButton.hide()
                msg.exec_()
                return

    def _on_skill_removed(self, name):
        self.load_skills()

    def _update_stats(self):
        enabled = sum(1 for s in self._all_skills if s.get("is_enabled", True))
        self.stats_label.setText(f"共 {len(self._all_skills)} 个技能  |  已启用 {enabled} 个")

    def _update_stats_label_color(self):
        color = "#aaa" if isDarkTheme() else "#999"
        self.stats_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def update_theme(self):
        self._update_stats_label_color()
        self._render_cards()
        self.detail_panel._update_empty_label_color()

    def _show_install(self):
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)
            self.btn_switch_page.setText("返回列表")
        else:
            self.stack.setCurrentIndex(0)
            self.btn_switch_page.setText("安装技能")
