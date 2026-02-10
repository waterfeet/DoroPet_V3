import sys
import os

# 将当前目录添加到 sys.path 以便能找到 src 模块
# 嵌入式 Python 环境可能不会自动添加脚本所在目录
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.live2dview import Live2DWidget
from src.resource_utils import resource_path
from src.core.logger import setup_logger
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import *

# Initialize Logger
logger = setup_logger()

def main():
    app = QApplication(sys.argv)
    logger.info("Application started.")
    
    # 防止关闭主窗口（设置界面）时导致程序退出
    # 同时也配合系统托盘功能，使程序可以后台运行
    app.setQuitOnLastWindowClosed(False) 

    # --- 设置全局字体开始 ---
    font_path = resource_path("cfg/zxf.ttf")
    
    # 检查文件是否存在
    if os.path.exists(font_path):
        # 1. 将字体文件加载到数据库
        font_id = QFontDatabase.addApplicationFont(font_path)
        
        # 2. 如果加载成功 (font_id != -1)
        if font_id != -1:
            # 获取字体的真实家族名称 (文件名不一定等于字体名)
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                font_name = font_families[0]
                
                # 3. 创建字体对象，设置大小为 12 (可以根据需要调整)
                custom_font = QFont(font_name, 12)
                
                # 4. 应用到整个程序
                app.setFont(custom_font)
                logger.info(f"成功加载字体: {font_name}")
        else:
            logger.warning(f"无法加载字体文件: {font_path}")
    else:
        logger.warning(f"未找到字体文件: {font_path}，将使用系统默认字体")
    # --- 设置全局字体结束 ---

    # 确保路径正确
    logger.info("Initializing Live2DWidget...")
    w = Live2DWidget(path=resource_path("models/Doro/Doro.model3.json"))
    
    w.show()
    
    # --- 系统托盘设置 ---
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
        if w.isVisible():
            w.hide()
        else:
            w.show()
            w.activateWindow()
    action_toggle.triggered.connect(toggle_pet)
    tray_menu.addAction(action_toggle)
    
    # 2. 打开主界面
    action_settings = QAction("打开主界面", app)
    action_settings.triggered.connect(w.open_main_window)
    tray_menu.addAction(action_settings)
    
    # 3. 锁定/解锁
    action_lock = QAction("锁定/解锁", app)
    action_lock.setCheckable(True)
    action_lock.setChecked(False)
    def toggle_lock(checked):
        w.set_locked(checked)
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
            w.open_main_window()
            
    tray_icon.activated.connect(on_tray_activated)
    # -------------------
    
    # 测试：启动时说一句话
    w.talk("欢迎回来！")
    

    sys.exit(app.exec())

if __name__ == '__main__':
    main()