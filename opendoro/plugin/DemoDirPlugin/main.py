# coding:utf-8
import sys
import os
import markdown
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    ScrollArea, CardWidget, TitleLabel, SubtitleLabel, 
    BodyLabel, StrongBodyLabel, IconWidget, FluentIcon,
    TextEdit, isDarkTheme
)

# Robustly import the game logic from the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from game_2048 import Game2048
except ImportError:
    # Fallback if import fails (should not happen with sys.path fix)
    class Game2048(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            layout.addWidget(BodyLabel("Error loading 2048 game module."))

class Plugin(QWidget):
    name = "插件开发教程 & 2048"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout for the plugin
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Scroll Area to allow vertical scrolling
        self.scroll = ScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.main_layout.addWidget(self.scroll)
        
        # Container widget for the scroll area
        self.container = QWidget()
        self.container.setObjectName("container")
        self.scroll.setWidget(self.container)
        
        # Layout for the container
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(36, 36, 36, 36)
        self.content_layout.setSpacing(24)
        
        # --- Header Section ---
        self.add_header()
        
        # --- Section 1: Detailed Introduction ---
        self.add_intro_section()

        # --- Section 2: AI Simulation Process ---
        self.add_ai_simulation_section()
        
        # --- Section 3: 2048 Tutorial & Demo ---
        self.add_2048_tutorial()
        
        # Add stretch to bottom
        self.content_layout.addStretch()

    def add_header(self):
        """Adds the main title and description."""
        title = TitleLabel("DoroPet 插件开发实战", self.container)
        subtitle = BodyLabel(
            "深入了解插件系统，并通过一个完整的 2048 游戏示例学习如何开发。", 
            self.container
        )
        subtitle.setTextColor(QColor(96, 96, 96), QColor(208, 208, 208))
        
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(subtitle)

    def add_intro_section(self):
        """Adds the detailed introduction card."""
        card = CardWidget(self.container)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Icon and Title
        header_layout = QHBoxLayout()
        icon = IconWidget(FluentIcon.BOOK_SHELF, card)
        icon.setFixedSize(24, 24)
        title = SubtitleLabel("插件系统详解", card)
        header_layout.addWidget(icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Detailed content
        raw_content = (
            "DoroPet 的插件系统旨在提供灵活的扩展能力。以下是核心概念：\n\n"
            "1. **文件结构**：\n"
            "   - 简单插件：`plugin/my_tool.py`（单文件）。\n"
            "   - 复杂插件：`plugin/MyComplexPlugin/main.py`（目录形式，推荐）。\n"
            "   目录形式允许你将资源文件、辅助代码等组织在一起，更加整洁。\n\n"
            "2. **核心类**：\n"
            "   每个插件必须包含一个 `Plugin` 类，该类继承自 `PyQt5.QtWidgets.QWidget`。\n"
            "   该类是插件的入口，实例化时会直接嵌入到主程序的插件页面中。\n\n"
            "3. **元数据**：\n"
            "   在 `Plugin` 类中定义类属性 `name = '插件名称'`，该名称将显示在左侧导航栏中。\n\n"
            "4. **依赖库**：\n"
            "   你可以自由使用 `PyQt5` 和 `qfluentwidgets` 来构建美观的界面。\n"
            "   `qfluentwidgets` 提供了符合 Windows 11 风格的控件，如 `CardWidget`, `PrimaryPushButton` 等。"
        )
        
        # Convert Markdown to HTML
        html_content = markdown.markdown(raw_content)
        
        content = BodyLabel(html_content, card)
        content.setTextFormat(Qt.RichText)
        content.setWordWrap(True)
        
        layout.addLayout(header_layout)
        layout.addWidget(content)
        self.content_layout.addWidget(card)

    def add_ai_simulation_section(self):
        """Adds a simulated conversation showing how to use AI to create the plugin."""
        title = SubtitleLabel("AI 辅助开发演示", self.container)
        self.content_layout.addWidget(title)
        
        # Chat Container
        chat_card = CardWidget(self.container)
        chat_layout = QVBoxLayout(chat_card)
        chat_layout.setContentsMargins(24, 24, 24, 24)
        chat_layout.setSpacing(20)
        
        # Introduction text
        intro_text = BodyLabel("你可以像这样通过自然语言指令，让 AI 帮你生成代码：", chat_card)
        chat_layout.addWidget(intro_text)
        
        # User Message 1
        self.add_chat_bubble(chat_layout, "User", "帮我写一个 2048 游戏插件，使用 PyQt5 和 qfluentwidgets，界面要现代简洁。", True)
        
        # AI Message 1
        ai_response_1 = (
            "好的，已为您生成 2048 游戏的基础框架。包含 `Game2048` 类和基本的网格布局。\n"
            "我使用了 `CardWidget` 作为容器，并为每个数字方块设置了不同的颜色样式。"
        )
        self.add_chat_bubble(chat_layout, "AI Assistant", ai_response_1, False)
        
        # User Message 2
        self.add_chat_bubble(chat_layout, "User", "看起来不错，但是缺少键盘控制，而且我想加上一个记录分数的 Label。", True)
        
        # AI Message 2
        ai_response_2 = (
            "没问题！我已添加 `keyPressEvent` 来处理方向键和 WASD 输入。\n"
            "同时在顶部添加了一个 `StrongBodyLabel` 用于显示当前分数，并在游戏结束时弹出提示框。"
        )
        self.add_chat_bubble(chat_layout, "AI Assistant", ai_response_2, False)

        # Conclusion
        conclusion = BodyLabel("经过几轮对话，一个完整的 2048 游戏就完成了（如下所示）。", chat_card)
        conclusion.setTextColor(QColor(96, 96, 96), QColor(208, 208, 208))
        chat_layout.addWidget(conclusion)

        self.content_layout.addWidget(chat_card)

    def add_chat_bubble(self, layout, sender, text, is_user):
        """Helper to create a chat bubble style widget."""
        bubble_container = QWidget()
        bubble_layout = QHBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        
        # Avatar (Simple Icon)
        icon_type = FluentIcon.PEOPLE if is_user else FluentIcon.ROBOT
        icon = IconWidget(icon_type)
        icon.setFixedSize(32, 32)
        
        # Message Box
        message_box = QFrame()
        message_box.setObjectName("messageContainer_user" if is_user else "messageContainer_assistant")
        message_box.setAttribute(Qt.WA_StyledBackground, True)  # Ensure QSS background is painted

        msg_layout = QVBoxLayout(message_box)
        msg_layout.setContentsMargins(12, 12, 12, 12)
        
        sender_lbl = StrongBodyLabel(sender, message_box)
        content_lbl = BodyLabel(text, message_box)
        content_lbl.setWordWrap(True)

        msg_layout.addWidget(sender_lbl)
        msg_layout.addWidget(content_lbl)
        
        if is_user:
            bubble_layout.addStretch()
            bubble_layout.addWidget(message_box)
            bubble_layout.addWidget(icon)
        else:
            bubble_layout.addWidget(icon)
            bubble_layout.addWidget(message_box)
            bubble_layout.addStretch()
            
        layout.addWidget(bubble_container)

    def add_2048_tutorial(self):
        """Adds the 2048 game tutorial section."""
        title = SubtitleLabel("实战示例：2048 游戏", self.container)
        self.content_layout.addWidget(title)
        
        # --- Part 1: Source Code ---
        code_card = CardWidget(self.container)
        code_layout = QVBoxLayout(code_card)
        code_layout.setContentsMargins(24, 24, 24, 24)
        code_layout.setSpacing(12)
        
        code_header = StrongBodyLabel("1. 源代码 (game_2048.py)", code_card)
        code_desc = BodyLabel(
            "这是 2048 游戏的完整实现逻辑。它继承自 QWidget，并使用 QGridLayout 布局网格。", 
            code_card
        )
        
        # Read the source code
        source_code = ""
        try:
            with open(os.path.join(current_dir, 'game_2048.py'), 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            source_code = f"Error reading source code: {e}"

        code_view = TextEdit(code_card)
        code_view.setPlainText(source_code)
        code_view.setReadOnly(True)
        code_view.setFixedHeight(300) # Limit height, scrollable
        
        code_layout.addWidget(code_header)
        code_layout.addWidget(code_desc)
        code_layout.addWidget(code_view)
        
        self.content_layout.addWidget(code_card)

        # --- Part 2: Live Demo ---
        demo_card = CardWidget(self.container)
        demo_layout = QVBoxLayout(demo_card)
        demo_layout.setContentsMargins(24, 24, 24, 24)
        demo_layout.setSpacing(12)
        
        demo_header = StrongBodyLabel("2. 实际效果预览", demo_card)
        demo_desc = BodyLabel(
            "下面是上述代码的实际运行效果。点击游戏区域并使用键盘方向键或 WASD 开始游玩！", 
            demo_card
        )
        
        # Instantiate the game
        game_widget = Game2048()
        
        # Center the game widget
        game_container = QHBoxLayout()
        game_container.addStretch()
        game_container.addWidget(game_widget)
        game_container.addStretch()
        
        demo_layout.addWidget(demo_header)
        demo_layout.addWidget(demo_desc)
        demo_layout.addLayout(game_container)
        
        self.content_layout.addWidget(demo_card)
