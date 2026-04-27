from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt

class TitleBar(QWidget):
    def __init__(self, parent=None, title="主菜单"):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.parent_window = parent
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # 标题
        self.title_label = QLabel(title)
        self.title_label.setObjectName("windowTitleLabel")
        # self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)
        
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # 切换主题按钮
        self.theme_btn = QPushButton("切换主题")
        self.theme_btn.setFixedSize(80, 25)
        self.theme_btn.clicked.connect(self.parent_window.toggle_theme)
        layout.addWidget(self.theme_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.parent_window.hide) # 只是隐藏，不退出程序
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        # 移动窗口逻辑交给父窗口处理，或者在这里调用父窗口移动
        if event.button() == Qt.LeftButton:
            self.parent_window.drag_pos = event.globalPos() - self.parent_window.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self.parent_window, 'drag_pos'):
            self.parent_window.move(event.globalPos() - self.parent_window.drag_pos)
        event.accept()