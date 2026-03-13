# -*- coding: utf-8 -*-
"""
图形计算器插件 - 科技风格
支持科学计算和函数绘图功能
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QStackedWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

from qfluentwidgets import (
    CardWidget, TitleLabel, SubtitleLabel, BodyLabel, 
    StrongBodyLabel, PushButton, PrimaryPushButton, LineEdit,
    Pivot, isDarkTheme
)


class Plugin(QWidget):
    """图形计算器插件入口"""
    
    name = "计算器"  # 导航栏显示名称
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 主容器
        container = CardWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(16)
        
        # Pivot 切换器
        self.pivot = Pivot(self)
        self.pivot.setFixedHeight(40)
        self.pivot.addItem(routeKey="scientific", text="🔢 科学计算", onClick=lambda: self.stackedWidget.setCurrentIndex(0))
        self.pivot.addItem(routeKey="plotter", text="📊 函数绘图", onClick=lambda: self.stackedWidget.setCurrentIndex(1))
        container_layout.addWidget(self.pivot)
        
        # 使用 QStackedWidget 管理页面切换
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.setContentsMargins(0, 0, 0, 0)
        
        # 科学计算页面
        self.scientific_page = ScientificCalculator()
        self.stackedWidget.addWidget(self.scientific_page)
        
        # 函数绘图页面
        self.plotter_page = FunctionPlotter()
        self.stackedWidget.addWidget(self.plotter_page)
        
        container_layout.addWidget(self.stackedWidget)
        layout.addWidget(container)
        
        # 默认选中第一项
        self.pivot.setCurrentItem("scientific")


class ScientificCalculator(CardWidget):
    """科学计算器组件"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_input = ""
        self.result = 0
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # 显示屏区域
        display_card = CardWidget()
        display_layout = QVBoxLayout(display_card)
        display_layout.setContentsMargins(16, 16, 16, 16)
        
        # 结果显示
        self.result_label = StrongBodyLabel("0")
        self.result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        font = QFont("Segoe UI", 32, QFont.Bold)
        self.result_label.setFont(font)
        self.result_label.setTextColor(QColor(0, 212, 255), QColor(0, 212, 255))
        display_layout.addWidget(self.result_label)
        
        layout.addWidget(display_card)
        
        # 输入框
        self.input_edit = LineEdit()
        self.input_edit.setPlaceholderText("输入表达式，如: 2+3*4, sin(3.14), sqrt(16)")
        self.input_edit.setClearButtonEnabled(True)
        self.input_edit.returnPressed.connect(self.calculate)
        layout.addWidget(self.input_edit)
        
        # 功能按钮区
        func_card = CardWidget()
        func_layout = QHBoxLayout(func_card)
        func_layout.setContentsMargins(8, 8, 8, 8)
        func_layout.setSpacing(8)
        
        functions = [
            ("sin", "sin()"),
            ("cos", "cos()"),
            ("tan", "tan()"),
            ("log", "log10()"),
            ("ln", "log()"),
            ("√", "sqrt()"),
            ("x²", "**2"),
            ("^", "**"),
        ]
        
        for text, func in functions:
            btn = PushButton(text)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, f=func: self.insertFunction(f))
            func_layout.addWidget(btn)
        
        layout.addWidget(func_card)
        
        # 数字和操作按钮
        button_card = CardWidget()
        button_layout = QGridLayout(button_card)
        button_layout.setContentsMargins(8, 8, 8, 8)
        button_layout.setSpacing(8)
        
        buttons = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2), ("/", 0, 3), ("C", 0, 4),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2), ("*", 1, 3), ("⌫", 1, 4),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2), ("-", 2, 3), ("(", 2, 4),
            ("0", 3, 0), (".", 3, 1), ("π", 3, 2), ("+", 3, 3), (")", 3, 4),
        ]
        
        for text, row, col in buttons:
            if text == "C":
                btn = PushButton(text)
                btn.setFixedHeight(44)
                # 红色清除按钮
                btn.setStyleSheet("""
                    PushButton {
                        background-color: rgba(239, 68, 68, 0.1);
                        color: #ef4444;
                        border: 1px solid rgba(239, 68, 68, 0.3);
                    }
                    PushButton:hover {
                        background-color: rgba(239, 68, 68, 0.2);
                        border: 1px solid rgba(239, 68, 68, 0.5);
                    }
                """)
            elif text in "0123456789.":
                btn = PushButton(text)
                btn.setFixedHeight(44)
                # 数字按钮
                btn.setStyleSheet("""
                    PushButton {
                        background-color: rgba(48, 54, 61, 1);
                        color: #c9d1d9;
                        border: 1px solid #30363d;
                    }
                    PushButton:hover {
                        background-color: rgba(56, 62, 70, 1);
                        border: 1px solid #0378d4;
                    }
                """)
            else:
                btn = PushButton(text)
                btn.setFixedHeight(44)
                # 操作符按钮
                btn.setStyleSheet("""
                    PushButton {
                        background-color: rgba(33, 38, 45, 1);
                        color: #00d4ff;
                        border: 1px solid #30363d;
                    }
                    PushButton:hover {
                        background-color: rgba(41, 46, 53, 1);
                        border: 1px solid #0378d4;
                    }
                """)
            
            btn.clicked.connect(lambda checked, t=text: self.onButtonClicked(t))
            button_layout.addWidget(btn, row, col)
        
        layout.addWidget(button_card)
        
        # 等号按钮
        self.equals_btn = PrimaryPushButton("=  计算")
        self.equals_btn.setFixedHeight(50)
        self.equals_btn.clicked.connect(self.calculate)
        layout.addWidget(self.equals_btn)
        
        # 添加弹性空间，保持布局稳定
        layout.addStretch()
    
    def onButtonClicked(self, text):
        if text == "C":
            self.current_input = ""
            self.input_edit.setText("")
            self.result_label.setText("0")
        elif text == "⌫":
            self.current_input = self.current_input[:-1]
            self.input_edit.setText(self.current_input)
        elif text == "π":
            self.current_input += "3.14159265359"
            self.input_edit.setText(self.current_input)
        else:
            self.current_input += text
            self.input_edit.setText(self.current_input)
    
    def insertFunction(self, func):
        self.current_input += func
        self.input_edit.setText(self.current_input)
    
    def calculate(self):
        expression = self.input_edit.text().strip()
        if not expression:
            return
        
        try:
            import math
            allowed_names = {
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "sqrt": math.sqrt,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pow": pow,
                "abs": abs,
                "pi": math.pi,
                "e": math.e,
            }
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            # 格式化结果
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 10)
            
            self.result_label.setText(str(result))
            self.result_label.setTextColor(QColor(22, 163, 74), QColor(22, 163, 74))  # 绿色
            
            # 恢复颜色
            QTimer.singleShot(1000, lambda: self.result_label.setTextColor(
                QColor(0, 212, 255), QColor(0, 212, 255)
            ))
            
        except Exception as e:
            self.result_label.setText("Error")
            self.result_label.setTextColor(QColor(239, 68, 68), QColor(239, 68, 68))  # 红色
            
            QTimer.singleShot(1500, lambda: self.result_label.setTextColor(
                QColor(0, 212, 255), QColor(0, 212, 255)
            ))


class FunctionPlotter(CardWidget):
    """函数绘图组件"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # 标题
        header_layout = QHBoxLayout()
        title = SubtitleLabel("函数绘图")
        title.setTextColor(QColor(3, 120, 212), QColor(3, 120, 212))
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 输入区域
        input_card = CardWidget()
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(12, 12, 12, 12)
        
        input_label = BodyLabel("函数表达式 f(x) =")
        input_layout.addWidget(input_label)
        
        self.func_input = LineEdit()
        self.func_input.setPlaceholderText("例如: sin(x), x**2, exp(-x**2)")
        input_layout.addWidget(self.func_input)
        
        layout.addWidget(input_card)
        
        # 绘图区域占位
        plot_card = CardWidget()
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(12, 12, 12, 12)
        
        self.plot_placeholder = StrongBodyLabel("📈 绘图区域")
        self.plot_placeholder.setAlignment(Qt.AlignCenter)
        self.plot_placeholder.setFixedHeight(250)
        self.plot_placeholder.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        
        plot_layout.addWidget(self.plot_placeholder)
        layout.addWidget(plot_card)
        
        # 绘图按钮
        self.plot_btn = PrimaryPushButton("绘制图形")
        self.plot_btn.setFixedHeight(40)
        layout.addWidget(self.plot_btn)
        
        # 快捷函数
        quick_card = CardWidget()
        quick_layout = QHBoxLayout(quick_card)
        quick_layout.setContentsMargins(8, 8, 8, 8)
        quick_layout.setSpacing(8)
        
        quick_funcs = ["sin(x)", "cos(x)", "x**2", "sqrt(x)", "log(x)", "exp(x)"]
        for func in quick_funcs:
            btn = PushButton(func)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, f=func: self.func_input.setText(f))
            quick_layout.addWidget(btn)
        
        layout.addWidget(quick_card)
        
        # 添加弹性空间，保持布局稳定
        layout.addStretch()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 设置深色主题
    from qfluentwidgets import setTheme, Theme
    setTheme(Theme.DARK)
    
    window = Plugin()
    window.resize(450, 650)
    window.setWindowTitle("图形计算器")
    window.show()
    
    sys.exit(app.exec_())
