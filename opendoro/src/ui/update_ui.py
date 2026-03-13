import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QStackedWidget, QTextEdit, QProgressBar, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush
from qfluentwidgets import (
    ScrollArea, TitleLabel, StrongBodyLabel, BodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, ProgressRing, CardWidget,
    FluentIcon as FIF, InfoBar, InfoBarPosition, SwitchButton,
    SubtitleLabel, isDarkTheme, MessageBox
)
from src.core.version_manager import (
    VersionManager, VersionInfo, ReleaseType, get_version_type_display,
    compare_versions, __version__
)
from src.core.logger import logger

class VersionListItem(QWidget):
    def __init__(self, version_info: VersionInfo, is_current: bool, parent=None):
        super().__init__(parent)
        self.version_info = version_info
        self.is_current = is_current
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        version_row = QHBoxLayout()
        version_label = StrongBodyLabel(f"v{self.version_info.version}", self)
        version_row.addWidget(version_label)
        
        type_label = CaptionLabel(get_version_type_display(self.version_info.release_type), self)
        type_label.setObjectName("versionTypeLabel")
        type_label.setProperty("releaseType", self.version_info.release_type.value)
        type_label.setAttribute(Qt.WA_StyledBackground, True)
        version_row.addWidget(type_label)
        
        if self.is_current:
            current_label = CaptionLabel("当前版本", self)
            current_label.setObjectName("currentVersionLabel")
            current_label.setAttribute(Qt.WA_StyledBackground, True)
            version_row.addWidget(current_label)
        
        version_row.addStretch()
        info_layout.addLayout(version_row)
        
        date_label = CaptionLabel(f"发布日期: {self.version_info.release_date}", self)
        date_label.setObjectName("versionDateLabel")
        info_layout.addWidget(date_label)
        
        layout.addLayout(info_layout, 1)
        
        if self.version_info.file_size > 0:
            size_label = CaptionLabel(self.version_info.display_size, self)
            size_label.setObjectName("versionSizeLabel")
            layout.addWidget(size_label)

class UpdateWidget(CardWidget):
    update_available = pyqtSignal(VersionInfo)
    download_completed = pyqtSignal(str)
    
    def __init__(self, parent=None, version_manager=None):
        super().__init__(parent)
        self.version_manager = version_manager if version_manager else VersionManager(self)
        self.selected_version: VersionInfo = None
        self._is_loading = False
        self._external_version_manager = version_manager is not None
        self.setup_ui()
        self.connect_signals()
        if not self._external_version_manager:
            self.load_versions()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = TitleLabel("软件更新", self)
        title_layout.addWidget(title)
        
        current_version_text = f"当前版本: v{self.version_manager.current_version}"
        self.current_version_label = BodyLabel(current_version_text, self)
        self.current_version_label.setObjectName("currentVersionTextLabel")
        title_layout.addWidget(self.current_version_label)
        
        header_layout.addLayout(title_layout, 1)
        
        self.refresh_btn = PushButton(FIF.SYNC, "检查更新", self)
        self.refresh_btn.clicked.connect(self.check_for_updates)
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        self.status_card = QWidget(self)
        self.status_card.setObjectName("updateStatusCard")
        status_layout = QHBoxLayout(self.status_card)
        status_layout.setContentsMargins(12, 12, 12, 12)
        
        self.status_icon = ProgressRing(self)
        self.status_icon.setFixedSize(24, 24)
        self.status_icon.setStrokeWidth(3)
        self.status_icon.hide()
        status_layout.addWidget(self.status_icon)
        
        self.status_label = BodyLabel("", self)
        status_layout.addWidget(self.status_label, 1)
        
        self.update_btn = PrimaryPushButton(FIF.DOWNLOAD, "立即更新", self)
        self.update_btn.hide()
        self.update_btn.clicked.connect(self.on_update_clicked)
        status_layout.addWidget(self.update_btn)
        
        self.status_card.hide()
        main_layout.addWidget(self.status_card)
        
        self.download_widget = QWidget(self)
        self.download_widget.setObjectName("downloadProgressWidget")
        download_layout = QVBoxLayout(self.download_widget)
        download_layout.setContentsMargins(12, 12, 12, 12)
        download_layout.setSpacing(8)
        
        download_header = QHBoxLayout()
        self.download_label = BodyLabel("正在下载...", self)
        download_header.addWidget(self.download_label, 1)
        
        self.download_speed = CaptionLabel("", self)
        download_header.addWidget(self.download_speed)
        
        self.download_percent = CaptionLabel("0%", self)
        download_header.addWidget(self.download_percent)
        download_layout.addLayout(download_header)
        
        self.download_progress = QProgressBar(self)
        self.download_progress.setObjectName("downloadProgressBar")
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.setTextVisible(False)
        self.download_progress.setFixedHeight(6)
        download_layout.addWidget(self.download_progress)
        
        download_btn_layout = QHBoxLayout()
        download_btn_layout.addStretch()
        self.cancel_download_btn = PushButton("取消下载", self)
        self.cancel_download_btn.clicked.connect(self.cancel_download)
        download_btn_layout.addWidget(self.cancel_download_btn)
        download_layout.addLayout(download_btn_layout)
        
        self.download_widget.hide()
        main_layout.addWidget(self.download_widget)
        
        self.install_widget = QWidget(self)
        self.install_widget.setObjectName("installProgressWidget")
        install_layout = QVBoxLayout(self.install_widget)
        install_layout.setContentsMargins(12, 12, 12, 12)
        install_layout.setSpacing(8)
        
        install_header = QHBoxLayout()
        self.install_label = BodyLabel("正在安装更新...", self)
        install_header.addWidget(self.install_label, 1)
        
        self.install_percent = CaptionLabel("", self)
        install_header.addWidget(self.install_percent)
        install_layout.addLayout(install_header)
        
        self.install_progress = QProgressBar(self)
        self.install_progress.setObjectName("installProgressBar")
        self.install_progress.setRange(0, 100)
        self.install_progress.setValue(0)
        self.install_progress.setTextVisible(False)
        self.install_progress.setFixedHeight(6)
        install_layout.addWidget(self.install_progress)
        
        self.install_step_label = CaptionLabel("", self)
        install_layout.addWidget(self.install_step_label)
        
        install_info = CaptionLabel("安装完成后将自动重启程序", self)
        install_info.setObjectName("installInfoLabel")
        install_layout.addWidget(install_info)
        
        self.install_widget.hide()
        main_layout.addWidget(self.install_widget)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        list_header = QHBoxLayout()
        list_title = StrongBodyLabel("历史版本", self)
        list_header.addWidget(list_title, 1)
        
        self.show_beta_switch = SwitchButton("包含测试版", self)
        self.show_beta_switch.setChecked(False)
        self.show_beta_switch.checkedChanged.connect(self.on_show_beta_changed)
        list_header.addWidget(self.show_beta_switch)
        
        left_layout.addLayout(list_header)
        
        self.version_list = QListWidget(self)
        self.version_list.setObjectName("versionListWidget")
        self.version_list.setFixedHeight(250)
        self.version_list.currentItemChanged.connect(self.on_version_selected)
        left_layout.addWidget(self.version_list)
        
        content_layout.addWidget(left_widget, 2)
        
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        changelog_title = StrongBodyLabel("更新日志", self)
        right_layout.addWidget(changelog_title)
        
        self.changelog_text = QTextEdit(self)
        self.changelog_text.setObjectName("changelogTextEdit")
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setFixedHeight(250)
        self.changelog_text.setPlaceholderText("选择一个版本查看更新日志")
        right_layout.addWidget(self.changelog_text)
        
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.download_version_btn = PrimaryPushButton(FIF.DOWNLOAD, "下载此版本", self)
        self.download_version_btn.setEnabled(False)
        self.download_version_btn.clicked.connect(self.on_download_version_clicked)
        action_layout.addWidget(self.download_version_btn)
        
        right_layout.addLayout(action_layout)
        content_layout.addWidget(right_widget, 3)
        
        main_layout.addLayout(content_layout)
    
    def connect_signals(self):
        self.version_manager.versions_loaded.connect(self.on_versions_loaded)
        self.version_manager.load_error.connect(self.on_load_error)
        self.version_manager.download_progress.connect(self.on_download_progress)
        self.version_manager.download_completed.connect(self.on_download_completed)
        self.version_manager.download_error.connect(self.on_download_error)
        self.version_manager.install_progress.connect(self.on_install_progress)
        self.version_manager.install_completed.connect(self.on_install_completed)
        self.version_manager.install_error.connect(self.on_install_error)
    
    def load_versions(self):
        self._is_loading = True
        self.version_list.clear()
        self.changelog_text.clear()
        self.download_version_btn.setEnabled(False)
        
        self.status_card.show()
        self.status_icon.show()
        self.status_label.setText("正在获取版本信息...")
        self.update_btn.hide()
        
        self.version_manager.fetch_remote_versions()
    
    def on_versions_loaded(self, versions):
        self._is_loading = False
        self.refresh_version_list(versions)
        self.check_for_updates()
    
    def set_versions(self, versions):
        self._is_loading = False
        self.refresh_version_list(versions)
        self._check_update_status()
    
    def _check_update_status(self):
        include_beta = self.show_beta_switch.isChecked()
        latest = self.version_manager.check_for_updates(include_beta)
        
        self.refresh_btn.setEnabled(True)
        self.status_icon.hide()
        
        if latest:
            self.status_label.setText(f"发现新版本: v{latest.version}")
            self.update_btn.show()
            self.selected_version = latest
            self.status_card.setProperty("status", "updateAvailable")
        else:
            self.status_label.setText("已是最新版本")
            self.status_card.setProperty("status", "upToDate")
        
        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
        self.status_card.show()
    
    def on_load_error(self, error_msg):
        self._is_loading = False
        self.status_icon.hide()
        self.status_label.setText(f"获取版本信息失败: {error_msg}")
        self.status_card.show()
        
        versions = self.version_manager.get_all_versions()
        if versions:
            self.refresh_version_list(versions)
    
    def refresh_version_list(self, versions):
        self.version_list.clear()
        show_beta = self.show_beta_switch.isChecked()
        current_ver = self.version_manager.current_version
        
        for v in versions:
            if not show_beta and v.release_type != ReleaseType.STABLE:
                continue
            
            item = QListWidgetItem(self.version_list)
            is_current = v.version == current_ver
            widget = VersionListItem(v, is_current)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, v)
            self.version_list.addItem(item)
            self.version_list.setItemWidget(item, widget)
    
    def on_show_beta_changed(self, checked):
        versions = self.version_manager.get_all_versions()
        self.refresh_version_list(versions)
    
    def check_for_updates(self):
        self.refresh_btn.setEnabled(False)
        self.status_card.show()
        self.status_icon.show()
        self.status_label.setText("正在检查更新...")
        self.update_btn.hide()
        
        if self._is_loading:
            return
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._do_check_update)
    
    def _do_check_update(self):
        include_beta = self.show_beta_switch.isChecked()
        latest = self.version_manager.check_for_updates(include_beta)
        
        self.refresh_btn.setEnabled(True)
        self.status_icon.hide()
        
        if latest:
            self.status_label.setText(f"发现新版本: v{latest.version}")
            self.update_btn.show()
            self.selected_version = latest
            self.status_card.setProperty("status", "updateAvailable")
        else:
            self.status_label.setText("已是最新版本")
            self.status_card.setProperty("status", "upToDate")
        
        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
        self.status_card.show()
    
    def on_version_selected(self, current, previous):
        if not current:
            self.changelog_text.clear()
            self.download_version_btn.setEnabled(False)
            return
        
        version_info = current.data(Qt.UserRole)
        if version_info:
            self.selected_version = version_info
            self.changelog_text.setMarkdown(version_info.changelog)
            
            current_ver = self.version_manager.current_version
            can_download = compare_versions(version_info.version, current_ver) != 0
            self.download_version_btn.setEnabled(can_download)
    
    def on_update_clicked(self):
        if self.selected_version:
            self.start_download(self.selected_version)
    
    def on_download_version_clicked(self):
        if self.selected_version:
            self.start_download(self.selected_version)
    
    def start_download(self, version: VersionInfo):
        if not version.download_url:
            InfoBar.warning(
                title="无法下载",
                content="该版本没有可用的下载链接",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        box = MessageBox(
            "确认更新",
            f"即将下载并安装 v{version.version}\n\n"
            "下载完成后程序将自动关闭并进行更新。\n"
            "是否继续？",
            self
        )
        box.yesButton.setText("开始更新")
        box.cancelButton.setText("取消")
        
        if not box.exec_():
            return
        
        self.download_widget.show()
        self.status_card.hide()
        self.install_widget.hide()
        self.download_label.setText(f"正在下载 v{version.version}...")
        self.download_progress.setValue(0)
        self.download_percent.setText("0%")
        self.download_speed.setText("")
        
        default_path = os.path.join(os.path.expanduser("~"), "Downloads", "DoroPet_Updates")
        self.version_manager.download_update(version, default_path, auto_install=True)
    
    def on_download_progress(self, percent, total_bytes, speed_str=""):
        self.download_progress.setValue(percent)
        self.download_percent.setText(f"{percent}%")
        if speed_str:
            self.download_speed.setText(speed_str)
    
    def on_download_completed(self, file_path):
        self.download_widget.hide()
        self.install_widget.show()
        self.install_label.setText("正在安装更新...")
        self.install_progress.setValue(0)
        self.install_percent.setText("0%")
        self.install_step_label.setText("准备安装...")
        
        self.download_completed.emit(file_path)
    
    def on_download_error(self, error_msg):
        self.download_widget.hide()
        self.install_widget.hide()
        self.status_card.show()
        
        InfoBar.error(
            title="下载失败",
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def on_install_progress(self, step_text: str, percent: int):
        self.install_progress.setValue(percent)
        self.install_percent.setText(f"{percent}%")
        self.install_step_label.setText(step_text)
    
    def on_install_completed(self):
        self.install_step_label.setText("安装完成，即将重启...")
        self.install_progress.setValue(100)
        self.install_percent.setText("100%")
        
        InfoBar.success(
            title="更新完成",
            content="程序将在3秒后自动重启...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, self._restart_application)
    
    def on_install_error(self, error_msg):
        self.install_widget.hide()
        self.status_card.show()
        
        InfoBar.error(
            title="安装失败",
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def _restart_application(self):
        import sys
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
        sys.exit(0)
    
    def cancel_download(self):
        self.version_manager.cancel_download()
        self.download_widget.hide()
        self.status_card.show()
        self.install_widget.hide()
        
        InfoBar.warning(
            title="已取消",
            content="下载已取消",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

class AboutWidget(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        title = TitleLabel("关于软件", self)
        layout.addWidget(title)
        
        info_widget = QWidget(self)
        info_widget.setObjectName("aboutInfoWidget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)
        
        info_layout.addWidget(StrongBodyLabel("DoroPet", self))
        info_layout.addWidget(BodyLabel(f"版本: v{__version__}", self))
        info_layout.addWidget(BodyLabel("一款可爱的桌面宠物应用", self))
        info_layout.addWidget(CaptionLabel("© 2026 DoroPet Team", self))
        
        layout.addWidget(info_widget)
        
        link_layout = QHBoxLayout()
        link_layout.setSpacing(16)
        
        gitee_btn = PushButton(FIF.GITHUB, "Gitee 仓库", self)
        gitee_btn.clicked.connect(self.open_gitee)
        link_layout.addWidget(gitee_btn)
        
        link_layout.addStretch()
        layout.addLayout(link_layout)
    
    def open_gitee(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://gitee.com/waterfeet/DoroPet_V3"))

class UpdateNotificationDialog(QWidget):
    update_now = pyqtSignal()
    remind_later = pyqtSignal()

    def __init__(self, version_info: VersionInfo, current_version: str, parent=None):
        super().__init__(parent)
        self.version_info = version_info
        self.current_version = current_version
        self._is_dragging = False
        self._drag_pos = None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 400)
        self.setup_ui()
        self._apply_theme()
        self.center_on_parent()

    def setup_ui(self):
        self.setObjectName("updateNotificationDialog")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        
        self.container = QWidget(self)
        self.container.setObjectName("updateDialogContainer")
        self.container.setGeometry(10, 10, self.width() - 20, self.height() - 20)
        self.container.setGraphicsEffect(shadow)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        
        self.title_icon = QLabel(self.container)
        self.title_icon.setFixedSize(28, 28)
        self.title_icon.setText("🎁")
        header_layout.addWidget(self.title_icon)
        
        self.title_label = TitleLabel("发现新版本", self.container)
        header_layout.addWidget(self.title_label, 1)
        
        self.close_btn = PushButton(FIF.CANCEL, "关闭", self.container)
        self.close_btn.setFixedHeight(28)
        self.close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(header_layout)
        
        self.version_widget = QWidget(self.container)
        version_layout = QHBoxLayout(self.version_widget)
        version_layout.setContentsMargins(12, 8, 12, 8)
        version_layout.setSpacing(16)
        
        old_ver_layout = QVBoxLayout()
        old_ver_layout.setSpacing(2)
        self.old_ver_label = CaptionLabel("当前版本", self.version_widget)
        self.old_ver_value = StrongBodyLabel(f"v{self.current_version}", self.version_widget)
        old_ver_layout.addWidget(self.old_ver_label, alignment=Qt.AlignCenter)
        old_ver_layout.addWidget(self.old_ver_value, alignment=Qt.AlignCenter)
        version_layout.addLayout(old_ver_layout)
        
        self.arrow_label = QLabel("→", self.version_widget)
        version_layout.addWidget(self.arrow_label)
        
        new_ver_layout = QVBoxLayout()
        new_ver_layout.setSpacing(2)
        self.new_ver_label = CaptionLabel("最新版本", self.version_widget)
        self.new_ver_value = StrongBodyLabel(f"v{self.version_info.version}", self.version_widget)
        new_ver_layout.addWidget(self.new_ver_label, alignment=Qt.AlignCenter)
        new_ver_layout.addWidget(self.new_ver_value, alignment=Qt.AlignCenter)
        version_layout.addLayout(new_ver_layout)
        
        version_layout.addStretch()
        
        self.type_label = QLabel(get_version_type_display(self.version_info.release_type), self.version_widget)
        version_layout.addWidget(self.type_label)
        
        main_layout.addWidget(self.version_widget)
        
        self.changelog_header = StrongBodyLabel("更新内容", self.container)
        main_layout.addWidget(self.changelog_header)
        
        self.changelog_text = QTextEdit(self.container)
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setFixedHeight(110)
        changelog = self.version_info.changelog or "暂无更新说明"
        self.changelog_text.setMarkdown(changelog[:500] + ("..." if len(changelog) > 500 else ""))
        main_layout.addWidget(self.changelog_text)
        
        info_layout = QHBoxLayout()
        self.date_label = None
        self.size_label = None
        if self.version_info.release_date:
            self.date_label = CaptionLabel(f"发布日期: {self.version_info.release_date}", self.container)
            info_layout.addWidget(self.date_label)
        if self.version_info.file_size > 0:
            self.size_label = CaptionLabel(f"大小: {self.version_info.display_size}", self.container)
            info_layout.addWidget(self.size_label)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)
        
        main_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.remind_btn = PushButton(FIF.CALENDAR, "稍后提醒", self.container)
        self.remind_btn.setFixedHeight(36)
        self.remind_btn.clicked.connect(self._on_remind_later)
        btn_layout.addWidget(self.remind_btn)
        
        self.update_btn = PrimaryPushButton(FIF.UPDATE, "立即更新", self.container)
        self.update_btn.setFixedHeight(36)
        self.update_btn.clicked.connect(self._on_update_now)
        btn_layout.addWidget(self.update_btn, 1)
        
        main_layout.addLayout(btn_layout)

    def _apply_theme(self):
        is_dark = isDarkTheme()
        if is_dark:
            self.container.setStyleSheet("""
                QWidget#updateDialogContainer {
                    background-color: #2b2b2b;
                    border-radius: 12px;
                    border: 1px solid #454545;
                }
            """)
            self.title_icon.setStyleSheet("font-size: 24px; background: transparent;")
            self.title_label.setStyleSheet("color: #ffffff;")
            self.arrow_label.setStyleSheet("font-size: 18px; color: #666; background: transparent;")
            self.version_widget.setStyleSheet("background-color: #363636; border-radius: 8px;")
            self.new_ver_value.setStyleSheet("color: #64b5f6; font-weight: bold;")
            self.type_label.setStyleSheet("background-color: #1976d2; color: white; padding: 2px 8px; border-radius: 4px;")
            self.changelog_header.setStyleSheet("color: #e0e0e0;")
            self.changelog_text.setStyleSheet("background-color: #1e1e1e; border: 1px solid #404040; border-radius: 6px; color: #e0e0e0;")
            if self.date_label:
                self.date_label.setStyleSheet("color: #888;")
            if self.size_label:
                self.size_label.setStyleSheet("color: #888;")
        else:
            self.container.setStyleSheet("""
                QWidget#updateDialogContainer {
                    background-color: #ffffff;
                    border-radius: 12px;
                    border: 1px solid #e0e0e0;
                }
            """)
            self.title_icon.setStyleSheet("font-size: 24px; background: transparent;")
            self.title_label.setStyleSheet("color: #000000;")
            self.arrow_label.setStyleSheet("font-size: 18px; color: #999; background: transparent;")
            self.version_widget.setStyleSheet("background-color: #f5f5f5; border-radius: 8px;")
            self.new_ver_value.setStyleSheet("color: #0078d4; font-weight: bold;")
            self.type_label.setStyleSheet("background-color: #0078d4; color: white; padding: 2px 8px; border-radius: 4px;")
            self.changelog_header.setStyleSheet("color: #333;")
            self.changelog_text.setStyleSheet("background-color: #fafafa; border: 1px solid #e0e0e0; border-radius: 6px; color: #333;")
            if self.date_label:
                self.date_label.setStyleSheet("color: #666;")
            if self.size_label:
                self.size_label.setStyleSheet("color: #666;")

    def center_on_parent(self):
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)

    def _on_update_now(self):
        self.close()
        self.update_now.emit()

    def _on_remind_later(self):
        self.close()
        self.remind_later.emit()

    def _on_close(self):
        self.remind_later.emit()
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._drag_pos = None


class UpdateInterface(ScrollArea):
    def __init__(self, parent=None, version_manager=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setObjectName("updateView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("UpdateInterface")
        self._version_manager = version_manager
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        
        self.update_widget = UpdateWidget(self, self._version_manager)
        layout.addWidget(self.update_widget)
        
        self.about_widget = AboutWidget(self)
        layout.addWidget(self.about_widget)
        
        layout.addStretch()
    
    def set_versions(self, versions):
        self.update_widget.set_versions(versions)
