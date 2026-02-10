import os
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices

from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentTranslator, 
                            NavigationAvatarWidget, SplashScreen, TransparentToolButton,
                            setTheme, Theme, isDarkTheme)
from qfluentwidgets import FluentIcon as FIF

# 导入子界面
from .chat_ui import ChatInterface
from .config_ui import ConfigInterface
from .settings_ui import SettingsInterface
from .prompt_ui import PromptInterface
from .log_ui import LogInterface
from .voice_config_ui import VoiceConfigInterface
from src.core.database import ChatDatabase
from src.resource_utils import resource_path
from src.core.logger import logger

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow...")
        self.setObjectName("MainWindow")
        
        # 1. 初始化窗口
        self.setWindowTitle("Doro Pet")
        self.resize(900, 700)
        
        # 2. 初始化数据库 (单一实例)
        self.db = ChatDatabase()

        # 3. 创建子界面
        self.chat_interface = ChatInterface(self.db, self)
        self.config_interface = ConfigInterface(self.db, self)
        self.voice_config_interface = VoiceConfigInterface(self.db, self)
        self.prompt_interface = PromptInterface(self.db, self)
        self.log_interface = LogInterface(self)
        self.settings_interface = SettingsInterface(self)
        
        # 4. 初始化导航栏
        self.init_navigation()
        
        # 5. 初始化标题栏功能 (置顶、主题切换)
        self.init_title_bar()
        
        # 初始化加载主题
        if isDarkTheme():
            self.load_stylesheet(resource_path("themes/dark.qss"))
        else:
            self.load_stylesheet(resource_path("themes/light.qss"))

        # 6. 初始化窗口属性
        self.init_window()

    def init_navigation(self):
        # 添加子界面到导航栏
        self.addSubInterface(self.chat_interface, FIF.CHAT, "AI 聊天")
        self.addSubInterface(self.config_interface, FIF.ROBOT, "模型配置")
        self.addSubInterface(self.voice_config_interface, FIF.MICROPHONE, "语音设置")
        self.addSubInterface(self.prompt_interface, FIF.PEOPLE, "角色扮演")
        self.addSubInterface(self.log_interface, FIF.COMMAND_PROMPT, "运行日志")
        
        # Connect signals
        self.voice_config_interface.settingsChanged.connect(self.chat_interface.update_voice_ui_visibility)

        self.navigationInterface.setCurrentItem(self.chat_interface.objectName())
        
        # 添加设置到底部
        self.addSubInterface(self.settings_interface, FIF.SETTING, "通用设置", NavigationItemPosition.BOTTOM)

    def init_window(self):
        # 设置窗口居中
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

    def init_title_bar(self):
        # 1. 创建按钮
        self.pin_btn = TransparentToolButton(FIF.PIN, self)
        self.pin_btn.setCheckable(True)
        self.pin_btn.setToolTip("置顶窗口")
        self.pin_btn.clicked.connect(self.toggle_pinning)

        self.theme_btn = TransparentToolButton(FIF.CONSTRACT, self)
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.clicked.connect(self.toggle_theme)

        # 2. 添加到标题栏布局
        # 在最小化按钮之前插入 (通常布局倒数第3个是Min，但要视具体实现而定)
        # 我们插入到 layout 的倒数位置之前
        self.titleBar.layout().insertWidget(self.titleBar.layout().count() - 3, self.pin_btn, 0, Qt.AlignRight)
        self.titleBar.layout().insertWidget(self.titleBar.layout().count() - 3, self.theme_btn, 0, Qt.AlignRight)
        
        # 添加间距
        self.titleBar.layout().insertSpacing(self.titleBar.layout().count() - 3, 10)

    def toggle_pinning(self):
        hwnd = int(self.winId())
        
        # Windows Constants
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        
        # Ensure correct argument types for 64-bit compatibility
        SetWindowPos = ctypes.windll.user32.SetWindowPos
        SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        SetWindowPos.restype = wintypes.BOOL
        
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        
        if self.pin_btn.isChecked():
            # Set Always on Top
            SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
            self.pin_btn.setToolTip("取消置顶")
        else:
            # Remove Always on Top
            SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
            self.pin_btn.setToolTip("置顶窗口")

    def toggle_theme(self):
        if isDarkTheme():
            logger.info("Switching to Light theme.")
            setTheme(Theme.LIGHT)
            self.load_stylesheet(resource_path("themes/light.qss"))
        else:
            logger.info("Switching to Dark theme.")
            setTheme(Theme.DARK)
            self.load_stylesheet(resource_path("themes/dark.qss"))
            
        # Update interfaces that need manual style updates
        if hasattr(self, 'config_interface'):
            self.config_interface.update_theme()
        if hasattr(self, 'prompt_interface'):
            self.prompt_interface.update_theme()
        if hasattr(self, 'chat_interface'):
            self.chat_interface.update_theme()
        if hasattr(self, 'settings_interface'):
            self.settings_interface.update_theme()
        if hasattr(self, 'voice_config_interface'):
            self.voice_config_interface.update_theme()

    def load_stylesheet(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
                # 叠加到现有样式 或者 替换
                # 这里我们替换全局样式
                QApplication.instance().setStyleSheet(qss)
        else:
            logger.warning(f"Stylesheet not found: {path}")

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        # Propagate to SettingsInterface
        if hasattr(self, 'settings_interface'):
            self.settings_interface.set_live2d_widget(widget)
        
    def closeEvent(self, event):
        """重写关闭事件，使其隐藏而不是关闭"""
        logger.info("MainWindow hidden to tray.")
        self.hide()
        event.ignore()