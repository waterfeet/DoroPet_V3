import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QStackedWidget, QTextEdit, QProgressBar, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, TitleLabel, StrongBodyLabel, BodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, ProgressRing, CardWidget,
    FluentIcon as FIF, InfoBar, InfoBarPosition, SwitchButton,
    SubtitleLabel, isDarkTheme
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.version_manager = VersionManager(self)
        self.selected_version: VersionInfo = None
        self.setup_ui()
        self.connect_signals()
        self.load_versions()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = TitleLabel("注意-本页面实际功能尚未开发，页面仅用于展示", self)
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
        self.version_manager.download_progress.connect(self.on_download_progress)
        self.version_manager.download_completed.connect(self.on_download_completed)
        self.version_manager.download_error.connect(self.on_download_error)
    
    def load_versions(self):
        versions = self.version_manager.get_all_versions()
        self.refresh_version_list(versions)
        self.check_for_updates()
    
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
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, self._do_check_update)
    
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
        self.download_widget.show()
        self.status_card.hide()
        self.download_label.setText(f"正在下载 v{version.version}...")
        self.download_progress.setValue(0)
        self.download_percent.setText("0%")
        
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", default_path)
        
        if not save_dir:
            self.download_widget.hide()
            self.status_card.show()
            return
        
        self.version_manager.download_update(version, save_dir)
    
    def on_download_progress(self, percent, total_bytes):
        self.download_progress.setValue(percent)
        self.download_percent.setText(f"{percent}%")
    
    def on_download_completed(self, file_path):
        self.download_widget.hide()
        
        InfoBar.success(
            title="下载完成",
            content=f"文件已保存到: {file_path}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
        
        self.download_completed.emit(file_path)
    
    def on_download_error(self, error_msg):
        self.download_widget.hide()
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
    
    def cancel_download(self):
        self.version_manager.cancel_download()
        self.download_widget.hide()
        self.status_card.show()
        
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
        
        github_btn = PushButton(FIF.GITHUB, "GitHub", self)
        github_btn.clicked.connect(self.open_github)
        link_layout.addWidget(github_btn)
        
        gitee_btn = PushButton(FIF.GITHUB, "Gitee", self)
        gitee_btn.clicked.connect(self.open_gitee)
        link_layout.addWidget(gitee_btn)
        
        link_layout.addStretch()
        layout.addLayout(link_layout)
    
    def open_github(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://github.com"))
    
    def open_gitee(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://gitee.com/waterfeet/opendoro"))

class UpdateInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setObjectName("updateView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("UpdateInterface")
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        
        self.update_widget = UpdateWidget(self)
        layout.addWidget(self.update_widget)
        
        self.about_widget = AboutWidget(self)
        layout.addWidget(self.about_widget)
        
        layout.addStretch()
