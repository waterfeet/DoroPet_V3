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
from .plugin_ui import PluginInterface
from .skills_ui import SkillsInterface
from .update_ui import UpdateInterface
from .pet_status_interface import PetStatusInterface
from .live2d_config_ui import Live2DConfigInterface
from src.core.database import ChatDatabase
from src.resource_utils import resource_path
from src.core.logger import logger

class MainWindow(FluentWindow):
    def __init__(self, version_manager=None):
        super().__init__()
        logger.info("Initializing MainWindow...")
        self.setObjectName("MainWindow")
        self._version_manager = version_manager
        
        # 1. 初始化窗口
        self.setWindowTitle("Doro Pet")
        self.resize(900, 700)
        
        # 2. 初始化数据库 (单一实例)
        self.db = ChatDatabase()

        # 3. 创建子界面
        self.chat_interface = ChatInterface(self.db, self)
        self.config_interface = ConfigInterface(self.db, self)
        self.voice_config_interface = VoiceConfigInterface(self.db, self)
        self.live2d_config_interface = Live2DConfigInterface(self.db, self)
        self.prompt_interface = PromptInterface(self.db, self)
        self.plugin_interface = PluginInterface(self)
        self.skills_interface = SkillsInterface(self)
        self.log_interface = LogInterface(self)
        self.update_interface = UpdateInterface(self, version_manager)
        self.settings_interface = SettingsInterface(self)
        
        self.attr_manager = None
        
        self.pet_status_interface = PetStatusInterface(None, self.db, self)
        
        # 4. 初始化导航栏
        self.init_navigation()
        
        # 5. 初始化标题栏功能 (置顶、主题切换)
        self.init_title_bar()
        
        # 初始化加载主题
        if isDarkTheme():
            setTheme(Theme.DARK)
            self.load_stylesheet(resource_path("themes/dark.qss"))
        else:
            setTheme(Theme.LIGHT)
            self.load_stylesheet(resource_path("themes/light.qss"))

        # 6. 初始化窗口属性
        self.init_window()

    def init_navigation(self):
        self.addSubInterface(self.pet_status_interface, FIF.HOME, "桌宠状态")
        self.addSubInterface(self.chat_interface, FIF.CHAT, "AI 聊天")
        self.addSubInterface(self.config_interface, FIF.ROBOT, "模型配置")
        self.addSubInterface(self.voice_config_interface, FIF.MICROPHONE, "语音设置")
        self.addSubInterface(self.live2d_config_interface, FIF.PHOTO, "Live2D模型")
        self.addSubInterface(self.prompt_interface, FIF.PEOPLE, "角色扮演")
        self.addSubInterface(self.plugin_interface, FIF.BOOK_SHELF, "插件管理")
        self.addSubInterface(self.skills_interface, FIF.PALETTE, "技能管理")
        self.addSubInterface(self.log_interface, FIF.COMMAND_PROMPT, "运行日志")
        
        # Connect signals
        self.voice_config_interface.settingsChanged.connect(self.chat_interface.update_voice_ui_visibility)
        self.pet_status_interface.start_chat_requested.connect(self._switch_to_chat)

        self.navigationInterface.setCurrentItem(self.pet_status_interface.objectName())
        
        # 添加设置到底部
        self.addSubInterface(self.update_interface, FIF.UPDATE, "软件更新", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settings_interface, FIF.SETTING, "通用设置", NavigationItemPosition.BOTTOM)

    def init_window(self):
        icon_path = resource_path("data/icons/app.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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

    def _switch_to_chat(self):
        self.switchTo(self.chat_interface)

    def toggle_theme(self):
        if isDarkTheme():
            logger.info("Switching to Light theme.")
            setTheme(Theme.LIGHT)
            self.load_stylesheet(resource_path("themes/light.qss"))
        else:
            logger.info("Switching to Dark theme.")
            setTheme(Theme.DARK)
            self.load_stylesheet(resource_path("themes/dark.qss"))
            
        is_dark = isDarkTheme()
        if hasattr(self, 'pet_status_interface'):
            self.pet_status_interface.update_theme(is_dark)
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
        if hasattr(self, 'live2d_config_interface'):
            self.live2d_config_interface.update_theme()
        
        if hasattr(self, 'live2d_widget') and hasattr(self.live2d_widget, 'quick_chat_window'):
            if self.live2d_widget.quick_chat_window:
                self.live2d_widget.quick_chat_window.update_theme()

    def load_stylesheet(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
                QApplication.instance().setStyleSheet(qss)
        else:
            logger.warning(f"Stylesheet not found: {path}")

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        
        if hasattr(widget, 'attr_manager'):
            self.attr_manager = widget.attr_manager
        
        if hasattr(self, 'settings_interface'):
            self.settings_interface.set_live2d_widget(widget)
        
        if hasattr(self, 'chat_interface'):
            self.chat_interface.set_live2d_widget(widget)
        
        if hasattr(self, 'live2d_config_interface'):
            self.live2d_config_interface.set_live2d_widget(widget)
        
        if hasattr(self, 'pet_status_interface') and self.attr_manager:
            self.pet_status_interface.set_attr_manager(self.attr_manager)
        
        if hasattr(widget, '_startup_checker') and widget._startup_checker:
            widget._startup_checker.set_main_window(self)
        
        if hasattr(self, 'pet_status_interface') and hasattr(self.pet_status_interface, 'music_player_card'):
            from PyQt5.QtCore import QTimer, QSettings
            settings = QSettings("DoroPet", "Settings")
            play_music_on_startup = settings.value("play_music_on_startup", False, type=bool)
            if play_music_on_startup:
                QTimer.singleShot(1500, self.pet_status_interface.music_player_card.auto_play)
        
    def closeEvent(self, event):
        """重写关闭事件，使其隐藏而不是关闭"""
        logger.info("MainWindow hidden to tray.")
        self.hide()
        event.ignore()