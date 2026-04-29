# coding:utf-8
import random
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QColor, QPainter, QBrush
from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, TitleLabel, BodyLabel,
    StrongBodyLabel, FluentIcon
)


class ColorButton(QWidget):
    """一个点击后变色的自定义圆形按钮组件"""

    color_changed = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_color = QColor(52, 152, 219)  # 初始蓝色
        self.setFixedSize(220, 220)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def _update_style(self):
        r, g, b = self._bg_color.red(), self._bg_color.green(), self._bg_color.blue()
        self.setStyleSheet(f"""
            ColorButton {{
                background-color: rgb({r}, {g}, {b});
                border-radius: 110px;
                border: none;
            }}
            ColorButton:hover {{
                background-color: rgb({min(r+25, 255)}, {min(g+25, 255)}, {min(b+25, 255)});
                border: 3px solid rgba(255, 255, 255, 100);
            }}
            ColorButton:pressed {{
                background-color: rgb({max(r-35, 0)}, {max(g-35, 0)}, {max(b-35, 0)});
            }}
        """)

    def get_bg_color(self):
        return self._bg_color

    def set_bg_color(self, color):
        self._bg_color = color
        self._update_style()
        self.color_changed.emit(color)

    bg_color = pyqtProperty(QColor, get_bg_color, set_bg_color)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.randomize_color()
        super().mousePressEvent(event)

    def randomize_color(self):
        """生成随机鲜艳的颜色"""
        hue = random.randint(0, 359)
        saturation = random.randint(180, 255)
        value = random.randint(160, 230)
        new_color = QColor.fromHsv(hue, saturation, value)
        self.set_bg_color(new_color)


# ========== 预设色板 ==========
COLOR_PALETTES = [
    ("蔚蓝海洋", QColor(52, 152, 219)),
    ("烈焰红", QColor(231, 76, 60)),
    ("翡翠绿", QColor(46, 204, 113)),
    ("暗夜紫", QColor(155, 89, 182)),
    ("夕阳橙", QColor(230, 126, 34)),
    ("樱花粉", QColor(255, 118, 168)),
    ("柠檬黄", QColor(241, 196, 15)),
    ("薄荷青", QColor(26, 188, 156)),
    ("星空蓝", QColor(41, 128, 185)),
    ("玫瑰红", QColor(192, 57, 43)),
]


class ColorChip(QWidget):
    """单个颜色色块 —— 点击后发射信号传递颜色"""

    clicked = pyqtSignal(QColor)

    def __init__(self, name: str, color: QColor, parent=None):
        super().__init__(parent)
        self.color = color
        self.name = name
        self.setFixedSize(80, 100)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._update_style(False)

    def _update_style(self, hovered):
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        style = f"""
            ColorChip {{
                background-color: rgb({r}, {g}, {b});
                border-radius: 12px;
                border: 2px solid rgba(255,255,255,30);
            }}
        """
        if hovered:
            style += f"""
            ColorChip:hover {{
                border: 3px solid rgba(255,255,255,130);
                background-color: rgb({min(r+25,255)}, {min(g+25,255)}, {min(b+25,255)});
            }}
            """
        self.setStyleSheet(style)

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.color)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """绘制颜色名称文字"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.color))
        painter.drawRoundedRect(self.rect(), 12, 12)

        # 底部绘制名称
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = Qt.white if brightness < 140 else Qt.black

        painter.setPen(text_color)
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, 65, 0, -5), Qt.AlignCenter, self.name)


class Plugin(QWidget):
    name = "🎨 变色按钮"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("colorButtonPlugin")
        self._init_ui()

    def _init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(28)

        # ========== 顶部标题 ==========
        title = TitleLabel("🎨 变色按钮", self)
        desc = BodyLabel("点击下方的大按钮，它会随机变换颜色！你也可以从色板中挑选喜欢的颜色。", self)
        desc.setTextColor(QColor(96, 96, 96), QColor(208, 208, 208))
        main_layout.addWidget(title)
        main_layout.addWidget(desc)

        # ========== 中央大按钮区域 ==========
        center_layout = QHBoxLayout()
        center_layout.addStretch()

        self.color_btn = ColorButton(self)
        self.color_btn.color_changed.connect(self._update_color_info)
        center_layout.addWidget(self.color_btn)

        center_layout.addStretch()
        main_layout.addLayout(center_layout)

        # 按钮下方提示文字
        hint = BodyLabel("👆 点击圆形按钮变色  /  或从下方色板选择颜色", self)
        hint.setAlignment(Qt.AlignCenter)
        hint.setTextColor(QColor(140, 140, 140), QColor(140, 140, 140))
        main_layout.addWidget(hint)

        # ========== 当前颜色信息卡片 ==========
        info_card = CardWidget(self)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(24, 18, 24, 18)
        info_layout.setSpacing(8)

        info_header = StrongBodyLabel("📋 当前颜色信息", info_card)
        self.color_info = BodyLabel("RGB: (52, 152, 219)  |  #3498DB", info_card)
        self.color_info.setTextColor(QColor(96, 96, 96), QColor(208, 208, 208))

        info_layout.addWidget(info_header)
        info_layout.addWidget(self.color_info)
        main_layout.addWidget(info_card)

        # ========== 色板选择器 ==========
        palette_label = StrongBodyLabel("🎯 快速选择颜色", self)
        main_layout.addWidget(palette_label)

        palette_card = CardWidget(self)
        palette_layout = QVBoxLayout(palette_card)
        palette_layout.setContentsMargins(24, 18, 24, 18)
        palette_layout.setSpacing(12)

        # 两行色板布局
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        for i, (name, color) in enumerate(COLOR_PALETTES):
            chip = ColorChip(name, color, palette_card)
            chip.clicked.connect(self.apply_color)
            if i < 5:
                row1.addWidget(chip)
            else:
                row2.addWidget(chip)

        row1.addStretch()
        row2.addStretch()

        palette_layout.addLayout(row1)
        palette_layout.addLayout(row2)
        main_layout.addWidget(palette_card)

        # ========== 底部操作按钮 ==========
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        random_btn = PrimaryPushButton(FluentIcon.SYNC, "随机变色", self)
        random_btn.clicked.connect(self.color_btn.randomize_color)
        random_btn.setFixedWidth(160)
        btn_row.addWidget(random_btn)

        reset_btn = PrimaryPushButton(FluentIcon.CANCEL, "重置蓝色", self)
        reset_btn.clicked.connect(lambda: self.apply_color(QColor(52, 152, 219)))
        reset_btn.setFixedWidth(160)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        main_layout.addStretch()

    def apply_color(self, color: QColor):
        """应用选中的颜色到按钮"""
        self.color_btn.set_bg_color(color)

    def _update_color_info(self, color: QColor):
        """更新颜色信息显示"""
        r, g, b = color.red(), color.green(), color.blue()
        hex_str = f"#{r:02X}{g:02X}{b:02X}"
        self.color_info.setText(f"RGB: ({r}, {g}, {b})  |  {hex_str}")
