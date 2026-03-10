import sys
import sqlite3
import datetime
import base64
import os
import tempfile
import uuid
import json
import html
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QDialog, QFormLayout, QFrame, QSizePolicy, QMenu, QAction,
                             QListWidgetItem, QToolButton, QGraphicsOpacityEffect, QFileDialog, QTextEdit, QTextBrowser)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize, QPropertyAnimation, QEasingCurve, QTimer, QUrl
from PyQt5.QtGui import QFont, QDesktopServices, QClipboard, QPixmap, QIcon, QPalette, QColor, QMovie, QImage, QTransform
import re
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from qfluentwidgets import (ListWidget, TextEdit, LineEdit, 
                            PrimaryPushButton, PushButton, ScrollArea, 
                            StrongBodyLabel, BodyLabel, FluentIcon, MessageBox, ComboBox,
                            ToolButton, CheckBox, isDarkTheme, themeColor, InfoBar, InfoBarPosition)

from src.core.database import ChatDatabase
from src.services.llm_service import LLMWorker, ImageGenerationWorker
from src.core.voice import VoiceAssistant
from src.core.tts import TTSManager
from src.core.skill_manager import SkillManager
from src.core.state_manager import StateManager, GenerationState, ConnectionState
from src.resource_utils import resource_path
from src.core.logger import logger
from src.ui.screenshot_tool import ScreenCaptureTool
from src.core.pet_constants import ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY, ATTR_NAMES

# ---------------------------------------------------------
# Part 3: UI Components
# ---------------------------------------------------------

class StatusBubble(QFrame):
    def __init__(self, text="正在处理...", parent=None):
        super().__init__(parent)
        self.setObjectName("statusBubble")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(10)
        
        # Container to center content
        container = QFrame()
        container.setObjectName("statusContainer")
        container.setAttribute(Qt.WA_StyledBackground, True)
        # Style for container
        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#f0f0f0"
        border_color = "#404040" if is_dark else "#e0e0e0"
        text_color = "#cccccc" if is_dark else "#666666"
        
        container.setStyleSheet(f"""
            #statusContainer {{
                background-color: {bg_color};
                border-radius: 14px;
                border: 1px solid {border_color};
            }}
        """)
        
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(12, 6, 12, 6)
        c_layout.setSpacing(8)

        # Icon
        self.icon_label = QLabel(container)
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setScaledContents(True)
        # Use a simple movie or rotate an icon
        self.icon_pixmap = FluentIcon.SYNC.icon().pixmap(16, 16)
        self.icon_label.setPixmap(self.icon_pixmap)
        
        # Text
        self.text_label = QLabel(text, container)
        self.text_label.setStyleSheet(f"color: {text_color}; font-size: 12px;")
        
        c_layout.addWidget(self.icon_label)
        c_layout.addWidget(self.text_label)
        
        layout.addStretch()
        layout.addWidget(container)
        layout.addStretch()
        
        # Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate_icon)
        self.angle = 0
        self.timer.start(50)

    def rotate_icon(self):
        self.angle = (self.angle + 10) % 360
        transform = QTransform().rotate(self.angle)
        rotated_pixmap = self.icon_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # Center crop to keep size consistent (rotation changes bounding rect)
        w, h = 16, 16
        x = (rotated_pixmap.width() - w) // 2
        y = (rotated_pixmap.height() - h) // 2
        self.icon_label.setPixmap(rotated_pixmap.copy(x, y, w, h))

    def update_text(self, text):
        self.text_label.setText(text)

class ThinkingBubble(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame(self)
        self.container.setObjectName("messageContainer_assistant") 
        self.container.setAttribute(Qt.WA_StyledBackground, True)
        
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 8, 12, 8)
        self.container_layout.setSpacing(10)
        
        # Text with animation
        self.lbl_text = QLabel("正在思考...", self.container)
        self.lbl_text.setObjectName("thinkingText")
        
        self.container_layout.addWidget(self.lbl_text)
        self.container_layout.addStretch()
        
        self.layout.addWidget(self.container, 0, Qt.AlignLeft)
        
        # Timer for dot animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_dots)
        self.timer.start(500)
        self.dot_count = 3
        
    def update_dots(self):
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.lbl_text.setText(f"正在思考{dots}")

class ThinkingWidget(QFrame):
    def __init__(self, thought_content, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        is_dark = isDarkTheme()
        bg_color = "#2d2d2d" if is_dark else "#f0f0f0"
        text_color = "#888888" if is_dark else "#666666"
        border_color = "#404040" if is_dark else "#e0e0e0"
        content_text_color = "#cccccc" if is_dark else "#333333"

        self.header_btn = PushButton(self)
        self.header_btn.setFixedHeight(28)
        self.header_btn.clicked.connect(self.toggle_content)
        self.header_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.header_btn.setText("思考过程")
        self.header_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
                color: {text_color};
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {"#3d3d3d" if is_dark else "#e5e5e5"};
            }}
        """)

        self.content_label = ChatTextEdit(thought_content, self)
        font = QFont("Microsoft YaHei")
        font.setPixelSize(12)
        self.content_label.setFont(font)
        self.content_label.setStyleSheet(f"""
            QTextEdit {{
                color: {content_text_color};
                font-size: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei';
                background-color: transparent;
                border: none;
            }}
        """)
        
        self.content_label.hide()

        self.layout.addWidget(self.header_btn)
        self.layout.addWidget(self.content_label)
        
    def toggle_content(self):
        if self.content_label.isVisible():
            self.content_label.hide()
            self.header_btn.setText("思考过程")
            # self.header_btn.setIcon(FluentIcon.CARE_DOWN_SOLID)
        else:
            self.content_label.show()
            self.header_btn.setText("思考过程")
            # self.header_btn.setIcon(FluentIcon.CARE_UP_SOLID)
        
        # Trigger layout update in parent
        self.updateGeometry()
        parent = self.parent()
        while parent:
            parent.updateGeometry()
            if hasattr(parent, 'adjust_height'):
                parent.adjust_height()
            parent = parent.parent()

class ToolExecutionWidget(QFrame):
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.tool_items = []
        self.tool_item_map = {}
        self.thinking_text = ""
        self._setup_ui()
    
    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)
        
        self.header_btn = PushButton(self)
        self.header_btn.setFixedHeight(28)
        self.header_btn.setObjectName("toolExecutionHeader")
        self.header_btn.clicked.connect(self.toggle_content)
        self.header_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.header_btn.setText("查看思考与工具")
        self.header_btn.setIcon(FluentIcon.PLAY)
        self.header_btn.setToolTip("点击查看思考与工具执行过程")
        
        self.content_frame = QFrame(self)
        self.content_frame.setObjectName("toolExecutionContent")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(15, 4, 8, 4)
        self.content_layout.setSpacing(8) # Increased spacing
        
        # Thinking area
        self.thinking_container = QFrame(self.content_frame)
        self.thinking_container.setObjectName("thinkingContainer")
        self.thinking_layout = QVBoxLayout(self.thinking_container)
        self.thinking_layout.setContentsMargins(10, 10, 10, 10)
        
        self.thinking_title = QLabel("思考过程", self.thinking_container)
        self.thinking_title.setObjectName("thinkingTitle")
        
        self.thinking_label = QLabel(self.thinking_container)
        self.thinking_label.setObjectName("thinkingLabel")
        self.thinking_label.setWordWrap(True)
        self.thinking_label.setTextFormat(Qt.MarkdownText)
        
        self.thinking_layout.addWidget(self.thinking_title)
        self.thinking_layout.addWidget(self.thinking_label)
        
        # Tool calls area
        self.tools_container = QFrame(self.content_frame)
        self.tools_container.setObjectName("toolsContainer")
        self.tools_layout = QVBoxLayout(self.tools_container)
        self.tools_layout.setContentsMargins(0, 0, 0, 0)
        self.tools_layout.setSpacing(4)
        
        self.tools_title = QLabel("工具调用", self.tools_container)
        self.tools_title.setObjectName("toolsTitle")
        self.tools_layout.addWidget(self.tools_title)
        
        self.content_layout.addWidget(self.thinking_container)
        self.content_layout.addWidget(self.tools_container)
        
        self.main_layout.addWidget(self.header_btn)
        self.main_layout.addWidget(self.content_frame)
        
        self.thinking_container.hide()
        self.tools_container.hide()
        self.content_frame.hide()

    def update_thinking(self, chunk):
        self.thinking_text += chunk
        self.thinking_label.setText(self.thinking_text)
        if self.thinking_text.strip():
            self.thinking_container.show()
            self._update_header()

    def set_thinking(self, text):
        self.thinking_text = text
        self.thinking_label.setText(self.thinking_text)
        if self.thinking_text.strip():
            self.thinking_container.show()
            self._update_header()
        else:
            self.thinking_container.hide()

    def _update_header(self):
        count = len(self.tool_items)
        has_thinking = bool(self.thinking_text.strip())
        
        text_parts = []
        if has_thinking:
            text_parts.append("思考过程")
        if count > 0:
            text_parts.append(f"{count} 个工具调用")
            
        if not text_parts:
            self.header_btn.setText("查看详情")
        else:
            self.header_btn.setText(" + ".join(text_parts))
    
    def _get_theme_colors(self):
        is_dark = isDarkTheme()
        return {
            "dark": is_dark,
            "bg": "#2a2a2a" if is_dark else "#f5f5f5",
            "border": "#404040" if is_dark else "#e0e0e0",
            "text": "#cccccc" if is_dark else "#333333",
            "text_dim": "#888888" if is_dark else "#666666",
            "success": "#4CAF50",
            "error": "#f44336",
            "running": "#2196F3",
            "skill_bg": "#1a3a2a" if is_dark else "#e8f5e9",
            "tool_bg": "#2a2a3a" if is_dark else "#e3f2fd",
        }
    
    def update_or_add_item(self, tool_name, tool_type, status, args=None, result=None):
        if tool_name in self.tool_item_map:
            self._update_tool_item(tool_name, status, result)
        else:
            self.add_tool_item(tool_name, tool_type, status, args, result)
    
    def _update_tool_item(self, tool_name, status, result=None):
        if tool_name not in self.tool_item_map:
            return
        
        item_data = self.tool_item_map[tool_name]
        colors = self._get_theme_colors()
        
        item_data["status"] = status
        
        status_icon_label = item_data.get("status_icon")
        if status_icon_label:
            icon = self._get_icon_for_status(status)
            pixmap = icon.icon().pixmap(14, 14)
            status_icon_label.setPixmap(pixmap)
        
        status_label = item_data.get("status_label")
        if status_label:
            status_label.setText(self._get_status_text(status))
            status_label.setProperty("running", False)
            status_label.setProperty("success", False)
            status_label.setProperty("error", False)
            if status == self.STATUS_RUNNING:
                status_label.setProperty("running", True)
            elif status == self.STATUS_SUCCESS:
                status_label.setProperty("success", True)
            elif status == self.STATUS_ERROR:
                status_label.setProperty("error", True)
        
        result_label = item_data.get("result_label")
        if result and result_label:
            result_label.setProperty("error", False)
            if status == self.STATUS_ERROR:
                result_label.setProperty("error", True)
            result_label.setText(f"结果: {self._truncate_text(result, 150)}")
            result_label.show()
        
        self._update_header()
    
    def _get_icon_for_status(self, status):
        if status == self.STATUS_RUNNING:
            return FluentIcon.SYNC
        elif status == self.STATUS_SUCCESS:
            return FluentIcon.ACCEPT
        else:
            return FluentIcon.CANCEL
    
    def add_tool_item(self, tool_name, tool_type, status, args=None, result=None):
        colors = self._get_theme_colors()
        
        item_frame = QFrame(self.content_frame)
        item_frame.setObjectName("toolItemFrame")
        item_frame.setProperty("toolType", tool_type)
        
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(8, 6, 8, 6)
        item_layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        
        status_icon = QLabel()
        status_icon.setFixedSize(14, 14)
        icon = self._get_icon_for_status(status)
        pixmap = icon.icon().pixmap(14, 14)
        status_icon.setPixmap(pixmap)
        header_layout.addWidget(status_icon)
        
        type_label = QLabel(f"[{tool_type.upper()}]" if tool_type == "skill" else "[TOOL]", item_frame)
        type_label.setObjectName("toolTypeLabel")
        header_layout.addWidget(type_label)
        
        name_label = QLabel(tool_name, item_frame)
        name_label.setObjectName("toolNameLabel")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        status_label = QLabel(self._get_status_text(status), item_frame)
        status_label.setObjectName("toolStatusLabel")
        if status == self.STATUS_RUNNING:
            status_label.setProperty("running", True)
        elif status == self.STATUS_SUCCESS:
            status_label.setProperty("success", True)
        elif status == self.STATUS_ERROR:
            status_label.setProperty("error", True)
        header_layout.addWidget(status_label)
        
        item_layout.addLayout(header_layout)
        
        if args:
            args_label = QLabel(f"参数: {self._truncate_text(args, 100)}", item_frame)
            args_label.setObjectName("toolArgsLabel")
            args_label.setWordWrap(True)
            item_layout.addWidget(args_label)
        
        result_label = QLabel(item_frame)
        result_label.setObjectName("toolResultLabel")
        result_label.setWordWrap(True)
        if result:
            if status == self.STATUS_ERROR:
                result_label.setProperty("error", True)
            result_label.setText(f"结果: {self._truncate_text(result, 150)}")
            result_label.show()
        else:
            result_label.hide()
        item_layout.addWidget(result_label)
        
        self.tools_layout.addWidget(item_frame)
        self.tools_container.show()
        
        item_data = {
            "frame": item_frame,
            "status_icon": status_icon,
            "status_label": status_label,
            "result_label": result_label,
            "status": status,
            "tool_type": tool_type
        }
        self.tool_items.append(item_data)
        self.tool_item_map[tool_name] = item_data
        
        self._update_header()
        self.content_frame.show()
        
        return item_frame
    
    def _get_status_text(self, status):
        return {
            self.STATUS_RUNNING: "执行中...",
            self.STATUS_SUCCESS: "完成",
            self.STATUS_ERROR: "失败"
        }.get(status, "未知")
    
    def _get_status_color_key(self, status):
        return {
            self.STATUS_RUNNING: "running",
            self.STATUS_SUCCESS: "success",
            self.STATUS_ERROR: "error"
        }.get(status, "text_dim")
    
    def _truncate_text(self, text, max_len):
        if not text:
            return ""
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = json.dumps(parsed, ensure_ascii=False, indent=None)
        except:
            pass
        return text[:max_len] + "..." if len(text) > max_len else text
    
    def _update_header(self):
        running_count = 0
        success_count = 0
        error_count = 0
        
        for name, data in self.tool_item_map.items():
            status = data.get("status")
            if status == self.STATUS_RUNNING:
                running_count += 1
            elif status == self.STATUS_SUCCESS:
                success_count += 1
            elif status == self.STATUS_ERROR:
                error_count += 1
        
        total_count = len(self.tool_item_map)
        has_thinking = bool(self.thinking_text.strip())
        
        text_parts = []
        if has_thinking:
            text_parts.append("思考过程")
        if total_count > 0:
            if running_count > 0:
                text_parts.append(f"{running_count} 个工具执行中")
            else:
                text_parts.append(f"{total_count} 个工具调用")
            
        if not text_parts:
            self.header_btn.setText("查看详情")
            self.header_btn.setIcon(FluentIcon.PLAY)
        else:
            self.header_btn.setText(" + ".join(text_parts))
            if running_count > 0:
                self.header_btn.setIcon(FluentIcon.SYNC)
            else:
                self.header_btn.setIcon(FluentIcon.COMPLETED)
        
        self.header_btn.adjustSize()
        self.header_btn.updateGeometry()
    
    def toggle_content(self):
        if self.content_frame.isVisible():
            self.content_frame.hide()
            # self.header_btn.setIcon(FluentIcon.CARE_RIGHT_SOLID)
        else:
            self.content_frame.show()
            # self.header_btn.setIcon(FluentIcon.CARE_DOWN_SOLID)
        
        # Trigger layout update in parent
        self.updateGeometry()
        parent = self.parent()
        while parent:
            parent.updateGeometry()
            if hasattr(parent, 'adjust_height'):
                parent.adjust_height()
            parent = parent.parent()


class ChatTextEdit(QTextBrowser):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(False) # Handle manually
        self.anchorClicked.connect(self.on_anchor_clicked)
        
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setContentsMargins(2, 2, 2, 2)
        self.document().setDocumentMargin(0)
        self.setObjectName("chatContent")
        self.setContextMenuPolicy(Qt.NoContextMenu)
        
        self.code_blocks = [] # Store raw code for copying
        
        # Force transparency via Palette and Viewport attributes
        # This is critical to allow the parent QFrame background to show through
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        self.setPalette(palette)
        
        self.viewport().setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Explicitly set transparent background in stylesheet
        # self.setStyleSheet("background: transparent; background-color: transparent;")
        
        font = QFont("Microsoft YaHei")
        font.setPixelSize(14)
        self.setFont(font)
        
        self.set_markdown_content(text)
        self.document().contentsChanged.connect(self.adjust_height)

    def setSource(self, url):
        # Override default navigation for custom schemes
        if url.scheme() == 'codecopy' or 'codecopy' in url.toString():
            return
        super().setSource(url)

    def on_anchor_clicked(self, url):
        url_str = url.toString()
        scheme = url.scheme()
        
        # Robust handling for custom scheme
        if scheme == 'codecopy' or 'codecopy' in url_str:
            try:
                # Extract index using regex to handle various URL formats (codecopy://1, codecopy:1, etc.)
                import re
                match = re.search(r'codecopy.*?(\d+)', url_str)
                if match:
                    idx = int(match.group(1))
                    if 0 <= idx < len(self.code_blocks):
                        code = self.code_blocks[idx]
                        QApplication.clipboard().setText(code)
                        
                        # Show feedback (InfoBar)
                        InfoBar.success(
                            title='复制成功',
                            content="代码已复制到剪贴板",
                            orient=Qt.Horizontal,
                            isClosable=True,
                            position=InfoBarPosition.TOP_RIGHT,
                            duration=2000,
                            parent=self.window()
                        )
                else:
                    logger.warning(f"Could not parse code block index from URL: {url_str}")
            except Exception as e:
                logger.error(f"Copy error: {e}")
        else:
            QDesktopServices.openUrl(url)

    def render_markdown(self, text):
        is_dark = isDarkTheme()
        
        # Modern Theme Colors
        if is_dark:
            style_name = 'one-dark' # Try one-dark
            # Fallback check
            try: 
                from pygments.styles import get_style_by_name
                get_style_by_name(style_name)
            except: 
                style_name = 'monokai'
                
            bg_color = "#282c34"      # One Dark bg
            header_bg = "#21252b"     # One Dark header
            border_color = "#181a1f"  
            text_color = "#abb2bf"    # One Dark fg
        else:
            style_name = 'xcode'      # Xcode is clean
            try:
                from pygments.styles import get_style_by_name
                get_style_by_name(style_name)
            except:
                style_name = 'default'
                
            bg_color = "#f6f8fa"      # GitHub-like light bg
            header_bg = "#e1e4e8"     
            border_color = "#d1d5da"
            text_color = "#24292e"

        # Configure extensions
        # Remove codehilite to handle highlighting manually
        extensions = ['fenced_code', 'tables']
        
        try:
            markdown_html = markdown.markdown(text, extensions=extensions)
            
            # Use Table layout (proven to work better in PyQt)
            def replace_block(match):
                lang = match.group('lang')
                code_content = match.group('code')
                
                # Unescape HTML entities in code because we need raw code for highlighting
                clean_code = html.unescape(code_content)
                
                # Store and get index for copy function
                self.code_blocks.append(clean_code)
                block_idx = len(self.code_blocks) - 1
                
                # Highlight code manually
                try:
                    if lang:
                        lexer = get_lexer_by_name(lang)
                    else:
                        lexer = guess_lexer(clean_code)
                except:
                    try:
                        lexer = get_lexer_by_name('text')
                    except:
                        # Fallback if text lexer fails for some reason
                        from pygments.lexers.special import TextLexer
                        lexer = TextLexer()
                    
                formatter = HtmlFormatter(style=style_name, noclasses=True)
                highlighted_html = highlight(clean_code, lexer, formatter)
                
                # Extract pre content from highlighted HTML
                # highlighted_html is usually <div ...><pre ...>...</pre></div>
                start_idx = highlighted_html.find('<pre')
                end_idx = highlighted_html.rfind('</pre>') + 6
                
                if start_idx != -1:
                    pre_content = highlighted_html[start_idx:end_idx]
                else:
                    pre_content = f'<pre>{code_content}</pre>'

                # Clean pre tag style and force our background
                # Replace <pre ...> with our styled pre
                # We overwrite margin/padding/bg to match our container
                # NOTE: Qt QTextBrowser handles padding on TD better than on PRE
                pre_content = re.sub(r'<pre[^>]*>', 
                    f'<pre style="margin: 0; padding: 0; background-color: {bg_color}; color: {text_color}; white-space: pre-wrap; font-family: \'Consolas\', monospace;">', 
                    pre_content, count=1)

                copy_btn_color = "#999999"
                if is_dark: copy_btn_color = "#bbbbbb"
                
                # Language display label
                lang_display = lang if lang else "Code"

                table_html = (
                    f'<table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 15px; border: 1px solid {border_color}; border-radius: 6px;">'
                    f'<tr><td style="background-color: {header_bg}; padding: 8px 12px; border-bottom: 1px solid {border_color}; border-top-left-radius: 6px; border-top-right-radius: 6px;">'
                    f'<table width="100%" cellspacing="0" cellpadding="0" border="0"><tr>'
                    f'<td style="border:none; background:transparent;" align="left">'
                    f'<span style="color: {text_color}; font-family: sans-serif; font-size: 12px; font-weight: bold;">{lang_display}</span>'
                    f'</td>'
                    f'<td style="border:none; background:transparent;" align="right">'
                    f'<a href="codecopy:///{block_idx}" style="text-decoration: none; color: {copy_btn_color}; font-family: sans-serif; font-size: 12px;">复制代码</a>'
                    f'</td>'
                    f'</tr></table>'
                    f'</td></tr>'
                    # Add padding to the TD containing the code
                    f'<tr><td style="background-color: {bg_color}; padding: 15px; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px;">'
                    f'{pre_content}'
                    f'</td></tr>'
                    f'</table>'
                )
                return table_html

            # Match <pre><code class="language-python">...</code></pre> or <pre><code>...</code></pre>
            pattern = r'<pre><code(?: class="language-(?P<lang>[\w-]+)")?>(?P<code>.*?)</code></pre>'
            markdown_html = re.sub(pattern, replace_block, markdown_html, flags=re.DOTALL)
            
        except Exception as e:
            logger.error(f"Markdown rendering error: {e}")
            markdown_html = f"<pre>{text}</pre>"

        custom_css = f"""
        <style>
            body {{
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 14px;
                color: {text_color};
            }}
            a {{ color: #40a9ff; }}
        </style>
        """
        
        return custom_css + markdown_html

    _theme_update_timer = None
    
    def update_theme(self):
        if hasattr(self, 'raw_markdown') and self.raw_markdown:
            if self._theme_update_timer is not None:
                self._theme_update_timer.stop()
            self._theme_update_timer = QTimer()
            self._theme_update_timer.setSingleShot(True)
            self._theme_update_timer.timeout.connect(self._do_theme_update)
            self._theme_update_timer.start(50)
    
    def _do_theme_update(self):
        if hasattr(self, 'raw_markdown') and self.raw_markdown:
            self.set_markdown_content(self.raw_markdown)

    def set_markdown_content(self, text):
        self.raw_markdown = text
        self.code_blocks = [] # Reset code blocks
        try:
            self.setHtml(self.render_markdown(text))
            
            # Force calculation of ideal width to hint container
            self.document().setTextWidth(-1) 
            ideal_width = self.document().idealWidth()
            
            # Use FontMetrics to calculate approximate width of plain text
            # This serves as a fallback/baseline to prevent narrow collapses
            fm = self.fontMetrics()
            # Clean text for width calculation (simple approximation)
            plain_text = re.sub(r'<[^>]+>', '', text)
            text_width = fm.width(plain_text)
            
            # Use the larger of the two, plus padding
            # Cap at a reasonable max width (e.g., 800) to prevent excessive width requests,
            # but allow it to be wide enough for the content.
            # The layout will constrain it to the window width anyway.
            final_width = max(ideal_width, text_width) + 40
            self.custom_width_hint = final_width
            
            if self.width() > 50:
                 self.document().setTextWidth(self.width())
            
            self.updateGeometry()
        except Exception as e:
            logger.error(f"Error setting markdown content: {e}")
            self.setPlainText(text)

    def sizeHint(self):
        s = super().sizeHint()
        if hasattr(self, 'custom_width_hint') and self.custom_width_hint > 0:
             return QSize(int(self.custom_width_hint), s.height())
        
        # Improve auto-width calculation for bubbles
        try:
            # Calculate text width to prompt layout to expand
            text = self.toPlainText()
            fm = self.fontMetrics()
            
            # Simple heuristic: find max line width
            max_line_width = 0
            # Check a sample of lines if too many to avoid performance hit
            lines = text.split('\n')
            for line in lines[:50]: 
                w = fm.boundingRect(line).width()
                if w > max_line_width:
                    max_line_width = w
            
            # Add padding
            target_width = max_line_width + 40
            
            # Cap width to ensure readability and wrapping
            # (e.g. don't let it be 2000px wide on a huge screen)
            target_width = min(target_width, 800)
            
            # Ensure minimum width
            target_width = max(target_width, 100)
            
            return QSize(int(target_width), s.height())
        except:
            return s

    def adjust_height(self):
        width = self.viewport().width()
        if width <= 0:
            width = self.width()
            
        if width > 50: # Only adjust if width is reasonable to prevent narrow collapse
            self.document().setTextWidth(width)
            
        doc_height = self.document().size().height()
        # Add a small buffer and ensure minimum height
        target_height = int(doc_height + 10)
        if target_height < 30: target_height = 30
        
        if self.height() != target_height:
            self.setFixedHeight(target_height)
        
        # Notify layout that size hint (width) might have changed due to content change
        self.updateGeometry()
        
    def resizeEvent(self, event):
        self.adjust_height()
        super().resizeEvent(event)

class ClickableImageLabel(QLabel):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击查看原图")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                os.startfile(self.image_path)
            except Exception as e:
                logger.error(f"Error opening image: {e}")
        super().mousePressEvent(event)

class BranchContainer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("branchContainer")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def add_bubble(self, bubble):
        self.layout.addWidget(bubble)

    def update_theme(self):
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if hasattr(widget, 'update_theme'):
                widget.update_theme()

class CodeBlockWidget(QFrame):
    def __init__(self, code, lang="", parent=None):
        super().__init__(parent)
        self.code = code
        self.lang = lang
        self.setObjectName("codeBlockWidget")
        self.is_expanded = True
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header
        self.header = QFrame(self)
        self.header.setObjectName("codeHeader")
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(12, 6, 12, 6)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.mousePressEvent = self.on_header_clicked
        
        self.lang_label = QLabel(self.lang if self.lang else "Code", self.header)
        self.lang_label.setObjectName("codeLangLabel")
        
        self.copy_btn = ToolButton(FluentIcon.COPY, self.header)
        self.copy_btn.setFixedSize(24, 24)
        self.copy_btn.setIconSize(QSize(14, 14))
        self.copy_btn.setToolTip("复制")
        self.copy_btn.clicked.connect(self.copy_code)
        
        self.toggle_btn = ToolButton(FluentIcon.CARE_UP_SOLID, self.header)
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setIconSize(QSize(12, 12))
        self.toggle_btn.setToolTip("折叠")
        self.toggle_btn.clicked.connect(self.toggle_expand)
        
        self.header_layout.addWidget(self.lang_label)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.copy_btn)
        self.header_layout.addWidget(self.toggle_btn)
        
        self.layout.addWidget(self.header)
        
        # Content
        self.code_view = QTextBrowser(self)
        self.code_view.setObjectName("codeContent")
        self.code_view.setFrameShape(QFrame.NoFrame)
        self.code_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.code_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.code_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.code_view.setOpenExternalLinks(False)
        
        # Set font
        font = QFont("Consolas")
        font.setPixelSize(13)
        font.setStyleHint(QFont.Monospace)
        self.code_view.setFont(font)
        
        self.layout.addWidget(self.code_view)
        
        self.render_code()
        
        self.code_view.document().contentsChanged.connect(self.adjust_height)
    
    _theme_update_timer = None

    def on_header_clicked(self, event):
        self.toggle_expand()
        
    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.code_view.setVisible(self.is_expanded)
        
        if self.is_expanded:
            self.toggle_btn.setIcon(FluentIcon.CARE_UP_SOLID)
            self.toggle_btn.setToolTip("折叠")
            self.header.setProperty("collapsed", False)
        else:
            self.toggle_btn.setIcon(FluentIcon.CARE_DOWN_SOLID)
            self.toggle_btn.setToolTip("展开")
            self.header.setProperty("collapsed", True)
            
        self.header.style().unpolish(self.header)
        self.header.style().polish(self.header)
        
    def render_code(self):
        is_dark = isDarkTheme()
        
        if is_dark:
            style_name = 'one-dark'
            try: 
                from pygments.styles import get_style_by_name
                get_style_by_name(style_name)
            except: 
                style_name = 'monokai'
        else:
            style_name = 'xcode'
            try:
                from pygments.styles import get_style_by_name
                get_style_by_name(style_name)
            except:
                style_name = 'default'
                
        try:
            if self.lang:
                lexer = get_lexer_by_name(self.lang)
            else:
                lexer = guess_lexer(self.code)
        except:
            from pygments.lexers.special import TextLexer
            lexer = TextLexer()
            
        formatter = HtmlFormatter(style=style_name, noclasses=True)
        highlighted_html = highlight(self.code, lexer, formatter)
        
        # Extract pre content to avoid extra margins from div/pre
        # highlighted_html is usually <div ...><pre ...>...</pre></div>
        start_idx = highlighted_html.find('<pre')
        end_idx = highlighted_html.rfind('</pre>') + 6
        if start_idx != -1:
            pre_content = highlighted_html[start_idx:end_idx]
        else:
            pre_content = f'<pre>{self.code}</pre>'
            
        # Add custom style to pre
        # We need to set font family explicitly here too
        text_color = "#abb2bf" if is_dark else "#24292e"
        pre_content = re.sub(r'<pre[^>]*>', 
            f'<pre style="margin: 0; padding: 12px; color: {text_color}; white-space: pre-wrap; font-family: \'Consolas\', monospace;">', 
            pre_content, count=1)
            
        self.code_view.setHtml(pre_content)
        
    def adjust_height(self):
        # Update text width to match viewport for correct height calculation with wrapping
        width = self.code_view.viewport().width()
        if width > 0:
            self.code_view.document().setTextWidth(width)
            
        doc_height = self.code_view.document().size().height()
        self.code_view.setFixedHeight(int(doc_height + 15))
        
    def resizeEvent(self, event):
        self.adjust_height()
        super().resizeEvent(event)

    def copy_code(self):
        QApplication.clipboard().setText(self.code)
        InfoBar.success(
            title='已复制',
            content='代码已复制到剪贴板',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )
        
    def update_theme(self):
        if self._theme_update_timer is not None:
            self._theme_update_timer.stop()
        self._theme_update_timer = QTimer()
        self._theme_update_timer.setSingleShot(True)
        self._theme_update_timer.timeout.connect(self.render_code)
        self._theme_update_timer.start(30)

    def update_code(self, code, lang=""):
        if self.code == code and self.lang == lang:
            return
        self.code = code
        self.lang = lang
        self.lang_label.setText(self.lang if self.lang else "Code")
        self.render_code()

class MessageBubble(QFrame):
    delete_requested = pyqtSignal(int)
    regenerate_requested = pyqtSignal(int)
    speak_requested = pyqtSignal(int, str)
    switch_branch_requested = pyqtSignal(int)
    branch_conversation_requested = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, str, str, object)
    
    def __init__(self, role, content, msg_id, parent_window=None, images=None, sibling_ids=None, current_index=0, is_active=True, model=None):
        super().__init__()
        self.role = role.lower() if role else "user"
        self.content = content
        self.msg_id = msg_id
        self.parent_window = parent_window
        self.images = images or []
        self.sibling_ids = sibling_ids or []
        self.current_index = current_index
        self.is_active = is_active
        self.model = model
        self.content_widgets = []
        
        # self.setFrameShape(QFrame.NoFrame)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Container for style
        self.container = QFrame(self)
        self.container.setObjectName(f"messageContainer_{self.role}")
        
        # Add active/inactive style differentiation if needed
        if not self.is_active:
             self.container.setObjectName(f"messageContainer_{self.role}_inactive")
             # We might need to add this ID to QSS or just style it here
             # For now, let's just use opacity or border to distinguish
             # self.setGraphicsEffect(QGraphicsOpacityEffect(self).setOpacity(0.7)) # This affects whole bubble including text
             pass

        # Ensure the container paints its background for QSS
        self.container.setAttribute(Qt.WA_StyledBackground, True)
        # self.container.setAutoFillBackground(True)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        # 允许容器根据内容自动拉伸高度，宽度由布局控制
        self.container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.container.setMinimumWidth(80) # Prevent extremely narrow bubbles on init
        
        if role == "user":
            self.layout.addWidget(self.container, 0, Qt.AlignRight)
        else:
            self.layout.addWidget(self.container, 0, Qt.AlignLeft)

        # --- Display Images ---
        if self.images:
            # Container for images (no scroll area, let it expand)
            img_content = QWidget()
            img_content.setObjectName("messageImageContainer")
            # img_content.setStyleSheet("background-color: transparent;")
            img_layout = QVBoxLayout(img_content)
            img_layout.setContentsMargins(0, 0, 0, 0)
            img_layout.setSpacing(5)
            
            for img_path in self.images:
                lbl_img = ClickableImageLabel(img_path, img_content)
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # Scale logic: max width 400
                    if pixmap.width() > 400:
                        pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
                    lbl_img.setPixmap(pixmap)
                    img_layout.addWidget(lbl_img)
                else:
                    lbl_err = QLabel(f"[图片无法加载: {img_path}]", img_content)
                    img_layout.addWidget(lbl_err)
            
            self.container_layout.addWidget(img_content)

        # Parse content using MessageParser for more robust block separation
        from src.core.message_parser import MessageParser, ContentType
        
        # We handle <think> tags specifically for the ThinkingWidget
        thinking_text, display_text = MessageParser.extract_thinking(content)
        
        if thinking_text:
            self.thinking_widget = ThinkingWidget(thinking_text, self.container)
            self.container_layout.addWidget(self.thinking_widget)

        # Parse display content into blocks
        blocks = MessageParser._parse_display_content(display_text)
        
        for block in blocks:
            if block.is_code():
                code_widget = CodeBlockWidget(block.content, block.language or "", self.container)
                self.container_layout.addWidget(code_widget)
                self.content_widgets.append(code_widget)
            else:
                text_widget = ChatTextEdit(block.content, self.container)
                self.container_layout.addWidget(text_widget)
                self.content_widgets.append(text_widget)
                
        # --- Action Widget (Hidden opacity by default, but occupies space) ---
        self.action_widget = QWidget(self)
        self.action_layout = QHBoxLayout(self.action_widget)
        self.action_layout.setContentsMargins(0, 5, 0, 0)
        self.action_layout.setSpacing(5)
        
        # Action buttons will be styled via QSS using ID "chatActionButton"
        
        # Copy Button
        self.btn_copy = ToolButton(FluentIcon.COPY, self.action_widget)
        self.btn_copy.setFixedSize(20, 20)
        self.btn_copy.setToolTip("复制")
        self.btn_copy.setObjectName("chatActionButton")
        self.btn_copy.setIconSize(QSize(14, 14))
        self.btn_copy.clicked.connect(self.copy_content)
        self.action_layout.addWidget(self.btn_copy)
        
        # Delete Button
        self.btn_delete = ToolButton(FluentIcon.DELETE, self.action_widget)
        self.btn_delete.setFixedSize(20, 20)
        self.btn_delete.setToolTip("删除")
        self.btn_delete.setObjectName("chatActionButton")
        self.btn_delete.setIconSize(QSize(14, 14))
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.msg_id))
        self.action_layout.addWidget(self.btn_delete)
        
        if role == "assistant":
            # Regenerate Button
            self.btn_regen = ToolButton(FluentIcon.SYNC, self.action_widget)
            self.btn_regen.setFixedSize(20, 20)
            self.btn_regen.setToolTip("重新生成")
            self.btn_regen.setObjectName("chatActionButton")
            self.btn_regen.setIconSize(QSize(14, 14))
            self.btn_regen.clicked.connect(lambda: self.regenerate_requested.emit(self.msg_id))
            self.action_layout.addWidget(self.btn_regen)

            # TTS Read Button
            self.btn_read = ToolButton(FluentIcon.PLAY, self.action_widget)
            self.btn_read.setFixedSize(20, 20)
            self.btn_read.setToolTip("朗读")
            self.btn_read.setObjectName("chatActionButton")
            self.btn_read.setIconSize(QSize(14, 14))
            self.btn_read.clicked.connect(lambda: self.speak_requested.emit(self.msg_id, self.content))
            self.action_layout.addWidget(self.btn_read)

            # Branch Button (Plus) - Now in the same row
            self.btn_branch = ToolButton(FluentIcon.ADD, self.action_widget)
            self.btn_branch.setFixedSize(20, 20)
            self.btn_branch.setToolTip("生成新分支")
            self.btn_branch.setObjectName("chatActionButton")
            self.btn_branch.setIconSize(QSize(14, 14))
            self.btn_branch.clicked.connect(self.on_branch_clicked)
            self.action_layout.addWidget(self.btn_branch)

            # Switch/Select Button (if not active or to show active state)
        # If multiple siblings are shown, we need a way to indicate which one is "selected" or allow switching
        if not self.is_active:
            self.btn_switch = ToolButton(FluentIcon.ACCEPT, self.action_widget) # Checkmark to select
            self.btn_switch.setFixedSize(20, 20)
            self.btn_switch.setToolTip("切换到此回复")
            self.btn_switch.setObjectName("chatActionButton")
            self.btn_switch.setIconSize(QSize(14, 14))
            self.btn_switch.clicked.connect(self.on_switch_clicked)
            self.action_layout.addWidget(self.btn_switch)

        # Show Model Name if available
        if self.model:
            # Clean up model name if it's too long or has path
            display_model = self.model
            if "/" in display_model:
                display_model = display_model.split("/")[-1]
            
            lbl_model = QLabel(display_model, self.action_widget)
            lbl_model.setObjectName("chatModelLabel")
            lbl_model.setStyleSheet("QLabel { color: #808080; font-size: 10px; margin-right: 8px; font-family: 'Segoe UI', sans-serif; }")
            lbl_model.setToolTip(f"生成模型: {self.model}")
            # Add at the beginning (leftmost)
            self.action_layout.insertWidget(0, lbl_model)

        self.action_layout.addStretch()
        
        # Add action widget to the MAIN layout (outside the colored bubble)
        # This will make it appear below the bubble
        if role == "user":
            self.layout.addWidget(self.action_widget, 0, Qt.AlignRight)
        else:
            self.layout.addWidget(self.action_widget, 0, Qt.AlignLeft)
            
        # Opacity Effect for smooth fade or visibility toggle without layout shift
        self.opacity_effect = QGraphicsOpacityEffect(self.action_widget)
        self.opacity_effect.setOpacity(0.0) # Initially invisible
        self.action_widget.setGraphicsEffect(self.opacity_effect)
        # We DO NOT hide() the widget, so it reserves space.
        
        # Force style update to apply QSS based on properties
        # self.container.style().unpolish(self.container)
        # self.container.style().polish(self.container)
        # self.container.update()

    def on_switch_clicked(self):
        self.switch_branch_requested.emit(self.msg_id)

    def on_branch_clicked(self):
        self.branch_conversation_requested.emit(self.msg_id)

    def copy_content(self):
        """复制内容到剪贴板并提供视觉反馈"""
        QApplication.clipboard().setText(self.content)
        self.btn_copy.setIcon(FluentIcon.ACCEPT)
        self.btn_copy.setToolTip("已复制")
        QTimer.singleShot(1500, self.reset_copy_icon)

    def reset_copy_icon(self):
        self.btn_copy.setIcon(FluentIcon.COPY)
        self.btn_copy.setToolTip("复制")

    def resizeEvent(self, event):
        # Limit container max width based on role
        if self.parent():
            # Calculate max width ratio based on role
            ratio = 0.5 if self.role == "user" else 0.8
            max_w = int(self.width() * ratio)
            
            if self.container.maximumWidth() != max_w:
                self.container.setMaximumWidth(max_w)
        super().resizeEvent(event)

    def enterEvent(self, event):
        self.opacity_effect.setOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.opacity_effect.setOpacity(0.0)
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(self.msg_id, self.role, self.content, event.globalPos())

    def update_theme(self):
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'update_theme'):
                    widget.update_theme()

    def update_content(self, content):
        try:
            self.content = content
            
            # Use MessageParser for more robust parsing
            from src.core.message_parser import MessageParser
            
            # Handle streaming thinking content
            # Pattern that matches <think> and optional content until end of string
            thinking_text, display_text = MessageParser.extract_thinking(content)
            
            if thinking_text:
                if hasattr(self, 'thinking_widget') and self.thinking_widget:
                    if self.thinking_widget.content_label.toPlainText() != thinking_text:
                        self.thinking_widget.content_label.setPlainText(thinking_text)
                        # Scroll to bottom of thinking if it's visible and streaming
                        if self.thinking_widget.content_label.isVisible():
                             sb = self.thinking_widget.content_label.verticalScrollBar()
                             sb.setValue(sb.maximum())
                else:
                    # Create thinking widget if it doesn't exist
                    self.thinking_widget = ThinkingWidget(thinking_text, self.container)
                    self.container_layout.insertWidget(0, self.thinking_widget)
            
            # Parse display blocks
            # Handle unclosed code blocks during streaming
            display_text_for_parse = display_text
            if '```' in display_text:
                # Count triple backticks
                count = display_text.count('```')
                if count % 2 != 0:
                    # Unclosed code block
                    display_text_for_parse += '\n```'
            
            blocks = MessageParser._parse_display_content(display_text_for_parse)
            new_parts = []
            for b in blocks:
                if b.is_code():
                    new_parts.append(f"```{(b.language or '')}\n{b.content}```")
                else:
                    new_parts.append(b.content)
            
            # Check for reuse
            can_reuse = False
            if hasattr(self, 'content_widgets') and len(self.content_widgets) == len(blocks):
                can_reuse = True
                for i, widget in enumerate(self.content_widgets):
                    block = blocks[i]
                    is_code_widget = isinstance(widget, CodeBlockWidget)
                    if block.is_code() != is_code_widget:
                        can_reuse = False
                        break
            
            if can_reuse:
                for i, widget in enumerate(self.content_widgets):
                    block = blocks[i]
                    if isinstance(widget, CodeBlockWidget):
                        widget.update_code(block.content, block.language or "")
                    else:
                        if getattr(widget, 'raw_markdown', '') != block.content:
                            widget.set_markdown_content(block.content)
            else:
                # Remove old content widgets
                if hasattr(self, 'content_widgets'):
                    for widget in self.content_widgets:
                        self.container_layout.removeWidget(widget)
                        widget.deleteLater()
                    self.content_widgets.clear()
                else:
                    self.content_widgets = []

                # Re-create widgets
                for block in blocks:
                    if block.is_code():
                        widget = CodeBlockWidget(block.content, block.language or "", self.container)
                        self.container_layout.addWidget(widget)
                        self.content_widgets.append(widget)
                    else:
                        widget = ChatTextEdit(block.content, self.container)
                        self.container_layout.addWidget(widget)
                        self.content_widgets.append(widget)
            
            # Trigger resize to ensure wrapping
            if self.parent():
                max_w = int(self.width() * 0.85)
                self.container.setMaximumWidth(max_w)
            
            # Notify layout about content change
            self.container.updateGeometry()
            self.updateGeometry()
        except Exception as e:
            logger.error(f"Error updating content: {e}")


class PasteableTextEdit(TextEdit):
    imagePasted = pyqtSignal(str)

    def canInsertFromMimeData(self, source):
        if source.hasImage():
            return True
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
                        return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image:
                # Handle QVariant wrapper if present
                try:
                    if hasattr(image, 'value'): 
                        image = image.value()
                except:
                    pass
                
                # Convert QPixmap to QImage if necessary
                if isinstance(image, QPixmap):
                    image = image.toImage()
                
                if isinstance(image, QImage):
                    try:
                        temp_dir = os.path.join(tempfile.gettempdir(), "doropet_images")
                        if not os.path.exists(temp_dir):
                            os.makedirs(temp_dir)
                        
                        filename = f"pasted_image_{uuid.uuid4().hex}.png"
                        file_path = os.path.join(temp_dir, filename)
                        image.save(file_path, "PNG")
                        self.imagePasted.emit(file_path)
                        return
                    except Exception as e:
                        logger.error(f"Error saving pasted image: {e}")
        
        if source.hasUrls():
            has_images = False
            for url in source.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
                        self.imagePasted.emit(path)
                        has_images = True
            
            if has_images:
                return

        super().insertFromMimeData(source)

class ChatInterface(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatInterface")
        
        self.db = db if db else ChatDatabase()
        self.current_session_id = None
        self.worker_session_id = None
        self.current_system_prompt = ""
        self.streaming_bubble = None
        self.thinking_bubble = None
        self.status_bubble = None
        self.streaming_content = ""
        self.streaming_buffer = "" # Buffer for streaming content
        self.selected_images = []
        self.branching_parent_id = None
        self.live2d_widget = None
        
        self.state_manager = StateManager()
        self._connect_state_manager_signals()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_streaming_display)
        
        self._stop_timer = QTimer(self)
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self._check_stop_timeout)
        
        self.init_ui()
        self.load_sessions_list()

        # Auto-select last active session
        self.select_last_active_session()

        # Initialize Voice Assistant
        self.voice_assistant = VoiceAssistant(self.db, self)
        self.voice_assistant.wake_detected.connect(self.on_voice_wake_detected)
        self.voice_assistant.text_recognized.connect(self.on_voice_text_recognized)
        self.voice_assistant.listening_status.connect(self.on_listening_status_changed)
        self.voice_assistant.error_occurred.connect(self.on_voice_error)
        
        # Auto-start voice assistant REMOVED for performance
        # self.voice_assistant.start()

        # Initialize TTS Manager
        self.tts_manager = TTSManager(self.db)
        self.tts_manager.playback_started.connect(self.on_tts_started)
        self.tts_manager.playback_stopped.connect(self.on_tts_stopped)
        self.tts_manager.playback_error.connect(self.on_tts_error)

        self.update_voice_ui_visibility()
    
    def _connect_state_manager_signals(self):
        self.state_manager.generation_state_changed.connect(self._on_generation_state_changed)
    
    def _on_generation_state_changed(self, state: GenerationState):
        if state in (GenerationState.STREAMING, GenerationState.TOOL_CALLING, GenerationState.THINKING, GenerationState.PREPARING):
            self._is_generating = True
            self.btn_send.setIcon(FluentIcon.CANCEL)
            self.btn_send.setText("停止")
        else:
            self._is_generating = False
            self.btn_send.setIcon(FluentIcon.SEND)
            self.btn_send.setText("发送")

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget

    def update_voice_ui_visibility(self):
        settings = self.db.get_voice_settings()
        if settings:
            is_enabled = bool(settings[0])
            self.btn_voice.setVisible(is_enabled)
            
            if not is_enabled and self.voice_assistant.isRunning():
                self.toggle_voice_assistant()
        else:
            self.btn_voice.setVisible(False)

    def select_last_active_session(self):
        last_session = self.db.get_last_active_session()
        if last_session:
            last_session_id = last_session[0]
            # Find in list
            for i in range(self.session_list.count()):
                item = self.session_list.item(i)
                if item.data(Qt.UserRole) == last_session_id:
                    self.session_list.setCurrentRow(i)
                    self.on_session_selected(item)
                    return

        # Fallback: if list not empty but specific session not found
        if self.session_list.count() > 0:
            self.session_list.setCurrentRow(0)
            self.on_session_selected(self.session_list.item(0))

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 左侧：会话列表 ---
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        btn_new_chat = PushButton(FluentIcon.ADD, "新建会话", self.left_panel)
        btn_new_chat.clicked.connect(self.create_new_session)
        
        self.session_list = ListWidget(self.left_panel)
        self.session_list.itemClicked.connect(self.on_session_selected)
        self.session_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self.show_session_context_menu)

        left_layout.addWidget(btn_new_chat)
        left_layout.addWidget(self.session_list)
        
        # --- 右侧：聊天区域 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. 顶部角色设置
        prompt_layout = QHBoxLayout()
        
        # 侧边栏切换按钮
        self.btn_toggle_sidebar = ToolButton(FluentIcon.MENU, right_panel)
        self.btn_toggle_sidebar.setToolTip("显示/隐藏会话列表")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        
        self.persona_combo = ComboBox(right_panel)
        self.persona_combo.setPlaceholderText("选择一个人格...")
        self.persona_prompts = []  # Store prompts separately to avoid itemData issues
        self.load_personas_to_combo()
        self.persona_combo.currentIndexChanged[int].connect(self.on_persona_changed)
        
        btn_refresh = PushButton(FluentIcon.SYNC, "刷新", right_panel)
        btn_refresh.setFixedWidth(80)
        btn_refresh.clicked.connect(self.load_personas_to_combo)
        
        prompt_layout.addWidget(self.btn_toggle_sidebar)
        prompt_layout.addWidget(self.persona_combo, 1)
        prompt_layout.addWidget(btn_refresh)
        
        # 2. 中间：滚动聊天区
        self.scroll_area = ScrollArea(right_panel)
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.chat_content_widget = QWidget()
        self.chat_content_widget.setObjectName("chatContentWidget")
        # self.chat_content_widget.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content_widget)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch()
        
        self.scroll_area.setWidget(self.chat_content_widget)
        
        # 3. 底部：输入区
        # 整体采用垂直布局：上方是文本框，下方是工具栏
        input_container_layout = QVBoxLayout()
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(10)
        
        # 图片预览区
        self.image_preview_widget = QWidget(right_panel)
        self.image_preview_layout = QHBoxLayout(self.image_preview_widget)
        self.image_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.image_preview_layout.setAlignment(Qt.AlignLeft)
        self.image_preview_widget.hide()
        input_container_layout.addWidget(self.image_preview_widget)

        # 上方：文本输入框
        self.input_text = PasteableTextEdit(right_panel)
        self.input_text.imagePasted.connect(self.on_image_pasted)
        self.input_text.setFixedHeight(80)
        self.input_text.setPlaceholderText("请输入内容...")
        
        # 下方：工具栏（模型选择 + 发送按钮）
        bottom_toolbar_layout = QHBoxLayout()
        bottom_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        bottom_toolbar_layout.setSpacing(10)

        # 图片选择按钮
        self.btn_image = ToolButton(FluentIcon.PHOTO, self)
        self.btn_image.setToolTip("添加图片")
        self.btn_image.clicked.connect(self.select_image)
        bottom_toolbar_layout.addWidget(self.btn_image)

        # 截图按钮
        self.btn_screenshot = ToolButton(FluentIcon.CUT, self)
        self.btn_screenshot.setToolTip("屏幕截图")
        self.btn_screenshot.clicked.connect(self.take_screenshot)
        bottom_toolbar_layout.addWidget(self.btn_screenshot)

        # 语音助手状态/开关按钮
        self.btn_voice = ToolButton(FluentIcon.MICROPHONE, self)
        # self.btn_voice.setFixedSize(32, 32)
        # self.btn_voice.setIconSize(QSize(16, 16))
        self.btn_voice.setToolTip("语音助手已关闭 (点击开启)")
        # self.btn_voice.setStyleSheet("ToolButton { opacity: 0.5; }")
        self.btn_voice.clicked.connect(self.toggle_voice_assistant)
        bottom_toolbar_layout.addWidget(self.btn_voice)
        
        # 左侧占位符，把控件挤到右边
        bottom_toolbar_layout.addStretch(1)

        # Agent/工具能力菜单按钮
        self.btn_agent_tools = ToolButton(FluentIcon.IOT, self)
        self.btn_agent_tools.setToolTip("配置 AI 能力 (联网、画图、编程)")
        self.btn_agent_tools.clicked.connect(self.show_tools_menu)
        bottom_toolbar_layout.addWidget(self.btn_agent_tools)
        
        # 初始化工具状态
        self.init_tools_menu()

        # 上下文开关
        self.chk_no_context = CheckBox("不带上下文", right_panel)
        self.chk_no_context.setToolTip("开启后，AI将不会收到之前的对话历史，仅根据当前输入和系统提示词进行回复")
        bottom_toolbar_layout.addWidget(self.chk_no_context)

        # 模型选择下拉框
        self.model_combo = ComboBox(right_panel)
        self.model_combo.setPlaceholderText("选择模型")
        self.model_combo.setFixedWidth(150) # 固定宽度
        self.load_models_to_combo()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        
        # 发送/停止按钮
        self._is_generating = False
        self.btn_send = PrimaryPushButton(FluentIcon.SEND, "发送", right_panel)
        self.btn_send.setFixedSize(100, 32)
        self.btn_send.clicked.connect(self.on_send_button_clicked)
        
        bottom_toolbar_layout.addWidget(self.model_combo)
        bottom_toolbar_layout.addWidget(self.btn_send)
        
        # 将文本框和工具栏加入主输入容器
        input_container_layout.addWidget(self.input_text)
        input_container_layout.addLayout(bottom_toolbar_layout)

        right_layout.addLayout(prompt_layout)
        right_layout.addWidget(self.scroll_area)
        right_layout.addLayout(input_container_layout)

        # 布局
        self.left_panel.setFixedWidth(250)
        main_layout.addWidget(self.left_panel)
        
        # Add Separator
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.VLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setFixedWidth(1)
        self.separator.setObjectName("chatSeparator")
        # sep_color handled in QSS
        main_layout.addWidget(self.separator)
        
        main_layout.addWidget(right_panel)

    def showEvent(self, event):
        self.load_models_to_combo()
        super().showEvent(event)

    def toggle_sidebar(self):
        width = self.left_panel.width()
        
        if width > 0:
            end_value = 0
            self.left_panel.setMinimumWidth(0)
            self.left_panel.setMaximumWidth(250)
        else:
            end_value = 250
            self.left_panel.setVisible(True)
            self.left_panel.setMinimumWidth(0)
            self.left_panel.setMaximumWidth(0)

        self.animation = QPropertyAnimation(self.left_panel, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(width)
        self.animation.setEndValue(end_value)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        if end_value == 0:
            self.animation.finished.connect(lambda: self.left_panel.setVisible(False))
        else:
            # When showing, after animation restore fixed width if desired, or keep as max
            self.animation.finished.connect(lambda: self.left_panel.setFixedWidth(250))
            
        self.animation.start()

    def load_sessions_list(self):
        self.session_list.clear()
        sessions = self.db.get_sessions()
        for sess in sessions:
            title = sess[1]
            if len(title) > 12:
                title = title[:11] + "…"
            item = QListWidgetItem(title, self.session_list) 
            item.setData(Qt.UserRole, sess[0])
            item.setData(Qt.UserRole + 1, sess[2])
            item.setToolTip(sess[1])
            self.session_list.addItem(item)

    def create_new_session(self):
        session_id = self.db.create_session()
        self.load_sessions_list()
        self.session_list.setCurrentRow(0)
        self.on_session_selected(self.session_list.item(0))
        self.input_text.setFocus()

    def on_session_selected(self, item):
        if not item: return
        
        if self._is_generating:
            MessageBox("提示", "正在生成消息，请等待完成或停止后再切换会话。", self).exec_()
            return
        
        self.current_session_id = item.data(Qt.UserRole)
        self.current_system_prompt = item.data(Qt.UserRole + 1)
        self.load_chat_history()
        
        # 尝试匹配当前 Prompt
        found = False
        # Use simple string matching or index matching
        for i, prompt in enumerate(self.persona_prompts):
            if prompt == self.current_system_prompt:
                self.persona_combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            self.persona_combo.setCurrentIndex(-1)

    def load_personas_to_combo(self):
        self.persona_combo.blockSignals(True)
        self.persona_combo.clear()
        self.persona_prompts = []
        self.persona_doro_tools = []
        self.persona_live2d_models = []
        
        self.persona_combo.addItem("默认助手")
        self.persona_prompts.append("You are a helpful assistant.")
        self.persona_doro_tools.append(False)
        self.persona_live2d_models.append("")
        
        personas = self.db.get_personas()
        for p in personas:
            self.persona_combo.addItem(p[1])
            self.persona_prompts.append(p[3])
            self.persona_doro_tools.append(bool(p[5]) if len(p) > 5 else False)
            self.persona_live2d_models.append(p[7] if len(p) > 7 else "")
            
        self.persona_combo.blockSignals(False)

    def on_persona_changed(self, index):
        if index < 0 or index >= len(self.persona_prompts):
            return
            
        new_prompt = self.persona_prompts[index]
        self.current_system_prompt = new_prompt
        print(f"DEBUG: Persona switched to index {index}. Prompt: {new_prompt[:50]}...")
        
        if self.current_session_id:
            self.db.update_session_prompt(self.current_session_id, new_prompt)
            curr_item = self.session_list.currentItem()
            if curr_item:
                curr_item.setData(Qt.UserRole + 1, new_prompt)
        
        if hasattr(self, 'persona_live2d_models') and index < len(self.persona_live2d_models):
            model_path = self.persona_live2d_models[index]
            if model_path and hasattr(self, 'live2d_widget') and self.live2d_widget:
                self.live2d_widget.reload_model(model_path)

    def _get_current_persona_name(self) -> str:
        """获取当前选择的人格名称"""
        if hasattr(self, 'persona_combo') and self.persona_combo.currentIndex() >= 0:
            return self.persona_combo.currentText()
        return ""
    
    def _is_doro_tools_enabled(self) -> bool:
        """检查当前人格是否启用了 Doro 工具"""
        if hasattr(self, 'persona_combo') and self.persona_combo.currentIndex() >= 0:
            index = self.persona_combo.currentIndex()
            if hasattr(self, 'persona_doro_tools') and index < len(self.persona_doro_tools):
                return self.persona_doro_tools[index]
        return False

    def _get_pet_status_context(self) -> str:
        """获取桌宠属性状态上下文（仅启用Doro工具的人格生效）"""
        if not hasattr(self, 'live2d_widget') or not self.live2d_widget:
            return ""
        
        if not hasattr(self.live2d_widget, 'attr_manager'):
            return ""
        
        if not self._is_doro_tools_enabled():
            return ""
        
        attr_manager = self.live2d_widget.attr_manager
        contexts = []
        
        for attr_name in [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]:
            status = attr_manager.get_status(attr_name)
            value = attr_manager.get_attribute(attr_name)
            chinese_name = ATTR_NAMES.get(attr_name, attr_name)
            
            if status in ["critical", "warning"]:
                if status == "critical":
                    contexts.append(f"{chinese_name}过低({value:.0f}%)，处于危急状态")
                elif status == "warning":
                    contexts.append(f"{chinese_name}偏低({value:.0f}%)")
        
        if contexts:
            return "\n【桌宠状态】" + "；".join(contexts) + "。请根据此状态调整你的回复风格。"
        return ""

    def on_model_changed(self, index):
        if index < 0: return
        data = self.model_combo.itemData(index)
        if data:
            # data: (api_key, base_url, model_name, is_thinking, is_visual, type)
            # Save user preference
            settings = QSettings("MyApp", "LLMClient")
            # data[2] is model_name, data[1] is base_url
            settings.setValue("last_model_name", data[2])
            settings.setValue("last_base_url", data[1])

    def init_tools_menu(self):
        self.tool_actions = {}
        self.tool_states = {
            "search": True,
            "image": True,
            "coding": True,
            "file": True
        }
        
        settings = QSettings("DoroPet", "Settings")
        self.tool_states["search"] = settings.value("tool_search_enabled", True, type=bool)
        self.tool_states["image"] = settings.value("tool_image_enabled", True, type=bool)
        self.tool_states["coding"] = settings.value("tool_coding_enabled", True, type=bool)
        self.tool_states["file"] = settings.value("tool_file_enabled", True, type=bool)
        
        self.skill_states = {}
        skill_mgr = SkillManager()
        for skill_name in skill_mgr.skills.keys():
            self.skill_states[skill_name] = settings.value(f"skill_{skill_name}_enabled", True, type=bool)
        
        self.update_tools_button_icon()

    def show_tools_menu(self):
        menu = QMenu(self)
        
        local_tools_label = QAction("── 本地工具 ──", self)
        local_tools_label.setEnabled(False)
        menu.addAction(local_tools_label)
        
        action_search = QAction("联网搜索", self, checkable=True)
        action_search.setChecked(self.tool_states["search"])
        action_search.triggered.connect(lambda checked: self.toggle_tool("search", checked))
        menu.addAction(action_search)
        
        action_image = QAction("画图能力", self, checkable=True)
        action_image.setChecked(self.tool_states["image"])
        action_image.triggered.connect(lambda checked: self.toggle_tool("image", checked))
        menu.addAction(action_image)
        
        action_coding = QAction("代码执行", self, checkable=True)
        action_coding.setChecked(self.tool_states["coding"])
        action_coding.triggered.connect(lambda checked: self.toggle_tool("coding", checked))
        menu.addAction(action_coding)
        
        action_file = QAction("文件操作", self, checkable=True)
        action_file.setChecked(self.tool_states["file"])
        action_file.triggered.connect(lambda checked: self.toggle_tool("file", checked))
        menu.addAction(action_file)
        
        skill_mgr = SkillManager()
        settings = QSettings("DoroPet", "Settings")
        
        for skill_name in self.skill_states:
            self.skill_states[skill_name] = settings.value(f"skill_{skill_name}_enabled", True, type=bool)
        
        if skill_mgr.skills:
            menu.addSeparator()
            skills_label = QAction("── 技能 (Skills) ──", self)
            skills_label.setEnabled(False)
            menu.addAction(skills_label)
            
            for skill_name, skill in sorted(skill_mgr.skills.items()):
                is_enabled = self.skill_states.get(skill_name, True)
                action = QAction(f"{skill_name}", self, checkable=True)
                action.setChecked(is_enabled)
                action.setToolTip(skill.description[:50] + "..." if len(skill.description) > 50 else skill.description)
                action.triggered.connect(lambda checked, name=skill_name: self.toggle_skill(name, checked))
                menu.addAction(action)
        
        menu.exec_(self.btn_agent_tools.mapToGlobal(self.btn_agent_tools.rect().bottomLeft()))

    def toggle_tool(self, tool_key, checked):
        self.tool_states[tool_key] = checked
        settings = QSettings("DoroPet", "Settings")
        settings.setValue(f"tool_{tool_key}_enabled", checked)
        self.update_tools_button_icon()
    
    def toggle_skill(self, skill_name, checked):
        self.skill_states[skill_name] = checked
        settings = QSettings("DoroPet", "Settings")
        settings.setValue(f"skill_{skill_name}_enabled", checked)
        self.update_tools_button_icon()
        
    def update_tools_button_icon(self):
        active_count = sum(1 for v in self.tool_states.values() if v)
        active_count += sum(1 for v in self.skill_states.values() if v)
        if active_count > 0:
            self.btn_agent_tools.setIcon(FluentIcon.IOT)
            tool_names = []
            if self.tool_states["search"]: tool_names.append("搜索")
            if self.tool_states["image"]: tool_names.append("画图")
            if self.tool_states["coding"]: tool_names.append("代码")
            if self.tool_states["file"]: tool_names.append("文件")
            active_skills = [k for k, v in self.skill_states.items() if v]
            if active_skills:
                tool_names.append(f"{len(active_skills)}个技能")
            self.btn_agent_tools.setToolTip(f"已启用: {', '.join(tool_names)}")
        else:
            self.btn_agent_tools.setIcon(FluentIcon.CANCEL)
            self.btn_agent_tools.setToolTip("所有工具已禁用")

    def get_enabled_plugins(self):
        enabled = [k for k, v in self.tool_states.items() if v]
        enabled += [f"skill:{k}" for k, v in self.skill_states.items() if v]
        return enabled

    def load_models_to_combo(self):
        current_data = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        
        # Load settings for preference
        settings = QSettings("MyApp", "LLMClient")
        last_model = settings.value("last_model_name", "")
        last_base_url = settings.value("last_base_url", "")
        
        # 1. Load LLM Models
        models = self.db.get_models()
        # models: id, name, provider, api_key, base_url, model_name, is_active, is_visual, is_thinking
        
        active_index = 0
        target_index = -1
        pref_index = -1
        current_count = 0

        for i, m in enumerate(models):
            # Ensure we handle cases where tuple might be shorter (backward compatibility)
            is_visual = 0
            if len(m) > 7:
                is_visual = m[7]

            is_thinking = 0
            if len(m) > 8:
                is_thinking = m[8]
                
            # Add "llm" type flag
            data = (m[3], m[4], m[5], is_thinking, is_visual, "llm") # api_key, base_url, model_name, is_thinking, is_visual, type
            self.model_combo.addItem(m[1], userData=data)
            
            if m[6] == 1: # is_active
                active_index = current_count
            
            # Check preference (match model name and base_url)
            if last_model and last_base_url and m[5] == last_model and m[4] == last_base_url:
                pref_index = current_count
            
            # Compare basic fields for selection stability
            if current_data and len(current_data) >= 3 and data[:3] == current_data[:3]:
                target_index = current_count
                
            current_count += 1
            
        # 2. Load Image Generation Models
        image_models = self.db.get_image_models()
        # Image model: id, name, provider, base_url, api_key, model_name, is_active
        for m in image_models:
            # Note: Swap api_key and base_url to match LLM structure for first 3 elements
            # m[3]=base_url, m[4]=api_key
            data = (m[4], m[3], m[5], 0, 0, "image")
            
            self.model_combo.addItem(f"{m[1]} (Image)", userData=data)
            
            # Only set active if no LLM was active (priority to LLM)
            if m[6] == 1 and active_index == 0:
                 active_index = current_count
            
            # Check preference
            if last_model and last_base_url and m[5] == last_model and m[3] == last_base_url:
                pref_index = current_count

            if current_data and len(current_data) >= 3 and data[:3] == current_data[:3]:
                target_index = current_count
                
            current_count += 1
        
        if target_index != -1:
            self.model_combo.setCurrentIndex(target_index)
        elif pref_index != -1:
            self.model_combo.setCurrentIndex(pref_index)
        elif current_count > 0:
            self.model_combo.setCurrentIndex(active_index)
        else:
            # Fallback if no models in DB
            self.model_combo.addItem("Default (OpenAI)")
            # settings already loaded above
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")
            # Default fallback data: thinking=0, visual=0, type="llm"
            self.model_combo.setItemData(0, (api_key, base_url, model, 0, 0, "llm"))
            
        self.model_combo.blockSignals(False)



    def export_chat_history(self, session_id, session_title):
        messages = self.db.get_messages(session_id)
        if not messages:
             MessageBox("提示", "该会话没有消息记录", self).exec_()
             return

        content_lines = []
        content_lines.append(f"会话: {session_title}")
        content_lines.append(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_lines.append("=" * 50)
        content_lines.append("")

        for msg in messages:
            # msg structure: (id, role, content, images, parent_id, sibling_ids, current_index)
            role = msg[1]
            content = msg[2]
            
            role_display = "User" if role == "user" else "AI"
            content_lines.append(f"[{role_display}]:")
            content_lines.append(content)
            content_lines.append("-" * 30)
            content_lines.append("")

        full_text = "\n".join(content_lines)

        # Clean filename
        safe_title = "".join([c for c in session_title if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_title: safe_title = "chat_export"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出聊天记录", f"{safe_title}.txt", "Text Files (*.txt)")
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                MessageBox("成功", f"已导出到: {file_path}", self).exec_()
            except Exception as e:
                logger.error(f"Export error: {e}")
                MessageBox("错误", f"导出失败: {e}", self).exec_()

    def show_session_context_menu(self, pos):
        item = self.session_list.itemAt(pos)
        if not item: return
        
        menu = QMenu()
        export_action = menu.addAction("导出聊天记录")
        delete_action = menu.addAction("删除会话")
        action = menu.exec_(self.session_list.mapToGlobal(pos))
        
        sess_id = item.data(Qt.UserRole)

        if action == export_action:
            self.export_chat_history(sess_id, item.text())
        elif action == delete_action:
            if self._is_generating and sess_id == self.worker_session_id:
                MessageBox("提示", "该会话正在生成消息，请等待完成或停止后再删除。", self).exec_()
                return
            self.db.delete_session(sess_id)
            self.load_sessions_list()
            if self.session_list.count() == 0:
                self.create_new_session()
            else:
                self.clear_chat_area()
                self.current_session_id = None

    def clear_chat_area(self, keep_widgets=None):
        keep_widgets = keep_widgets or []
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                if widget in keep_widgets:
                    pass
                else:
                    widget.deleteLater()
        self.chat_layout.addStretch()
        
        self.streaming_bubble = None
        self.thinking_bubble = None
        self.status_bubble = None
        self.streaming_content = ""
        self.streaming_buffer = ""
        self.tool_execution_widget = None 

    def load_chat_history(self, keep_widgets=None):
        self.clear_chat_area(keep_widgets)
        if not self.current_session_id: return
        
        item = self.chat_layout.takeAt(0) 
        if item: del item

        messages = self.db.get_messages(self.current_session_id)
        for msg_data in messages:
            # Unpack based on length to support legacy code if needed, but db returns 10 items now
            if len(msg_data) >= 10:
                msg_id, role, content, images, parent_id, sibling_ids, current_index, model, reasoning, tool_calls = msg_data[:10]
            elif len(msg_data) >= 9:
                msg_id, role, content, images, parent_id, sibling_ids, current_index, model, reasoning = msg_data[:9]
                tool_calls = None
            elif len(msg_data) >= 8:
                msg_id, role, content, images, parent_id, sibling_ids, current_index, model = msg_data[:8]
                reasoning = None
                tool_calls = None
            elif len(msg_data) >= 7:
                msg_id, role, content, images, parent_id, sibling_ids, current_index = msg_data[:7]
                model = None
                reasoning = None
                tool_calls = None
            else:
                # Fallback
                msg_id, role, content, images = msg_data[:4]
                sibling_ids = []
                current_index = 0
                model = None
                reasoning = None
                tool_calls = None
            
            # Check for multiple branches (siblings)
            if len(sibling_ids) > 1:
                # Fetch all siblings to display side-by-side
                siblings_data = self.db.get_messages_by_ids(sibling_ids)
                
                # Container for side-by-side bubbles
                container = BranchContainer()
                
                for s_row in siblings_data:
                    # Unpack: id, role, content, images, parent_id, is_active, timestamp, model, reasoning, tool_calls
                    if len(s_row) >= 10:
                        s_id, s_role, s_content, s_images_str, s_parent_id, s_is_active, s_ts, s_model, s_reasoning, s_tool_calls = s_row[:10]
                    elif len(s_row) >= 9:
                        s_id, s_role, s_content, s_images_str, s_parent_id, s_is_active, s_ts, s_model, s_reasoning = s_row[:9]
                        s_tool_calls = None
                    elif len(s_row) >= 8:
                        s_id, s_role, s_content, s_images_str, s_parent_id, s_is_active, s_ts, s_model = s_row[:8]
                        s_reasoning = None
                        s_tool_calls = None
                    else:
                        s_id, s_role, s_content, s_images_str, s_parent_id, s_is_active, s_ts = s_row[:7]
                        s_model = None
                        s_reasoning = None
                        s_tool_calls = None
                    
                    # Parse images for sibling
                    s_images = []
                    if s_images_str:
                         try:
                             s_images = json.loads(s_images_str)
                         except:
                             pass
                    
                    # Calculate index
                    try:
                        s_index = sibling_ids.index(s_id)
                    except:
                        s_index = 0
                    
                    # Create reasoning/tools widget if needed
                    if s_role == "assistant" and (s_reasoning or s_tool_calls):
                        exec_widget = ToolExecutionWidget(self)
                        if s_reasoning:
                            exec_widget.set_thinking(s_reasoning)
                        if s_tool_calls:
                            import json
                            if isinstance(s_tool_calls, str):
                                try:
                                    s_tool_calls = json.loads(s_tool_calls)
                                except:
                                    s_tool_calls = []
                            for tc in s_tool_calls:
                                exec_widget.add_tool_item(tc['name'], tc['type'], tc['status'], tc['args'], tc.get('result'))
                        container.add_bubble(exec_widget)

                    # Create bubble
                    # Note: s_is_active is 1 or 0 from DB
                    bubble = MessageBubble(s_role, s_content, s_id, self, s_images, sibling_ids, s_index, is_active=(s_is_active==1), model=s_model)
                    bubble.delete_requested.connect(self.delete_message)
                    bubble.regenerate_requested.connect(self.regenerate_message)
                    bubble.speak_requested.connect(self.speak_message)
                    bubble.switch_branch_requested.connect(self.switch_branch)
                    bubble.branch_conversation_requested.connect(self.branch_conversation)
                    bubble.context_menu_requested.connect(self._on_bubble_context_menu)
                    container.add_bubble(bubble)
                
                self.chat_layout.addWidget(container)
            else:
                self.add_message_to_ui(role, content, msg_id, images, sibling_ids, current_index, model=model, reasoning=reasoning, tool_calls=tool_calls)

        
        self.chat_layout.addStretch()
        
        QApplication.processEvents()
        self.scroll_to_bottom()

    # --- Voice Assistant Handlers ---
    def on_voice_wake_detected(self):
        """Handle 'Hey Doro' wake-up detected"""
        logger.info("Voice wake word 'Hey Doro' detected.")
        self.btn_voice.setIcon(FluentIcon.MICROPHONE)
        # Change color to indicate listening (Blue background)
        # self.btn_voice.setStyleSheet("background-color: rgba(0, 120, 212, 0.2); border-radius: 4px; border: 1px solid rgba(0, 120, 212, 0.3);")
        self.input_text.setPlaceholderText("正在听...")
        self.btn_voice.setToolTip("正在聆听...")

    def on_voice_text_recognized(self, text):
        """Handle recognized text"""
        if not text: return
        logger.info(f"Voice text recognized: {text}")
        
        # Reset UI
        self.on_listening_status_changed("idle")
        
        # Set text and send
        self.input_text.setPlainText(text)
        self.send_message()

    def on_listening_status_changed(self, status):
        """Update UI based on listening status"""
        # style = self.get_voice_button_style(status)
        # self.btn_voice.setStyleSheet(style)

        if status == "idle":
            self.input_text.setPlaceholderText("请输入内容...")
            self.btn_voice.setToolTip("语音唤醒: Hey Doro")
        elif status == "listening":
            self.input_text.setPlaceholderText("正在听...")

    def get_voice_button_style(self, state):
        is_dark = isDarkTheme()
        
        if not self.voice_assistant.isRunning():
            return "ToolButton { opacity: 0.5; }"
            
        if state == "listening":
            # Accent color for listening
            if is_dark:
                return "ToolButton { background-color: rgba(60, 150, 255, 0.3); border-radius: 4px; border: 1px solid rgba(60, 150, 255, 0.5); }"
            else:
                return "ToolButton { background-color: rgba(0, 120, 212, 0.3); border-radius: 4px; border: 1px solid rgba(0, 120, 212, 0.5); }"
            
        if state == "idle":
            # Subtle background to show it's active/ready
            if is_dark:
                return "ToolButton { background-color: rgba(0, 0, 0, 0.1); border-radius: 4px; }"
            else:
                return "ToolButton { background-color: rgba(0, 120, 212, 0.1); border-radius: 4px; }"
                
        return ""

    _theme_update_timer = None
    _pending_theme_widgets = []
    
    def update_theme(self):
        if self._theme_update_timer is not None:
            self._theme_update_timer.stop()
        
        self._pending_theme_widgets = []
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'update_theme'):
                    self._pending_theme_widgets.append(widget)
        
        self._theme_update_timer = QTimer()
        self._theme_update_timer.setSingleShot(True)
        self._theme_update_timer.timeout.connect(self._process_theme_updates)
        self._theme_update_timer.start(10)
    
    def _process_theme_updates(self):
        if self._pending_theme_widgets:
            widget = self._pending_theme_widgets.pop(0)
            widget.update_theme()
            if self._pending_theme_widgets:
                QTimer.singleShot(5, self._process_theme_updates)

    def on_voice_error(self, error_msg):
        """Handle voice errors"""
        logger.error(f"Voice Error: {error_msg}")
        self.btn_voice.setToolTip(f"语音错误: {error_msg}")
        # Optionally disable the button or show an error icon

    def toggle_voice_assistant(self):
        """Toggle voice assistant on/off or restart"""
        if self.voice_assistant.isRunning():
            logger.info("Stopping voice assistant.")
            self.voice_assistant.stop()
            # self.btn_voice.setIcon(FluentIcon.MICROPHONE) 
            self.btn_voice.setToolTip("语音助手已关闭 (点击开启)")
            # self.btn_voice.setStyleSheet("ToolButton { opacity: 0.5; }")
        else:
            logger.info("Starting voice assistant.")
            self.voice_assistant.start()
            # self.btn_voice.setIcon(FluentIcon.MICROPHONE)
            self.btn_voice.setToolTip("语音唤醒: Hey Doro")
            # Initial active style
            # self.btn_voice.setStyleSheet(self.get_voice_button_style("idle"))
    
    # --- TTS Handlers ---
    def speak_message(self, msg_id, content):
        if not hasattr(self, 'tts_manager') or not self.tts_manager:
            return
        
        try:
            clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            if self.tts_manager.current_msg_id == msg_id:
                 self.tts_manager.speak(msg_id, clean_content)
                 return

            if clean_content:
                 self.tts_manager.speak(msg_id, clean_content)
        except Exception as e:
            logger.error(f"Error in speak_message: {e}")

    def on_tts_started(self, msg_id):
        try:
            bubble = self.get_bubble_by_id(msg_id)
            if bubble and hasattr(bubble, 'btn_read'):
                bubble.btn_read.setIcon(FluentIcon.PAUSE) 
                bubble.btn_read.setToolTip("停止播放")
        except Exception as e:
            logger.error(f"Error in on_tts_started: {e}")

    def on_tts_stopped(self, msg_id):
        try:
            bubble = self.get_bubble_by_id(msg_id)
            if bubble and hasattr(bubble, 'btn_read'):
                bubble.btn_read.setIcon(FluentIcon.PLAY)
                bubble.btn_read.setToolTip("朗读")
        except Exception as e:
            logger.error(f"Error in on_tts_stopped: {e}")

    def on_tts_error(self, msg_id, error_msg):
        try:
            self.on_tts_stopped(msg_id)
            logger.error(f"TTS Error for msg {msg_id}: {error_msg}")
            bubble = self.get_bubble_by_id(msg_id)
            if bubble and hasattr(bubble, 'btn_read'):
                 bubble.btn_read.setToolTip(f"错误: {error_msg}")
        except Exception as e:
            logger.error(f"Error in on_tts_error: {e}")

    def get_bubble_by_id(self, msg_id):
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, MessageBubble) and widget.msg_id == msg_id:
                    return widget
        return None

    def add_message_to_ui(self, role, content, msg_id, images=None, sibling_ids=None, current_index=0, model=None, reasoning=None, tool_calls=None):
        if role == "assistant" and (reasoning or tool_calls):
            exec_widget = ToolExecutionWidget(self)
            if reasoning:
                exec_widget.set_thinking(reasoning)
            
            if tool_calls:
                import json
                if isinstance(tool_calls, str):
                    try:
                        tool_calls = json.loads(tool_calls)
                    except:
                        tool_calls = []
                
                for tc in tool_calls:
                    exec_widget.add_tool_item(tc['name'], tc['type'], tc['status'], tc['args'], tc.get('result'))
            
            # Find insertion point (before stretch)
            count = self.chat_layout.count()
            inserted_exec = False
            if count > 0:
                item = self.chat_layout.itemAt(count - 1)
                if item.spacerItem():
                    self.chat_layout.insertWidget(count - 1, exec_widget)
                    inserted_exec = True
            if not inserted_exec:
                self.chat_layout.addWidget(exec_widget)

        bubble = MessageBubble(role, content, msg_id, self, images, sibling_ids, current_index, model=model)
        
        bubble.delete_requested.connect(self.delete_message)
        bubble.regenerate_requested.connect(self.regenerate_message)
        bubble.speak_requested.connect(self.speak_message)
        bubble.switch_branch_requested.connect(self.switch_branch)
        bubble.branch_conversation_requested.connect(self.branch_conversation)
        bubble.context_menu_requested.connect(self._on_bubble_context_menu)
        
        count = self.chat_layout.count()
        inserted = False
        if count > 0:
            item = self.chat_layout.itemAt(count - 1)
            if item.spacerItem():
                self.chat_layout.insertWidget(count - 1, bubble)
                inserted = True
        
        if not inserted:
            self.chat_layout.addWidget(bubble)
            
    def switch_branch(self, msg_id):
        self.db.switch_branch(msg_id)
        self.load_chat_history()

    def branch_conversation(self, msg_id):
        """Create a new branch from the parent of the given message"""
        # Find the message to get its parent
        msgs = self.db.get_messages(self.current_session_id)
        target_msg = None
        for m in msgs:
            if m[0] == msg_id:
                target_msg = m
                break
        
        if target_msg:
            # target_msg[4] is parent_id
            parent_id = target_msg[4]
            
            # Remove UI elements after parent_id to clear the way for new generation
            self.prune_ui_after(parent_id)
            
            # Trigger generation starting from parent_id
            self.trigger_llm_generation(parent_id=parent_id)

    def prune_ui_after(self, parent_id):
        """Remove messages from UI that are children of parent_id (or subsequent messages)"""
        # We iterate backwards
        # If parent_id is None, it means we are branching from root? 
        # If parent_id is None, we keep nothing? Or we keep the system prompt?
        # System prompt is not in chat_layout (it's hidden).
        
        # NOTE: get_messages returns active path.
        # If we are branching from A (parent U), we want to keep U.
        # So we delete everything after U.
        
        found_parent = False
        
        # Start from end (skipping stretch)
        # chat_layout has stretch at end?
        # Yes, usually.
        
        # Safety check for loop
        max_iters = self.chat_layout.count() * 2
        iters = 0
        
        while self.chat_layout.count() > 0 and iters < max_iters:
            iters += 1
            # Get last item (which might be stretch or widget)
            index = self.chat_layout.count() - 1
            item = self.chat_layout.itemAt(index)
            widget = item.widget()
            
            if not widget:
                # It's a layout item or spacer (stretch)
                self.chat_layout.takeAt(index)
                continue
                
            if isinstance(widget, MessageBubble):
                if widget.msg_id == parent_id:
                    # Found the parent, stop deleting.
                    found_parent = True
                    break
                else:
                    # This is a child or subsequent message, delete it
                    widget.deleteLater()
                    self.chat_layout.takeAt(index)
            elif isinstance(widget, ThinkingBubble) or isinstance(widget, QWidget):
                # Remove thinking bubble or other widgets (like streaming bubble)
                widget.deleteLater()
                self.chat_layout.takeAt(index)
        
        # If parent_id is None, we might have cleared everything, which is correct for root branch.
        
        # Add stretch back
        self.chat_layout.addStretch()

    def scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_image_pasted(self, image_path):
        self.selected_images.append(image_path)
        self.update_image_preview()

    def select_image(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "选择图片", 
            "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_paths:
            self.selected_images.extend(file_paths)
            self.update_image_preview()

    def take_screenshot(self):
        """最小化窗口并启动截图工具"""
        # 1. 隐藏当前窗口
        if self.window():
            self.window().hide()
        
        # 2. 延时一小段时间等待窗口隐藏完成，然后启动截图工具
        QTimer.singleShot(300, self.start_capture_tool)

    def start_capture_tool(self):
        # 3. 创建并显示截图工具
        # 注意：必须保持引用，否则会被垃圾回收
        self.capture_tool = ScreenCaptureTool()
        self.capture_tool.screenshot_captured.connect(self.on_screenshot_captured)
        self.capture_tool.canceled.connect(self.on_screenshot_canceled)
        self.capture_tool.show()

    def on_screenshot_captured(self, file_path):
        # 4. 添加到预览列表
        self.selected_images.append(file_path)
        self.update_image_preview()
        
        # 5. 恢复窗口
        self.restore_window()
        
    def on_screenshot_canceled(self):
        self.restore_window()
        
    def restore_window(self):
        if self.window():
            self.window().show()
            self.window().activateWindow()

    def update_image_preview(self):
        # Clear layout
        while self.image_preview_layout.count():
            item = self.image_preview_layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
            
        if not self.selected_images:
            self.image_preview_widget.hide()
            return
            
        self.image_preview_widget.show()
        
        for path in self.selected_images:
            lbl = QLabel()
            pix = QPixmap(path)
            if not pix.isNull():
                 pix = pix.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 lbl.setPixmap(pix)
                 lbl.setObjectName("imagePreviewLabel")
                 # lbl.setStyleSheet("border: 1px solid #ccc;")
            self.image_preview_layout.addWidget(lbl)
        
        # Add a clear button if there are images
        if self.selected_images:
            btn_clear = ToolButton(FluentIcon.CLOSE, self.image_preview_widget)
            btn_clear.setToolTip("清除所有图片")
            btn_clear.clicked.connect(self.clear_images)
            self.image_preview_layout.addWidget(btn_clear)

    def clear_images(self):
        self.selected_images = []
        self.update_image_preview()

    def on_send_button_clicked(self):
        if self._is_generating:
            self.stop_generation()
        else:
            self.send_message()

    def stop_generation(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            logger.info("[ChatUI] Stop requested by user")
            self.worker.stop()
            self._stop_timer.start(100)
        else:
            self._is_generating = False
            self.btn_send.setIcon(FluentIcon.SEND)
            self.btn_send.setText("发送")
    
    def _check_stop_timeout(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            logger.warning("[ChatUI] Stop timeout, forcing worker termination")
            self.worker.terminate()
            self.worker.wait(500)
            self.on_generation_stopped()
        self._stop_timer.stop()
            
    def on_generation_stopped(self):
        self._is_generating = False
        self.btn_send.setIcon(FluentIcon.SEND)
        self.btn_send.setText("发送")
        
        self._stop_timer.stop()
        self.update_timer.stop()
        
        if self.streaming_bubble:
            try:
                self.streaming_content += "\n\n*[已停止]*"
                self.streaming_bubble.update_content(self.streaming_content)
            except RuntimeError:
                pass
            self.streaming_bubble = None
        
        if self.status_bubble:
            try:
                self.status_bubble.deleteLater()
            except RuntimeError:
                pass
            self.status_bubble = None
            
        if self.thinking_bubble:
            try:
                self.thinking_bubble.deleteLater()
            except RuntimeError:
                pass
            self.thinking_bubble = None
        
        if self.tool_execution_widget:
            try:
                self.tool_execution_widget.deleteLater()
            except RuntimeError:
                pass
            self.tool_execution_widget = None
        
        if hasattr(self, 'worker') and self.worker:
            try:
                self.worker.finished.disconnect()
                self.worker.error.disconnect()
                self.worker.chunk_received.disconnect()
                self.worker.thinking_chunk.disconnect()
                self.worker.tool_status_changed.disconnect()
                self.worker.tool_execution_update.disconnect()
                self.worker.stopped.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.worker = None
        
        self.scroll_to_bottom()

    def send_message(self):
        user_input = self.input_text.toPlainText().strip()
        if (not user_input and not self.selected_images) or not self.current_session_id:
            return
        
        # Log the full user message
        logger.info(f"User sent: {user_input}")
        
        stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)

        images = list(self.selected_images)
        msg_id = self.db.add_message(self.current_session_id, "user", user_input, images)
        self.add_message_to_ui("user", user_input, msg_id, images)
        
        if stretch_item: self.chat_layout.addItem(stretch_item)
        
        self.input_text.clear()
        self.selected_images = []
        self.update_image_preview()
        
        QApplication.processEvents()
        self.scroll_to_bottom()

        self.trigger_llm_generation()

    def encode_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None

    def trigger_llm_generation(self, parent_id=None):
        logger.info("Starting LLM generation...")
        self._is_generating = True
        self.btn_send.setIcon(FluentIcon.CANCEL)
        self.btn_send.setText("停止")
        
        self.worker_session_id = self.current_session_id
        
        # Get model config from combo
        model_data = self.model_combo.currentData()
        
        is_thinking = 0
        is_visual = 0
        model_type = "llm"
        
        if model_data:
            if len(model_data) >= 6:
                api_key, base_url, model, is_thinking, is_visual, model_type = model_data[:6]
            elif len(model_data) >= 5:
                api_key, base_url, model, is_thinking, is_visual = model_data[:5]
            elif len(model_data) >= 4:
                api_key, base_url, model, is_thinking = model_data[:4]
            else:
                api_key, base_url, model = model_data[:3]
        else:
            # Fallback to QSettings if combo is empty or failed
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")

        if not api_key:
            w = MessageBox("提示", "请先在【模型配置】页面添加并选择一个有效的模型！", self)
            w.exec_()
            self._is_generating = False
            self.btn_send.setIcon(FluentIcon.SEND)
            self.btn_send.setText("发送")
            return

        # Check for Direct Image Generation
        if model_type == "image":
            self.trigger_direct_image_generation(api_key, base_url, model)
            return

        history = [{"role": "system", "content": self.current_system_prompt}]
        
        # Inject pet status context for Doro character
        pet_context = self._get_pet_status_context()
        if pet_context:
            history[0]['content'] += pet_context
        
        db_msgs = self.db.get_messages(self.current_session_id)
        
        # Handle branching: truncate history after parent_id
        if parent_id is not None:
            truncated = []
            for m in db_msgs:
                truncated.append(m)
                if m[0] == parent_id:
                    break
            db_msgs = truncated
            self.branching_parent_id = parent_id
        else:
            self.branching_parent_id = None
        
        # Check context toggle: if checked, only use the last message
        if hasattr(self, 'chk_no_context') and self.chk_no_context.isChecked():
            if db_msgs:
                db_msgs = [db_msgs[-1]]

        # Inject current time if enabled
        settings = QSettings("DoroPet", "Settings")
        if settings.value("inject_time", False, type=bool):
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_instruction = f"\n【当前时间】{current_time}"
            if history and history[0]['role'] == 'system':
                history[0]['content'] += time_instruction
            else:
                history.insert(0, {"role": "system", "content": time_instruction})

        # System Prompt Injection for Tool Use
        # Ensure the model knows how to handle tool outputs
        enabled_tools = self.get_enabled_plugins()
        
        # Check for available expressions to enable expression tool in system prompt
        available_expressions = []
        if self.live2d_widget and hasattr(self.live2d_widget, 'expression_ids') and self._is_doro_tools_enabled():
            try:
                available_expressions = list(self.live2d_widget.expression_ids)
            except:
                available_expressions = []
            
        if available_expressions:
             if "expression" not in enabled_tools:
                 enabled_tools.append("expression")

        if enabled_tools:
            tool_instruction = "\n【系统指令】你拥有强大的工具箱，包括：\n"
            
            if "search" in enabled_tools:
                tool_instruction += "1. 联网搜索工具（search_baidu, search_bing, visit_webpage, zhipu_web_search, zhipu_web_read）：用于获取实时信息。\n"
            
            if "image" in enabled_tools:
                tool_instruction += "2. 画图工具（generate_image）：当用户要求生成图片时调用。\n"
                
            if "python" in enabled_tools:
                tool_instruction += "3. 文件/代码操作工具（write_file, run_python_script, read_file, list_files, search_files）：\n"
                tool_instruction += "   - write_file: 创建或编辑任意文件（支持 Python, HTML, CSS, JS, Markdown 等）。\n"
                tool_instruction += "   - run_python_script: 运行本地 Python 脚本（需提供文件路径）。\n"
                tool_instruction += "   - read_file, list_files, search_files: 查看和搜索文件系统。\n"
                tool_instruction += "   - 【重要】关于编写插件（Plugin）：\n"
                tool_instruction += "     * 当用户请求“写个插件”、“制作插件”时，你必须创建一个 Python 脚本文件，路径必须在 'plugin/' 目录下（如 'plugin/hello.py'）。\n"
                tool_instruction += "     * 插件必须包含一个名为 'Plugin' 的类，该类必须继承自 'PyQt5.QtWidgets.QWidget'。\n"
                tool_instruction += "     * 这是一个原生 PyQt5 插件系统，不要生成 HTML/JS 文件作为插件，除非用户明确要求编写网页。\n"
                tool_instruction += "     * 示例结构：\n"
                tool_instruction += "       from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel\n"
                tool_instruction += "       class Plugin(QWidget):\n"
                tool_instruction += "           def __init__(self, parent=None):\n"
                tool_instruction += "               super().__init__(parent)\n"
                tool_instruction += "               layout = QVBoxLayout(self)\n"
                tool_instruction += "               layout.addWidget(QLabel('Hello Plugin'))\n"
                tool_instruction += "   - 任务示例：\n"
                tool_instruction += "     * 编写 Python 脚本并运行：先 write_file('script.py', content)，后 run_python_script('script.py')。\n"
                tool_instruction += "     * 创建网页：write_file('index.html', html_content)。\n"
                tool_instruction += "   - 务必检查运行结果并据此回答用户。\n"
                tool_instruction += "\n"
                tool_instruction += "【推荐工作流程】\n"
                tool_instruction += "1. 先用 list_files 或 search_files 了解项目结构\n"
                tool_instruction += "2. 用 read_file 确认文件内容\n"
                tool_instruction += "3. 再用 edit_file 进行精确修改\n"
                tool_instruction += "\n"
                tool_instruction += "【edit_file 使用技巧】\n"
                tool_instruction += "- search内容必须完全匹配，建议先read_file复制原文\n"
                tool_instruction += "- 包含正确的缩进（Python对缩进敏感）\n"
                tool_instruction += "- 如不确定内容，先用read_file查看\n"
                tool_instruction += "- 可使用fuzzy_match=true启用模糊匹配（忽略空格差异）\n"
                tool_instruction += "- 可使用context_before/context_after帮助定位重复内容\n"
                tool_instruction += "\n"
                tool_instruction += "【insert_at_line 使用技巧】\n"
                tool_instruction += "- 行号从1开始（1-indexed）\n"
                tool_instruction += "- line_number=0 表示插入到文件开头\n"
                tool_instruction += "- 先read_file确认行号\n"
                tool_instruction += "\n"
                tool_instruction += "【delete_lines 使用技巧】\n"
                tool_instruction += "- start_line和end_line都是包含的（inclusive）\n"
                tool_instruction += "- 只删除一行时，end_line可省略\n"
                tool_instruction += "\n"
                tool_instruction += "【常见错误避免】\n"
                tool_instruction += "- 路径必须相对于项目根目录\n"
                tool_instruction += "- 不能访问 src/core/ 目录（保护区域）\n"
                tool_instruction += "- 文件不存在时用write_file创建\n"
                tool_instruction += "- 使用find_in_file工具定位内容位置\n"

            if "expression" in enabled_tools and available_expressions:
                tool_instruction += f"4. Live2D表情控制工具（set_expression）：\n"
                tool_instruction += f"   - 根据回复的心情自动调整Live2D模型表情。\n"
                tool_instruction += f"   - 可用表情：{', '.join(available_expressions)}。\n"
                tool_instruction += f"   - **必须**调用工具来修改表情，严禁仅在回复中用文字描述（如'(xx表情已应用)'）。\n"
                tool_instruction += f"\n"
                tool_instruction += f"5. 宠物属性控制工具（modify_pet_attribute）：\n"
                tool_instruction += f"   - 当用户与Doro互动时，调用此工具修改Doro的属性。\n"
                tool_instruction += f"   - 推荐使用语义化参数 interaction，可精确控制互动效果：\n"
                tool_instruction += f"     * 投喂类：feed_snack(零食), feed_meal(正餐), feed_feast(大餐), feed_bad(变质食物)\n"
                tool_instruction += f"     * 玩耍类：play_gentle(轻度), play_fun(愉快), play_exhausting(剧烈)\n"
                tool_instruction += f"     * 清洁类：clean_wipe(擦拭), clean_wash(洗澡)\n"
                tool_instruction += f"     * 休息类：rest_nap(小憩), rest_sleep(沉睡)\n"
                tool_instruction += f"     * 互动类：pet_affection(抚摸), scold(责备), comfort(安慰)\n"
                tool_instruction += f"   - 可选参数 intensity 控制强度：light(0.5x), moderate(1.0x), heavy(1.5x)\n"
                tool_instruction += f"   - 新格式示例：modify_pet_attribute(interaction='play_fun', intensity='moderate')\n"
                tool_instruction += f"   - 兼容旧格式：modify_pet_attribute(attribute='mood', action='play')，会自动映射到对应效果\n"

            skill_mgr = SkillManager()
            enabled_skill_names = [k.replace("skill:", "") for k in enabled_tools if k.startswith("skill:")]
            if enabled_skill_names:
                tool_instruction += f"6. 专业技能工具：\n"
                for skill_name in enabled_skill_names:
                    if skill_name in skill_mgr.skills:
                        skill_desc = skill_mgr.skills[skill_name].description
                        tool_instruction += f"   - {skill_name}：{skill_desc}\n"

            tool_instruction += "当工具返回结果（JSON格式）后，请仔细分析，并回归对话主线，基于结果回答用户。决不要直接输出 JSON 数据。"

            # Append to current system prompt
            if history and history[0]['role'] == 'system':
                history[0]['content'] += tool_instruction
            else:
                # Should not happen given line 1936, but safe fallback
                history.insert(0, {"role": "system", "content": tool_instruction})

        has_images = False
        for msg_data in db_msgs:
            # Unpack safely (support both 4 and 7 items)
            if len(msg_data) >= 4:
                role = msg_data[1]
                content = msg_data[2]
                images = msg_data[3]
            else:
                continue

            if not images:
                history.append({"role": role, "content": content})
            else:
                has_images = True
                content_list = []
                if content:
                    content_list.append({"type": "text", "text": content})
                for img_path in images:
                    base64_image = self.encode_image(img_path)
                    if base64_image:
                        content_list.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                            "_file_path": img_path
                        })
                history.append({"role": role, "content": content_list})

        # Check if we need vision fallback
        if has_images and not is_visual:
            # Note: process_vision_fallback returns True if it starts async processing
            if self.process_vision_fallback(history, model_data, parent_id):
                return
        
        self.start_llm_worker(history, model_data, parent_id)

    def trigger_direct_image_generation(self, api_key, base_url, model):
        """Handle direct image generation without LLM worker"""
        logger.info(f"Starting direct image generation with model: {model}")
        
        self.worker_session_id = self.current_session_id
        
        # Get latest user message for prompt
        db_msgs = self.db.get_messages(self.worker_session_id)
        if not db_msgs:
            self._is_generating = False
            self.btn_send.setIcon(FluentIcon.SEND)
            self.btn_send.setText("发送")
            return
            
        # Find last user message
        last_user_msg = None
        for i in range(len(db_msgs) - 1, -1, -1):
            if db_msgs[i][1] == "user":
                last_user_msg = db_msgs[i][2]
                break
        
        if not last_user_msg:
             self._is_generating = False
             self.btn_send.setIcon(FluentIcon.SEND)
             self.btn_send.setText("发送")
             MessageBox("提示", "无法获取有效的图片生成提示词。", self).exec_()
             return
             
        # If content is list (e.g. with images), extract text
        if isinstance(last_user_msg, list):
             text_parts = [p['text'] for p in last_user_msg if isinstance(p, dict) and p.get('type') == 'text']
             last_user_msg = " ".join(text_parts)
             
        if not isinstance(last_user_msg, str) or not last_user_msg.strip():
             self._is_generating = False
             self.btn_send.setIcon(FluentIcon.SEND)
             self.btn_send.setText("发送")
             MessageBox("提示", "无法获取有效的图片生成提示词。", self).exec_()
             return

        # Start Image Generation Worker
        self.image_worker = ImageGenerationWorker(api_key, base_url, model, last_user_msg)
        self.image_worker.finished.connect(self.on_image_generation_finished)
        self.image_worker.error.connect(self.on_image_generation_error)
        self.image_worker.start()

    def on_image_generation_finished(self, result_json_str):
        self._is_generating = False
        self.btn_send.setIcon(FluentIcon.SEND)
        self.btn_send.setText("发送")
        
        session_id = self.worker_session_id
        is_same_session = (session_id == self.current_session_id)
        
        try:
            res = json.loads(result_json_str)
            if res.get("status") == "success":
                content = res.get("message", "")
                image_path = res.get("image_path", "")
                
                images = []
                if image_path:
                    images.append(image_path)
                    content = re.sub(r'!\[.*?\]\(.*?\)', '', content).strip()
                
                used_model = None
                if hasattr(self, 'image_worker') and hasattr(self.image_worker, 'model'):
                    used_model = self.image_worker.model
                
                msg_id = self.db.add_message(session_id, "assistant", content, images, model=used_model)
                if is_same_session:
                    self.add_message_to_ui("assistant", content, msg_id, images, model=used_model)
                    self.scroll_to_bottom()
            else:
                error_msg = res.get("message", "Unknown error")
                self.on_image_generation_error(error_msg)
        except Exception as e:
            self.on_image_generation_error(str(e))
            
    def on_image_generation_error(self, error_msg):
        self._is_generating = False
        self.btn_send.setIcon(FluentIcon.SEND)
        self.btn_send.setText("发送")
        MessageBox("生成失败", f"图片生成失败: {error_msg}", self).exec_()

    def process_vision_fallback(self, history, model_data, parent_id):
        """
        Check if we can find a vision model to describe images.
        Returns True if fallback started, False if not possible.
        """
        # 1. Identify all images in history that need description
        # We look for image_url blocks in ALL messages (User and Assistant)
        
        # Structure to track what needs analysis: list of (msg_idx, content_idx, image_path)
        self.vision_queue = []
        
        # First pass: check cache and collect missing ones
        has_changes = False
        
        for i, msg in enumerate(history):
            if isinstance(msg['content'], list):
                new_content = []
                content_modified = False
                
                for j, part in enumerate(msg['content']):
                    if part.get('type') == 'image_url':
                        file_path = part.get('_file_path')
                        if file_path:
                            # Check cache
                            cached_desc = self.db.get_image_description(file_path)
                            if cached_desc:
                                # Replace with text
                                new_content.append({
                                    "type": "text", 
                                    "text": f"\n[图片描述: {cached_desc}]\n"
                                })
                                content_modified = True
                                has_changes = True
                            else:
                                # Needs analysis
                                self.vision_queue.append((i, j, file_path))
                                # Keep original for now, will be replaced later
                                new_content.append(part)
                        else:
                             new_content.append(part)
                    else:
                        new_content.append(part)
                
                if content_modified:
                    msg['content'] = new_content

        # If no images need analysis, but we did some replacements, 
        # we return False so trigger_llm_generation proceeds to start_llm_worker (which will sanitize).
        if not self.vision_queue:
            return False

        # 2. If we have images to analyze, find a vision model
        vision_model_data = None
        
        # Try current model first (if it were visual, we wouldn't be here, but check anyway)
        # Actually, we are here because is_visual is False.
        
        # Search in combo items (loaded from DB)
        # We can't access combo items data directly easily without iterating.
        # But we can query DB or config.
        # Easier: iterate model_combo items
        
        count = self.model_combo.count()
        for i in range(count):
            data = self.model_combo.itemData(i)
            # data: (api_key, base_url, model, is_thinking, is_visual)
            if len(data) >= 5 and data[4]: # is_visual is True
                vision_model_data = data
                break
        
        if not vision_model_data:
            # Try to find 'gpt-4o' or 'claude-3' in name as fallback heuristic if data not reliable
            for i in range(count):
                data = self.model_combo.itemData(i)
                model_name = data[2] if len(data) >= 3 else ""
                if 'gpt-4o' in model_name or 'claude-3' in model_name or 'gemini' in model_name or 'vision' in model_name:
                    vision_model_data = data
                    break

        if not vision_model_data:
            msg = "当前选择的模型不支持视觉理解，且未找到可用的辅助视觉模型。\n请切换到支持视觉的模型，或在【模型配置】中添加支持视觉的模型（勾选'视觉模型'）。"
            MessageBox("不支持图片", msg, self).exec_()
            self._is_generating = False
            self.btn_send.setIcon(FluentIcon.SEND)
            self.btn_send.setText("发送")
            return True

        # 3. Start processing queue
        self.vision_model_data = vision_model_data
        self.vision_history = history # Store ref to modify
        self.vision_parent_id = parent_id
        self.vision_main_model_data = model_data
        self.vision_total_count = len(self.vision_queue)
        
        # Show Status Bubble
        if not hasattr(self, 'status_bubble') or self.status_bubble is None:
            self.status_bubble = StatusBubble(f"正在分析图片 (0/{self.vision_total_count})...", self)
            # Insert at bottom
            stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
            self.chat_layout.addWidget(self.status_bubble)
            if stretch_item: self.chat_layout.addItem(stretch_item)
            self.scroll_to_bottom()
            
        self.process_next_vision_item()
        return True

    def process_next_vision_item(self):
        if not self.vision_queue:
            self.finish_vision_fallback()
            return

        msg_idx, content_idx, file_path = self.vision_queue[0]
        
        # Update bubble
        current_idx = self.vision_total_count - len(self.vision_queue) + 1
        if self.status_bubble:
            self.status_bubble.update_text(f"正在分析图片 ({current_idx}/{self.vision_total_count})...")

        # Prepare request for vision model
        # We send: System prompt + User message with JUST this image
        prompt = "Please describe this image in detail. The description will be provided to a text-only model as context."
        
        base64_image = self.encode_image(file_path)
        
        vision_messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
        
        api_key, base_url, model = self.vision_model_data[:3]
        
        logger.info(f"[Vision] Starting vision model: base_url={base_url}, model={model}")
        
        # Use LLMWorker with skip_tools_and_max_tokens=True for vision models
        self.vision_worker = LLMWorker(api_key, base_url, vision_messages, model, self.db, enabled_plugins=[], skip_tools_and_max_tokens=True)
        self.vision_worker.finished.connect(self.on_vision_item_finished)
        self.vision_worker.error.connect(self.on_vision_item_error)
        self.vision_worker.start()

    def on_vision_item_finished(self, content, reasoning, tool_calls, generated_images=[]):
        logger.info(f"[Vision] Vision model finished, content length: {len(content) if content else 0}")
        # Save to cache and update history
        if self.vision_queue:
            msg_idx, content_idx, file_path = self.vision_queue.pop(0)
            
            # Save to DB
            self.db.save_image_description(file_path, content)
            
            # Update history
            # We need to find the item again because indices might shift if we modified the list?
            # Actually, we are modifying deep inside dicts, so list structure of 'history' stays same length.
            # But wait, content list length stays same too, we just replace the item.
            
            msg = self.vision_history[msg_idx]
            if isinstance(msg['content'], list) and len(msg['content']) > content_idx:
                # Replace image_url with text
                msg['content'][content_idx] = {
                    "type": "text", 
                    "text": f"\n[图片描述: {content}]\n"
                }
            
            # Next
            self.process_next_vision_item()

    def on_vision_item_error(self, err_msg):
        logger.error(f"Vision item error: {err_msg}")
        # Skip this item or retry? For now, skip and leave original (or add error note)
        if self.vision_queue:
            msg_idx, content_idx, file_path = self.vision_queue.pop(0)
            
            # Optional: Add error note to history?
            # msg = self.vision_history[msg_idx]
            # msg['content'][content_idx] = {"type": "text", "text": "[图片分析失败]"}
            
            self.process_next_vision_item()

    def finish_vision_fallback(self):
        logger.info("Vision fallback finished.")
        
        # Remove Status Bubble
        if self.status_bubble:
            self.status_bubble.deleteLater()
            self.status_bubble = None
        
        # Proceed to main LLM
        self.start_llm_worker(self.vision_history, self.vision_main_model_data, self.vision_parent_id)

    def start_llm_worker(self, history, model_data, parent_id):
        # Sanitize history (remove internal _file_path keys)
        clean_history = []
        for msg in history:
            clean_msg = msg.copy()
            if isinstance(clean_msg.get('content'), list):
                new_content = []
                for part in clean_msg['content']:
                    clean_part = part.copy()
                    if '_file_path' in clean_part:
                        del clean_part['_file_path']
                    new_content.append(clean_part)
                clean_msg['content'] = new_content
            clean_history.append(clean_msg)
            
        # Extract params

        is_thinking = 0
        if model_data:
            if len(model_data) >= 4:
                api_key, base_url, model, is_thinking = model_data[:4]
            else:
                api_key, base_url, model = model_data[:3]
        else:
            # Fallback (should be covered in trigger_llm_generation, but good for safety)
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")

        # Determine available expressions
        available_expressions = []
        
        # Check setting
        settings = QSettings("DoroPet", "Settings")
        enable_expression = settings.value("enable_expression_response", True, type=bool)
        
        is_doro_tools_enabled = self._is_doro_tools_enabled()
        
        if enable_expression and self.live2d_widget and hasattr(self.live2d_widget, 'expression_ids') and is_doro_tools_enabled:
            try:
                available_expressions = list(self.live2d_widget.expression_ids)
            except Exception as e:
                logger.error(f"Error converting expression_ids to list: {e}")
                available_expressions = []
            
        enabled_plugins = self.get_enabled_plugins()
        if available_expressions:
             if "expression" not in enabled_plugins:
                 enabled_plugins.append("expression")

        self.worker = LLMWorker(api_key, base_url, clean_history, model, self.db, is_thinking=is_thinking, enabled_plugins=enabled_plugins, available_expressions=available_expressions)
        self.worker.chunk_received.connect(self.handle_llm_chunk)
        self.worker.thinking_chunk.connect(self.on_thinking_chunk)
        self.worker.finished.connect(self.handle_llm_response)
        self.worker.error.connect(self.handle_llm_error)
        self.worker.tool_status_changed.connect(self.on_tool_status_changed)
        self.worker.tool_execution_update.connect(self.on_tool_execution_update)
        self.worker.stopped.connect(self.on_generation_stopped)
        
        if self.live2d_widget and is_doro_tools_enabled:
             self.worker.expression_changed.connect(self.on_expression_change_request)
             self.worker.pet_attribute_changed.connect(self.on_pet_attribute_change_request)
        
        self.streaming_bubble = None
        self.streaming_content = ""
        self.streaming_buffer = ""
        self.tool_execution_widget = None
        self.update_timer.start(100)
        
        stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.thinking_bubble = ThinkingBubble(self)
        self.chat_layout.addWidget(self.thinking_bubble)
        if stretch_item: self.chat_layout.addItem(stretch_item)
        
        self.scroll_to_bottom()
        
        self.worker.start()

    def check_expression_fallback(self, content):
        """Check if model described an expression change but didn't call the tool"""
        # Check setting
        settings = QSettings("DoroPet", "Settings")
        if not settings.value("enable_expression_response", True, type=bool):
            return

        if not self.live2d_widget or not hasattr(self.live2d_widget, 'expression_ids'):
            return

        # 1. Check for explicit pattern from user log: (expression_name表情已应用)
        match = re.search(r'[（\(](.*?)表情已应用[）\)]', content)
        if match:
            potential_name = match.group(1)
            # Verify if it exists (case-insensitive)
            if self.is_valid_expression(potential_name):
                logger.info(f"Expression fallback triggered (pattern match): {potential_name}")
                self.on_expression_change_request(potential_name)
                return
        
        # 2. If not found, check for simple bracketed expressions commonly used by RP bots
        # Look for [expression] or (expression) or 【expression】
        matches = re.findall(r'[（\(\[【](.*?)[）\)\]】]', content)
        for m in matches:
            if self.is_valid_expression(m):
                logger.info(f"Expression fallback triggered (bracket match): {m}")
                self.on_expression_change_request(m)
                return

    def is_valid_expression(self, name):
        """Check if name matches any available expression ID (case-insensitive)"""
        if not hasattr(self.live2d_widget, 'expression_ids'):
            return False
            
        ids = self.live2d_widget.expression_ids
        for eid in ids:
            if eid.lower() == name.lower():
                return True
        return False

    def on_expression_change_request(self, expression_name):
        """Handle expression change request from LLM"""
        logger.info(f"Received expression change request: {expression_name}")
        
        if not self.live2d_widget:
            logger.warning("Live2D widget not available")
            return
            
        if not hasattr(self.live2d_widget, 'model'):
            logger.warning("Live2D model not available")
            return
            
        try:
            # Check if expression exists (case-insensitive fallback if needed)
            target_exp = expression_name
            if hasattr(self.live2d_widget, 'expression_ids'):
                # Exact match check
                if expression_name not in self.live2d_widget.expression_ids:
                    logger.warning(f"Expression '{expression_name}' not found in {self.live2d_widget.expression_ids}")
                    # Try case-insensitive match
                    for exp in self.live2d_widget.expression_ids:
                        if exp.lower() == expression_name.lower():
                            target_exp = exp
                            logger.info(f"Using case-insensitive match: {target_exp}")
                            break
            
            logger.info(f"Setting expression to: {target_exp}")
            self.live2d_widget.model.SetExpression(target_exp)
        except Exception as e:
            logger.error(f"Failed to set expression: {e}")

    def on_pet_attribute_change_request(self, interaction, intensity="moderate"):
        """Handle pet attribute change request from LLM
        
        New format: interaction="play_fun", intensity="moderate"
        Legacy format: action="play", intensity="moderate" (action is passed as 'interaction' for backward compat)
        """
        logger.info(f"Received pet attribute change request: interaction={interaction}, intensity={intensity}")
        
        if not self.live2d_widget or not hasattr(self.live2d_widget, 'attr_manager'):
            logger.warning("PetAttributesManager not available")
            return
        
        attr_manager = self.live2d_widget.attr_manager
        
        new_interactions = [
            "feed_snack", "feed_meal", "feed_feast", "feed_bad",
            "play_gentle", "play_fun", "play_exhausting",
            "clean_wipe", "clean_wash",
            "rest_nap", "rest_sleep",
            "pet_affection", "scold", "comfort"
        ]
        
        if interaction in new_interactions:
            attr_manager.perform_interaction(interaction, intensity)
            logger.info(f"Pet attribute interaction performed: {interaction} (intensity: {intensity})")
            return
        
        legacy_actions = ["feed", "play", "clean", "rest"]
        if interaction in legacy_actions:
            attr_manager.perform_interaction(interaction, intensity)
            logger.info(f"Pet attribute interaction performed (legacy): {interaction}")
            return
        
        logger.warning(f"Unknown interaction type: {interaction}")

    def on_thinking_chunk(self, chunk):
        if not self.tool_execution_widget:
            self.tool_execution_widget = ToolExecutionWidget(self)
            stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
            self.chat_layout.addWidget(self.tool_execution_widget)
            if stretch_item: self.chat_layout.addItem(stretch_item)
        
        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None
            
        self.tool_execution_widget.update_thinking(chunk)
        self.scroll_to_bottom()

    def on_tool_status_changed(self, status_text):
        logger.info(f"Tool status changed: {status_text}")
        
        if self.status_bubble:
            self.status_bubble.update_text(status_text)
            return

        self.status_bubble = StatusBubble(status_text, self)
        
        stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.chat_layout.addWidget(self.status_bubble)
        if stretch_item: self.chat_layout.addItem(stretch_item)
        
        self.scroll_to_bottom()

    def on_tool_execution_update(self, tool_name, tool_type, status, args, result):
        logger.info(f"Tool execution update: {tool_name}, type={tool_type}, status={status}")
        
        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None
        
        if not self.tool_execution_widget:
            self.tool_execution_widget = ToolExecutionWidget(self)
            stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
            self.chat_layout.addWidget(self.tool_execution_widget)
            if stretch_item: self.chat_layout.addItem(stretch_item)
        
        if self.status_bubble:
            self.status_bubble.deleteLater()
            self.status_bubble = None
        
        self.tool_execution_widget.update_or_add_item(tool_name, tool_type, status, args, result)
        self.scroll_to_bottom()

    def update_streaming_display(self):
        """Timer callback to update UI with buffered content"""
        if not self.streaming_buffer:
            return
            
        # Move buffer to content
        chunk = self.streaming_buffer
        self.streaming_buffer = ""
        
        # Remove thinking bubble if exists (lazy removal on first render)
        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        self.streaming_content += chunk
        
        if not self.streaming_bubble:
            # Temporarily remove stretch item to insert bubble before it
            stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
            
            # Get model name from worker if available
            used_model = None
            if hasattr(self, 'worker') and hasattr(self.worker, 'model'):
                used_model = self.worker.model

            # Create a new bubble for streaming with dummy ID
            self.streaming_bubble = MessageBubble("assistant", "", -1, self, model=used_model)
            self.streaming_bubble.delete_requested.connect(self.delete_message)
            self.streaming_bubble.regenerate_requested.connect(self.regenerate_message)
            self.streaming_bubble.speak_requested.connect(self.speak_message)
            self.streaming_bubble.switch_branch_requested.connect(self.switch_branch)
            self.streaming_bubble.branch_conversation_requested.connect(self.branch_conversation)
            self.streaming_bubble.context_menu_requested.connect(self._on_bubble_context_menu)
            self.chat_layout.addWidget(self.streaming_bubble)
            
            if stretch_item: self.chat_layout.addItem(stretch_item)
            
        self.streaming_bubble.update_content(self.streaming_content)
        self.scroll_to_bottom()

    def handle_llm_chunk(self, chunk):
        # Tool execution is finished if we receive text
        if self.status_bubble:
            self.status_bubble.deleteLater()
            self.status_bubble = None

        # Just buffer the chunk
        self.streaming_buffer += chunk

    def check_and_generate_title(self):
        """Check if we need to auto-generate a title for this session"""
        if not self.current_session_id: return

        # 1. Check if current title is default "New Chat"
        current_title = "New Chat"
        sessions = self.db.get_sessions()
        for s in sessions:
            if s[0] == self.current_session_id:
                current_title = s[1]
                break
        
        # Check if it's "New Chat" (case insensitive just in case)
        if current_title.lower() != "new chat":
            return

        # 2. Get chat history
        msgs = self.db.get_messages(self.current_session_id)
        # Only generate if we have at least 2 messages (User + Assistant)
        if not msgs or len(msgs) < 2: return
        
        # Limit generation to early stage of conversation (e.g. < 6 messages)
        # to avoid re-generating title for long existing "New Chat" sessions constantly
        if len(msgs) > 6: return

        # Construct context for summarization (use first 2 exchanges)
        context_msgs = msgs[:4] 
        context_str = ""
        for msg in context_msgs:
            role = msg[1]
            content = msg[2]
            # Truncate long content
            clean_content = content[:200] + "..." if len(content) > 200 else content
            context_str += f"{role}: {clean_content}\n"
            
        prompt = f"Summarize the following conversation into a short title (max 10 words). Output ONLY the title text without quotes.\n\nConversation:\n{context_str}"

        # 3. Start LLM Worker for title
        model_data = self.model_combo.currentData()
        if not model_data: return

        # Check model type, skip if it's an image model
        if len(model_data) >= 6 and model_data[5] == "image":
            return
        
        if len(model_data) >= 3:
            api_key, base_url, model = model_data[:3]
        else:
            return
            
        history = [{"role": "user", "content": prompt}]
        
        # Use a separate worker (disable tools to avoid multi-turn loop)
        self.title_worker = LLMWorker(api_key, base_url, history, model, self.db, enabled_plugins=[])
        self.title_worker.finished.connect(self.on_title_generated)
        # We don't connect chunk_received, we don't need streaming for title
        self.title_worker.start()

    def on_title_generated(self, title, reasoning, tool_calls, _):
        if not title: return
        # Clean title
        title = title.strip().strip('"').strip("'")
        # Remove any trailing period
        if title.endswith("."): title = title[:-1]
        
        if not title: return
        
        # Avoid <think> tags if they leaked into final output (though worker handles them usually)
        title = re.sub(r'<think>.*?</think>', '', title, flags=re.DOTALL).strip()

        session_id = self.worker_session_id
        if not session_id: return

        # Update DB
        self.db.update_session_title(session_id, title)
        
        # Update UI List
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            if item.data(Qt.UserRole) == session_id:
                display_title = title
                if len(title) > 12:
                    display_title = title[:11] + "…"
                item.setText(display_title)
                item.setToolTip(title)
                break

    def handle_llm_response(self, content, reasoning, tool_calls, generated_images=[]):
        self.update_timer.stop()
        if self.streaming_buffer:
            self.update_streaming_display()

        if self.status_bubble:
            self.status_bubble.deleteLater()
            self.status_bubble = None

        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None
        
        self.check_expression_fallback(content)

        parent_id = self.branching_parent_id
        self.branching_parent_id = None
        
        used_model = None
        if hasattr(self, 'worker') and hasattr(self.worker, 'model'):
            used_model = self.worker.model

        # Reset current turn state
        self.tool_execution_widget = None
        
        session_id = self.worker_session_id
        is_same_session = (session_id == self.current_session_id)
        
        if self.streaming_bubble:
            msg_id = self.db.add_message(session_id, "assistant", content, generated_images, parent_id=parent_id, model=used_model, reasoning=reasoning, tool_calls=tool_calls)
            
            self.streaming_bubble.msg_id = msg_id
            
            if is_same_session:
                self.load_chat_history()
            
            self.streaming_bubble = None
            self.streaming_content = ""
        else:
            msg_id = self.db.add_message(session_id, "assistant", content, generated_images, parent_id=parent_id, model=used_model, reasoning=reasoning, tool_calls=tool_calls)
            if is_same_session:
                self.load_chat_history()
        
        if is_same_session:
            QApplication.processEvents()
            self.scroll_to_bottom()
        
        self._is_generating = False
        self.btn_send.setIcon(FluentIcon.SEND)
        self.btn_send.setText("发送")
        
        if is_same_session:
            self.check_and_generate_title()

    def handle_llm_error(self, err_msg):
        self.update_timer.stop()
        logger.error(f"LLM Error: {err_msg}")
        
        if self.status_bubble:
            self.status_bubble.deleteLater()
            self.status_bubble = None

        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        if self.tool_execution_widget:
            self.tool_execution_widget.deleteLater()
            self.tool_execution_widget = None

        w = MessageBox("API 错误", err_msg, self)
        w.exec_()
        self._is_generating = False
        self.btn_send.setIcon(FluentIcon.SEND)
        self.btn_send.setText("发送")

    def delete_message(self, msg_id):
        self.db.delete_message(msg_id)
        self.load_chat_history()

    def regenerate_message(self, msg_id):
        # 1. Find message index
        msgs = self.db.get_messages(self.current_session_id)
        target_idx = -1
        for i, m in enumerate(msgs):
            if m[0] == msg_id:
                target_idx = i
                break
        
        if target_idx == -1: return

        # 2. Check if it's the last assistant message
        # If it is, we delete it and re-trigger LLM
        # If it's not the last one, regeneration is tricky because context is different.
        # Usually regeneration is only allowed for the latest assistant reply.
        
        # But for flexibility, let's say if we regenerate a message, 
        # we delete that message and ALL subsequent messages, then trigger LLM based on remaining history.
        # This is a common pattern (e.g. ChatGPT "Edit" or "Regenerate").
        
        w = MessageBox("确认重新生成", "重新生成将会删除此消息及其之后的所有对话记录，确定要继续吗？", self)
        if w.exec_():
            # Delete this and subsequent
            ids_to_delete = [m[0] for m in msgs[target_idx:]]
            for mid in ids_to_delete:
                self.db.delete_message(mid)
            
            self.load_chat_history()
            self.trigger_llm_generation()

    def show_message_context_menu(self, msg_id, role, content, global_pos):
        menu = QMenu()
        copy_action = menu.addAction("复制")
        delete_action = menu.addAction("删除")
        
        action = menu.exec_(global_pos)
        
        if action == copy_action:
            QApplication.clipboard().setText(content)
        elif action == delete_action:
            self.db.delete_message(msg_id)
            self.load_chat_history()
    
    def _on_bubble_context_menu(self, msg_id, role, content, global_pos):
        self.show_message_context_menu(msg_id, role, content, global_pos) 
