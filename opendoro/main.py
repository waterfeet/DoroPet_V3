import sys
import os

# 将当前目录添加到 sys.path 以便能找到 src 模块
# 嵌入式 Python 环境可能不会自动添加脚本所在目录
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.live2dview import Live2DWidget
from src.resource_utils import resource_path
from src.core.logger import setup_logger
from src.splash_screen import SplashScreen
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import *

# Initialize Logger
logger = setup_logger()

def setup_tray_icon(app, widget):
    """设置系统托盘"""
    tray_icon = QSystemTrayIcon(app)
    
    # 尝试加载图标
    icon_path = resource_path("data/icons/app.ico")
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

def main():
    app = QApplication(sys.argv)
    # 显示启动画面（立即显示，让用户知道程序正在启动）
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    logger.info("Application started.")

    # 设置应用程序图标 (任务栏图标)
    icon_path = resource_path("data/icons/logo-small.png")
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
    w = Live2DWidget(path=resource_path("models/Doro/Doro.model3.json"))
    
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
    

    sys.exit(app.exec())

if __name__ == '__main__':
    main()