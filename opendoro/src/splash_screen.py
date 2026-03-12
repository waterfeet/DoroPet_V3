from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 240)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        container = QWidget()
        container.setObjectName("splashContainer")
        container.setStyleSheet("""
            #splashContainer {
                background-color: #f9f9f9;
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setContentsMargins(30, 25, 30, 25)
        
        title_label = QLabel("Doro Pet")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #0078d4;")
        title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title_label)
        
        subtitle_label = QLabel("桌面宠物")
        subtitle_label.setStyleSheet("font-size: 14px; color: #888888; margin-bottom: 15px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(subtitle_label)
        
        self.status_label = QLabel("正在启动...")
        self.status_label.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        self.status_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.status_label)
        
        self.loading_label = QLabel()
        self.loading_label.setStyleSheet("color: #666666;")
        self.loading_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.loading_label)
        
        self.dot_count = 0
        self.dot_timer = QTimer(self)
        self.dot_timer.timeout.connect(self.update_loading_dots)
        self.dot_timer.start(1000)
        
        layout.addWidget(container, 0, Qt.AlignCenter)
        
        screen = QDesktopWidget().screenGeometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
    
    def update_loading_dots(self):
        self.dot_count = (self.dot_count + 1) % 4
        dots = "●" * self.dot_count + "○" * (3 - self.dot_count)
        self.loading_label.setText(dots)
    
    def set_status(self, text):
        self.status_label.setText(text)
        self.dot_timer.stop()
        self.loading_label.setText("请稍候")
    
    def close_splash(self):
        self.dot_timer.stop()
        self.close()
