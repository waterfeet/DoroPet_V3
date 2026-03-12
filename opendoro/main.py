import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.dependency_checker import check_and_exit_on_failure
check_and_exit_on_failure()

from src.live2dview import Live2DWidget
from src.resource_utils import resource_path
from src.core.logger import setup_logger
from src.splash_screen import SplashScreen
from src.provider.manager import ProviderManager
from src.core.database import DatabaseManager
from src.core.startup_update_checker import StartupUpdateChecker
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import *

# Initialize Logger
logger = setup_logger()

def init_provider_framework():
    try:
        from src.provider.sources import (
            ProviderOpenAI, ProviderDeepSeek, ProviderAnthropic,
            ProviderOllama, ProviderMoonshot, ProviderGemini,
            ProviderGroq, ProviderZhipu,
            ProviderEdgeTTS, ProviderOpenAITTS, ProviderGradioTTS,
            ProviderOpenAIImage
        )
        logger.info("Provider adapters loaded successfully")
    except ImportError as e:
        logger.warning(f"Some provider adapters could not be loaded: {e}")
    
    db = DatabaseManager().config
    pm = ProviderManager.get_instance()
    pm.load_providers_from_db(db)
    logger.info(f"ProviderManager initialized with {len(pm.get_all_llm_providers())} LLM providers")

def setup_tray_icon(app, widget):
    """设置系统托盘"""
    tray_icon = QSystemTrayIcon(app)
    
    # 尝试加载图标
    icon_path = resource_path("data/icons/logo.png")
    if not os.path.exists(icon_path):
        icon_path = resource_path("data/icons/orange.ico")
        
    if os.path.exists(icon_path):
        tray_icon.setIcon(QIcon(icon_path))
    else:
        logger.warning("Tray icon not found.")
        
    # 托盘菜单
    tray_menu = QMenu()
    
    # 1. 显示/隐藏桌宠
    action_toggle = QAction("显示/隐藏桌宠", app)
    def toggle_pet():
        if widget.isVisible():
            widget.hide()
            if hasattr(widget, 'status_overlay') and widget.status_overlay.isVisible():
                widget.status_overlay._fade_out()
        else:
            widget.show()
            widget.activateWindow()
    action_toggle.triggered.connect(toggle_pet)
    tray_menu.addAction(action_toggle)
    
    # 2. 打开主界面
    action_settings = QAction("打开主界面", app)
    action_settings.triggered.connect(widget.open_main_window)
    tray_menu.addAction(action_settings)
    
    # 3. 锁定/解锁
    action_lock = QAction("锁定/解锁", app)
    action_lock.setCheckable(True)
    action_lock.setChecked(False)
    def toggle_lock(checked):
        widget.set_locked(checked)
        if checked:
            action_lock.setText("解锁")
        else:
            action_lock.setText("锁定")
            
    action_lock.triggered.connect(toggle_lock)
    tray_menu.addAction(action_lock)

    tray_menu.addSeparator()
    
    # 4. 退出程序
    action_quit = QAction("退出", app)
    action_quit.triggered.connect(app.quit)
    tray_menu.addAction(action_quit)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # 双击托盘显示主界面
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.DoubleClick:
            widget.open_main_window()
            
    tray_icon.activated.connect(on_tray_activated)
    
    return tray_icon

def setup_startup_update_checker(widget):
    update_checker = StartupUpdateChecker(widget)
    
    def on_update_available(version_info):
        logger.info(f"Update available: v{version_info.version}")
        show_update_dialog(widget, version_info, update_checker)
    
    def on_check_failed(error_msg):
        logger.warning(f"Startup update check failed: {error_msg}")
    
    update_checker.update_available.connect(on_update_available)
    update_checker.check_failed.connect(on_check_failed)
    
    return update_checker

def show_update_dialog(widget, version_info, update_checker):
    from src.ui.update_ui import UpdateNotificationDialog
    from src.core.version_manager import __version__
    
    main_window = None
    if hasattr(widget, 'main_window') and widget.main_window:
        main_window = widget.main_window
    else:
        main_window = widget.open_main_window()
    
    dialog = UpdateNotificationDialog(version_info, __version__, main_window)
    
    def on_update_now():
        main_window.switchTo(main_window.update_interface)
        
        update_widget = main_window.update_interface.update_widget
        if update_widget:
            update_widget.selected_version = version_info
            update_widget.start_download(version_info)
    
    def on_remind_later():
        logger.info("User chose to be reminded later")
    
    dialog.update_now.connect(on_update_now)
    dialog.remind_later.connect(on_remind_later)
    dialog.show()

def main():
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='DoroPet Desktop Pet')
    parser.add_argument('--create-shortcut', action='store_true', help='创建桌面快捷方式')
    args = parser.parse_args()
    
    # 如果指定了创建快捷方式参数，执行创建操作
    if args.create_shortcut:
        from src.core.shortcut_utils import create_desktop_shortcut
        success, message = create_desktop_shortcut(replace_existing=False)
        logger.info(f"Shortcut creation: {message}")
        # 可以选择在这里退出，或者继续启动程序
    
    app = QApplication(sys.argv)
    # 显示启动画面（立即显示，让用户知道程序正在启动）
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    logger.info("Application started.")

    # 设置应用程序图标 (任务栏图标)
    icon_path = resource_path("data/icons/logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Windows 任务栏图标设置
    try:
        import ctypes
        app_id = "DoroPet.Application.v3"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        logger.warning(f"Failed to set AppUserModelID: {e}")
    
    # 防止关闭主窗口（设置界面）时导致程序退出
    # 同时也配合系统托盘功能，使程序可以后台运行
    app.setQuitOnLastWindowClosed(False) 

    # Initialize Provider Framework
    splash.set_status("正在初始化 Provider 框架...")
    init_provider_framework()

    # Load light.qss
    qss_path = resource_path("themes/light.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            logger.info(f"Loaded stylesheet: {qss_path}")
        except Exception as e:
            logger.error(f"Failed to load stylesheet: {e}")
    else:
        logger.warning(f"Stylesheet not found: {qss_path}")

    # 确保路径正确
    logger.info("Initializing Live2DWidget...")
    splash.set_status("正在加载Live2D模型...")
    
    from src.core.database import DatabaseManager
    db_manager = DatabaseManager()
    default_model_path = resource_path("models/Doro/Doro.model3.json")
    
    try:
        personas = db_manager.personas.get_personas()
        if personas:
            first_persona = personas[0]
            if len(first_persona) > 7 and first_persona[7]:
                saved_model = first_persona[7]
                if os.path.exists(saved_model):
                    default_model_path = saved_model
                    logger.info(f"Using saved model from persona: {saved_model}")
    except Exception as e:
        logger.warning(f"Failed to load model from database: {e}")
    
    w = Live2DWidget(path=default_model_path)
    
    # 读取启动设置
    settings = QSettings("DoroPet", "Settings")
    hide_pet_on_startup = settings.value("hide_pet_on_startup", False, type=bool)
    
    if hide_pet_on_startup:
        w.hide()
        w.open_main_window()
        logger.info("Pet hidden on startup, showing main window instead.")
    else:
        w.show()
    
    # --- 系统托盘设置 ---
    tray_icon = setup_tray_icon(app, w)
    # -------------------
    
    # 测试：启动时说一句话
    if not hide_pet_on_startup:
        w.talk("欢迎回来！")
    
    # 关闭启动画面
    splash.close_splash()
    logger.info("Splash screen closed")
    
    update_checker = setup_startup_update_checker(w)
    w._startup_checker = update_checker
    update_checker.start_check(delay_ms=3000)

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
