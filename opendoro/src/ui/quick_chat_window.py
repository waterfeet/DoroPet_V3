import sys
import re
import uuid
import html
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QComboBox, QFrame, QApplication,
                             QScrollArea, QButtonGroup, QSizePolicy, QTextBrowser,
                             QGraphicsOpacityEffect, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer, QSize
from PyQt5.QtGui import QFont, QPixmap, QIcon
from qfluentwidgets import (PushButton, PrimaryPushButton, TransparentToolButton, ToolButton, FluentIcon as FIF,
                            CardWidget, StrongBodyLabel, BodyLabel, setTheme, Theme,
                            isDarkTheme, TransparentTogglePushButton, MessageBox,
                            LineEdit, ComboBox, TextEdit)

import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from src.core.database import ChatDatabase
from src.services.llm_service import LLMWorker
from src.core.memory_manager import MemoryManager, init_memory_database
from datetime import datetime
from src.resource_utils import resource_path


class QuickMessageBubble(QFrame):
    """快捷聊天消息气泡 - 带操作按钮"""
    
    delete_requested = pyqtSignal(int)
    regenerate_requested = pyqtSignal(int)
    speak_requested = pyqtSignal(int, str)
    
    def __init__(self, role, content, msg_id, parent_window=None):
        super().__init__()
        self.role = role
        self.content = content
        self.msg_id = msg_id
        self.parent_window = parent_window
        
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background-color: transparent;")
        
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI - 操作按钮在侧边"""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        
        self.container = QFrame(self)
        self.container.setAttribute(Qt.WA_StyledBackground, True)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        self.container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.container.setMinimumWidth(80)
        
        is_dark = isDarkTheme()
        
        if self.role == "user":
            self.container.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 120, 215, 180);
                    color: white;
                    border-radius: 10px;
                }
            """)
            
            self.content_label = QLabel(self.content)
            self.content_label.setWordWrap(True)
            self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.content_label.setStyleSheet("background-color: transparent; color: white;")
            self.container_layout.addWidget(self.content_label)
        else:
            if is_dark:
                self.container.setStyleSheet("""
                    QFrame {
                        background-color: rgba(50, 50, 50, 220);
                        color: rgba(255, 255, 255, 220);
                        border-radius: 10px;
                    }
                """)
            else:
                self.container.setStyleSheet("""
                    QFrame {
                        background-color: rgba(245, 245, 245, 220);
                        color: rgba(0, 0, 0, 200);
                        border-radius: 10px;
                    }
                """)
            
            self.content_browser = QTextBrowser()
            self.content_browser.setOpenExternalLinks(True)
            self.content_browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            if is_dark:
                self.content_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: transparent;
                        color: rgba(255, 255, 255, 220);
                        border: none;
                    }
                """)
            else:
                self.content_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: transparent;
                        color: rgba(0, 0, 0, 200);
                        border: none;
                    }
                """)
            self.content_browser.setHtml(self.parent_window.render_markdown(self.content) if self.parent_window else self.content)
            self.content_browser.setMinimumWidth(200)
            self.content_browser.setMaximumWidth(400)
            self.container_layout.addWidget(self.content_browser)
        
        self.action_widget = QWidget(self)
        self.action_layout = QVBoxLayout(self.action_widget)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(2)
        
        if is_dark:
            btn_style = """
                ToolButton {
                    background-color: transparent;
                    border: none;
                }
                ToolButton:hover {
                    background-color: rgba(255, 255, 255, 30);
                    border-radius: 3px;
                }
            """
        else:
            btn_style = """
                ToolButton {
                    background-color: transparent;
                    border: none;
                }
                ToolButton:hover {
                    background-color: rgba(0, 0, 0, 30);
                    border-radius: 3px;
                }
            """
        
        self.btn_copy = ToolButton(FIF.COPY, self.action_widget)
        self.btn_copy.setFixedSize(20, 20)
        self.btn_copy.setToolTip("复制")
        self.btn_copy.setIconSize(QSize(14, 14))
        self.btn_copy.setStyleSheet(btn_style)
        self.btn_copy.clicked.connect(self.copy_content)
        self.action_layout.addWidget(self.btn_copy)
        
        self.btn_delete = ToolButton(FIF.DELETE, self.action_widget)
        self.btn_delete.setFixedSize(20, 20)
        self.btn_delete.setToolTip("删除")
        self.btn_delete.setIconSize(QSize(14, 14))
        self.btn_delete.setStyleSheet(btn_style)
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.msg_id))
        self.action_layout.addWidget(self.btn_delete)
        
        if self.role == "assistant":
            self.btn_regen = ToolButton(FIF.SYNC, self.action_widget)
            self.btn_regen.setFixedSize(20, 20)
            self.btn_regen.setToolTip("重新生成")
            self.btn_regen.setIconSize(QSize(14, 14))
            self.btn_regen.setStyleSheet(btn_style)
            self.btn_regen.clicked.connect(lambda: self.regenerate_requested.emit(self.msg_id))
            self.action_layout.addWidget(self.btn_regen)
            
            self.btn_read = ToolButton(FIF.PLAY, self.action_widget)
            self.btn_read.setFixedSize(20, 20)
            self.btn_read.setToolTip("朗读")
            self.btn_read.setIconSize(QSize(14, 14))
            self.btn_read.setStyleSheet(btn_style)
            self.btn_read.clicked.connect(lambda: self.speak_requested.emit(self.msg_id, self.content))
            self.action_layout.addWidget(self.btn_read)
        
        self.action_layout.addStretch()
        
        if self.role == "user":
            self.main_layout.addStretch()
            self.main_layout.addWidget(self.action_widget, 0, Qt.AlignVCenter)
            self.main_layout.addWidget(self.container, 0, Qt.AlignVCenter)
        else:
            self.main_layout.addWidget(self.container, 0, Qt.AlignVCenter)
            self.main_layout.addWidget(self.action_widget, 0, Qt.AlignVCenter)
            self.main_layout.addStretch()
        
        self.opacity_effect = QGraphicsOpacityEffect(self.action_widget)
        self.opacity_effect.setOpacity(0.0)
        self.action_widget.setGraphicsEffect(self.opacity_effect)
    
    def enterEvent(self, event):
        """鼠标进入时显示操作按钮"""
        self.opacity_effect.setOpacity(1.0)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开时隐藏操作按钮"""
        self.opacity_effect.setOpacity(0.0)
        super().leaveEvent(event)
    
    def copy_content(self):
        """复制内容到剪贴板"""
        QApplication.clipboard().setText(self.content)
        self.btn_copy.setIcon(FIF.ACCEPT)
        self.btn_copy.setToolTip("已复制")
        QTimer.singleShot(1500, self.reset_copy_icon)
    
    def reset_copy_icon(self):
        """重置复制按钮图标"""
        self.btn_copy.setIcon(FIF.COPY)
        self.btn_copy.setToolTip("复制")


class QuickChatWindow(QWidget):
    """独立快捷聊天窗口"""
    
    def __init__(self, db=None, persona_db=None, live2d_widget=None):
        super().__init__()
        self.chat_db = db or ChatDatabase()
        self.persona_db = persona_db
        self.live2d_widget = live2d_widget
        self.current_session_id = None
        self.current_persona = "默认助手"
        self.current_system_prompt = "You are a helpful assistant."
        self._is_generating = False
        
        self.selected_images = []
        
        from src.core.database import DatabaseManager
        db_manager = DatabaseManager()
        init_memory_database(db_manager)
        self.memory_manager = MemoryManager(db_manager)
        
        from src.core.tts import TTSManager
        self.tts_manager = TTSManager(db_manager)
        
        self.message_widgets = {}
        
        icon_path = resource_path("data\\icons\\app.ico")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化 UI - 简洁布局设计"""
        self.setWindowTitle("Doro 快捷聊天")
        self.setMinimumSize(450, 600)
        self.resize(550, 800)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._drag_position = None
        self._mouse_pressed = False
        
        self.main_container = QWidget(self)
        self.main_container.setObjectName("mainContainer")
        
        is_dark = isDarkTheme()
        
        if is_dark:
            setTheme(Theme.DARK)
            self.main_container.setStyleSheet("""
                QWidget#mainContainer {
                    background-color: rgba(32, 32, 32, 220);
                    border-radius: 10px;
                }
                QScrollArea {
                    background-color: rgba(0, 0, 0, 80);
                }
            """)
        else:
            self.main_container.setStyleSheet("""
                QWidget#mainContainer {
                    background-color: rgba(255, 255, 255, 180);
                    border-radius: 10px;
                    border: 1px solid rgba(0, 0, 0, 30);
                }
                QScrollArea {
                    background-color: rgba(255, 255, 255, 100);
                }
            """)
        
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        title_bar = self.create_title_bar()
        title_bar.setFixedHeight(40)
        main_layout.addWidget(title_bar)
        
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll.setMinimumHeight(500)
        self.chat_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        if is_dark:
            self.chat_scroll.setStyleSheet("""
                QScrollArea {
                    background-color: rgba(20, 20, 20, 120);
                    border: 1px solid rgba(255, 255, 255, 20);
                    border-radius: 8px;
                }
                QScrollBar:vertical {
                    background-color: rgba(255, 255, 255, 30);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(255, 255, 255, 80);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(255, 255, 255, 120);
                }
            """)
        else:
            self.chat_scroll.setStyleSheet("""
                QScrollArea {
                    background-color: rgba(255, 255, 255, 120);
                    border: 1px solid rgba(0, 0, 0, 20);
                    border-radius: 8px;
                }
                QScrollBar:vertical {
                    background-color: rgba(0, 0, 0, 30);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(0, 0, 0, 80);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(0, 0, 0, 120);
                }
            """)
        
        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setSpacing(8)
        self.chat_layout.setContentsMargins(5, 5, 5, 5)
        self.chat_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_content)
        main_layout.addWidget(self.chat_scroll, stretch=10)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        if is_dark:
            separator.setStyleSheet("background-color: rgba(255, 255, 255, 50);")
        else:
            separator.setStyleSheet("background-color: rgba(0, 0, 0, 50);")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 6, 10, 6)
        control_layout.setSpacing(5)
        
        self.image_preview_widget = QWidget()
        self.image_preview_layout = QHBoxLayout(self.image_preview_widget)
        self.image_preview_layout.setContentsMargins(0, 0, 0, 5)
        self.image_preview_layout.setSpacing(5)
        self.image_preview_widget.hide()
        control_layout.addWidget(self.image_preview_widget)
        
        self.input_text = TextEdit()
        self.input_text.setPlaceholderText("输入想对 Doro 说的话...")
        self.input_text.setMaximumHeight(60)
        self.input_text.setMinimumHeight(50)
        control_layout.addWidget(self.input_text)
        
        self._auto_play_enabled = False
        
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        
        self.btn_screenshot = ToolButton(FIF.CUT, self)
        self.btn_screenshot.setFixedSize(24, 24)
        self.btn_screenshot.setToolTip("屏幕截图")
        self.btn_screenshot.clicked.connect(self.take_screenshot)
        bottom_row.addWidget(self.btn_screenshot)
        
        self.auto_play_btn = TransparentToolButton(FIF.VOLUME, self)
        self.auto_play_btn.setFixedSize(24, 24)
        self.auto_play_btn.setToolTip("自动播放语音")
        self.auto_play_btn.setStyleSheet("""
            TransparentToolButton {
                border: none;
                background-color: transparent;
            }
        """)
        self.auto_play_btn.clicked.connect(self._toggle_auto_play)
        self._update_auto_play_btn_style()
        bottom_row.addWidget(self.auto_play_btn)
        
        self.quick_phrase_combo = ComboBox()
        self.quick_phrase_combo.setFixedHeight(30)
        self.quick_phrase_combo.setMinimumWidth(150)
        
        quick_phrases = [
            "早上好！",
            "你好呀~",
            "陪我聊天~",
            "记得吃饭哦~",
            "别太累了",
            "今天心情怎么样？",
            "给我讲个故事",
            "我们来玩游戏吧",
        ]
        self.quick_phrase_combo.addItem("选择快捷用语...")
        self.quick_phrase_combo.setCurrentIndex(0)
        for phrase in quick_phrases:
            self.quick_phrase_combo.addItem(phrase)
        
        self.quick_phrase_combo.currentIndexChanged.connect(self.on_quick_phrase_selected)
        bottom_row.addWidget(self.quick_phrase_combo)
        
        self.persona_combo = ComboBox()
        self.persona_combo.setFixedHeight(30)
        self.load_personas()
        self.persona_combo.currentIndexChanged.connect(self.on_persona_changed)
        bottom_row.addWidget(self.persona_combo, 1)
        
        self.send_btn = ToolButton(FIF.SEND, self)
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.clicked.connect(self.send_message)
        bottom_row.addWidget(self.send_btn)
        
        self.stop_btn = ToolButton(FIF.CANCEL, self)
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_generation)
        bottom_row.addWidget(self.stop_btn)
        
        control_layout.addLayout(bottom_row)
        
        main_layout.addWidget(control_panel)
        
        self.load_chat_history()
    
    def create_title_bar(self):
        """创建标题栏"""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: transparent;")
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(10, 0, 5, 0)
        
        is_dark = isDarkTheme()
        
        self.title_label = QLabel("💬 Doro 快捷聊天")
        if is_dark:
            self.title_label.setStyleSheet("""
                color: rgba(255, 255, 255, 220);
                font-size: 14px;
                font-weight: bold;
            """)
        else:
            self.title_label.setStyleSheet("""
                color: rgba(0, 0, 0, 200);
                font-size: 14px;
                font-weight: bold;
            """)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        min_btn = TransparentToolButton(FIF.MINIMIZE, self)
        min_btn.setFixedSize(25, 25)
        if is_dark:
            min_btn.setStyleSheet("""
                TransparentToolButton {
                    border: none;
                    border-radius: 3px;
                    background-color: rgba(255, 255, 255, 30);
                }
                TransparentToolButton:hover {
                    background-color: rgba(255, 255, 255, 60);
                }
            """)
        else:
            min_btn.setStyleSheet("""
                TransparentToolButton {
                    border: none;
                    border-radius: 3px;
                    background-color: rgba(0, 0, 0, 30);
                }
                TransparentToolButton:hover {
                    background-color: rgba(0, 0, 0, 60);
                }
            """)
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)
        
        close_btn = TransparentToolButton(FIF.CLOSE, self)
        close_btn.setFixedSize(25, 25)
        close_btn.setStyleSheet("""
            TransparentToolButton {
                border: none;
                border-radius: 3px;
                background-color: rgba(255, 100, 100, 150);
            }
            TransparentToolButton:hover {
                background-color: rgba(255, 50, 50, 200);
            }
        """)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            if event.y() < 40:
                self._mouse_pressed = True
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.LeftButton and self._mouse_pressed:
            self.move(event.globalPos() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._mouse_pressed = False
    
    def take_screenshot(self):
        """截图功能"""
        if self.window():
            self.window().hide()
        
        QTimer.singleShot(300, self.start_capture_tool)
    
    def start_capture_tool(self):
        """启动截图工具"""
        try:
            from src.ui.screenshot_tool import ScreenCaptureTool
            self.capture_tool = ScreenCaptureTool()
            self.capture_tool.screenshot_captured.connect(self.on_screenshot_captured)
            self.capture_tool.canceled.connect(self.on_screenshot_canceled)
            self.capture_tool.show()
        except ImportError:
            from src.core.logger import logger
            logger.error("[QuickChat] 无法导入 ScreenCaptureTool")
            self.restore_window()
    
    def on_screenshot_captured(self, file_path):
        """截图完成"""
        self.selected_images.append(file_path)
        self.update_image_preview()
        self.restore_window()
    
    def on_screenshot_canceled(self):
        """截图取消"""
        self.restore_window()
    
    def restore_window(self):
        """恢复窗口"""
        if self.window():
            self.window().show()
            self.window().activateWindow()
    
    def update_image_preview(self):
        """更新图片预览"""
        while self.image_preview_layout.count():
            item = self.image_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.selected_images:
            self.image_preview_widget.hide()
            return
        
        self.image_preview_widget.show()
        
        for img_path in self.selected_images:
            preview_container = QFrame()
            preview_container.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 0, 0, 30);
                    border-radius: 5px;
                    padding: 2px;
                }
            """)
            preview_layout = QHBoxLayout(preview_container)
            preview_layout.setContentsMargins(5, 5, 5, 5)
            preview_layout.setSpacing(5)
            
            img_label = QLabel()
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(scaled_pixmap)
            img_label.setFixedSize(40, 40)
            img_label.setScaledContents(True)
            preview_layout.addWidget(img_label)
            
            remove_btn = TransparentToolButton(FIF.CLOSE, preview_container)
            remove_btn.setFixedSize(16, 16)
            remove_btn.clicked.connect(lambda checked, path=img_path: self.remove_image(path))
            preview_layout.addWidget(remove_btn)
            
            self.image_preview_layout.addWidget(preview_container)
        
        self.image_preview_layout.addStretch()
    
    def remove_image(self, img_path):
        """移除图片"""
        if img_path in self.selected_images:
            self.selected_images.remove(img_path)
            self.update_image_preview()
    
    def load_chat_history(self):
        """加载聊天历史到 UI"""
        from src.core.logger import logger
        
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.message_widgets.clear()
        
        session_id = self.get_or_create_session()
        if not session_id:
            return
        
        db_msgs = self.chat_db.get_messages(session_id)
        
        logger.info(f"[QuickChat] 加载历史消息：session_id={session_id}, 消息数={len(db_msgs)}")
        
        for msg in db_msgs:
            msg_id = msg[0]
            role = msg[1]
            content = msg[2] if msg[2] else ""
            
            if content:
                bubble = QuickMessageBubble(role, content, msg_id, self)
                bubble.delete_requested.connect(self.delete_message)
                bubble.regenerate_requested.connect(self.regenerate_message)
                bubble.speak_requested.connect(self.speak_message)
                self.message_widgets[msg_id] = bubble
                
                insert_index = self.chat_layout.count() - 1
                self.chat_layout.insertWidget(insert_index, bubble)
                
                self.memory_manager.short_term_messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": msg[6] if len(msg) > 6 and msg[6] else datetime.now().isoformat()
                })
    
    def render_markdown(self, text):
        """渲染 Markdown 为 HTML"""
        is_dark = isDarkTheme()
        
        if is_dark:
            style_name = 'one-dark'
            bg_color = "#282c34"
            header_bg = "#21252b"
            border_color = "#181a1f"
            text_color = "#abb2bf"
        else:
            style_name = 'xcode'
            bg_color = "#f6f8fa"
            header_bg = "#e1e4e8"
            border_color = "#d1d5da"
            text_color = "#24292e"
        
        extensions = ['fenced_code', 'tables']
        
        try:
            markdown_html = markdown.markdown(text, extensions=extensions)
            
            def replace_block(match):
                lang = match.group('lang')
                code_content = match.group('code')
                clean_code = html.unescape(code_content)
                
                try:
                    if lang:
                        lexer = get_lexer_by_name(lang)
                    else:
                        lexer = guess_lexer(clean_code)
                except:
                    from pygments.lexers.special import TextLexer
                    lexer = TextLexer()
                
                formatter = HtmlFormatter(style=style_name, noclasses=True)
                highlighted_html = highlight(clean_code, lexer, formatter)
                
                start_idx = highlighted_html.find('<pre')
                end_idx = highlighted_html.rfind('</pre>') + 6
                
                if start_idx != -1:
                    pre_content = highlighted_html[start_idx:end_idx]
                else:
                    pre_content = f'<pre>{code_content}</pre>'
                
                pre_content = re.sub(r'<pre[^>]*>', 
                    f'<pre style="margin: 0; padding: 8px; background-color: {bg_color}; color: {text_color}; white-space: pre-wrap; font-family: Consolas, monospace; border-radius: 4px;">', 
                    pre_content, count=1)
                
                lang_display = lang if lang else "Code"
                
                return (
                    f'<div style="margin: 8px 0; border: 1px solid {border_color}; border-radius: 6px; overflow: hidden;">'
                    f'<div style="background-color: {header_bg}; padding: 6px 12px; border-bottom: 1px solid {border_color};">'
                    f'<span style="color: {text_color}; font-family: sans-serif; font-size: 11px; font-weight: bold;">{lang_display}</span>'
                    f'</div>'
                    f'<div style="background-color: {bg_color}; padding: 0;">{pre_content}</div>'
                    f'</div>'
                )
            
            pattern = r'<pre><code class="language-(?P<lang>\w*)">(?P<code>.*?)</code></pre>'
            markdown_html = re.sub(pattern, replace_block, markdown_html, flags=re.DOTALL)
            
            pattern_no_lang = r'<pre><code>(?P<code>.*?)</code></pre>'
            markdown_html = re.sub(pattern_no_lang, replace_block, markdown_html, flags=re.DOTALL)
            
            custom_css = f"""
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13px; line-height: 1.5; color: {text_color}; }}
                p {{ margin: 0.5em 0; }}
                h1, h2, h3, h4, h5, h6 {{ margin: 0.8em 0 0.4em 0; font-weight: 600; }}
                ul, ol {{ margin: 0.5em 0; padding-left: 1.5em; }}
                li {{ margin: 0.2em 0; }}
                blockquote {{ border-left: 3px solid {border_color}; margin: 0.5em 0; padding-left: 1em; color: #666; }}
                code {{ background-color: {bg_color}; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; font-size: 12px; }}
                table {{ border-collapse: collapse; margin: 0.5em 0; }}
                th, td {{ border: 1px solid {border_color}; padding: 6px 12px; }}
                th {{ background-color: {header_bg}; }}
            </style>
            """
            
            return custom_css + markdown_html
            
        except Exception as e:
            return f"<pre>{text}</pre>"
    
    def add_message_to_ui(self, role, content, msg_id=None):
        """添加消息到 UI"""
        if not content:
            return None
        
        if msg_id is None:
            msg_id = int(uuid.uuid4().hex[:8], 16)
        
        bubble = QuickMessageBubble(role, content, msg_id, self)
        
        bubble.delete_requested.connect(self.delete_message)
        bubble.regenerate_requested.connect(self.regenerate_message)
        bubble.speak_requested.connect(self.speak_message)
        
        self.message_widgets[msg_id] = bubble
        
        insert_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_index, bubble)
        
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )
        
        return msg_id
    
    def delete_message(self, msg_id):
        """删除消息"""
        from src.core.logger import logger
        
        self.chat_db.delete_message(msg_id)
        
        if msg_id in self.message_widgets:
            bubble = self.message_widgets[msg_id]
            self.chat_layout.removeWidget(bubble)
            bubble.deleteLater()
            del self.message_widgets[msg_id]
        
        logger.info(f"[QuickChat] 删除消息：msg_id={msg_id}")
    
    def regenerate_message(self, msg_id):
        """重新生成消息"""
        from src.core.logger import logger
        
        session_id = self.get_or_create_session()
        msgs = self.chat_db.get_messages(session_id)
        
        target_idx = -1
        for i, m in enumerate(msgs):
            if m[0] == msg_id:
                target_idx = i
                break
        
        if target_idx == -1:
            return
        
        w = MessageBox("确认重新生成", "重新生成将会删除此消息及其之后的所有对话记录，确定要继续吗？", self)
        if w.exec_():
            ids_to_delete = [m[0] for m in msgs[target_idx:]]
            for mid in ids_to_delete:
                self.chat_db.delete_message(mid)
                if mid in self.message_widgets:
                    bubble = self.message_widgets[mid]
                    self.chat_layout.removeWidget(bubble)
                    bubble.deleteLater()
                    del self.message_widgets[mid]
            
            self.memory_manager.short_term_messages.clear()
            
            self.load_chat_history()
            
            self.trigger_llm_generation()
    
    def speak_message(self, msg_id, content):
        """朗读消息"""
        clean_content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()
        if clean_content and hasattr(self, 'tts_manager'):
            self.tts_manager.speak(str(msg_id), clean_content)
    
    def trigger_llm_generation(self):
        """触发 LLM 生成"""
        session_id = self.get_or_create_session()
        
        history = self.memory_manager.get_context(session_id)
        
        system_prompt = self.current_system_prompt
        if len(system_prompt) > 1000:
            if "你是 Doro" in system_prompt:
                system_prompt = "你是 Doro，一个可爱的白色小生物。你性格活泼、黏人，喜欢用可爱的语气和表情符号。请用中文回复，保持简短友好。"
        
        history.insert(0, {"role": "system", "content": system_prompt})
        
        from src.core.database import DatabaseManager
        db_manager = DatabaseManager()
        active_model = db_manager.config.get_active_model()
        
        if not active_model or len(active_model) < 6:
            return
        
        api_key = active_model[3] if len(active_model) > 3 else ""
        base_url = active_model[4] if len(active_model) > 4 else "https://api.openai.com/v1"
        model_name = active_model[5] if len(active_model) > 5 else ""
        
        if not api_key or not model_name or not base_url:
            return
        
        self._is_generating = True
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.llm_worker = LLMWorker(
            api_key=api_key,
            base_url=base_url,
            messages=history,
            model=model_name,
            db=self.chat_db,
            is_thinking=0,
            enabled_plugins=[]
        )
        self.llm_worker.finished.connect(self.on_response_received)
        self.llm_worker.error.connect(self.on_error_occurred)
        self.llm_worker.start()
    
    def load_personas(self):
        """加载人格列表"""
        current_text = self.persona_combo.currentText()
        self.persona_combo.clear()
        self.persona_combo.addItem("默认助手")
        self.persona_prompts = ["You are a helpful assistant."]
        self.persona_doro_tools = [False]
        
        if self.persona_db:
            personas = self.persona_db.get_personas()
        else:
            from src.core.database import DatabaseManager
            db_manager = DatabaseManager()
            personas = db_manager.personas.get_personas()
        for p in personas:
            self.persona_combo.addItem(p[1])
            self.persona_prompts.append(p[3])
            self.persona_doro_tools.append(bool(p[5]))
        
        settings = QSettings("DoroPet", "QuickChat")
        last_persona = settings.value("last_persona", "")
        
        if last_persona:
            index = self.persona_combo.findText(last_persona)
            if index >= 0:
                self.persona_combo.setCurrentIndex(index)
                self.on_persona_changed(index)
                return
            elif current_text:
                index = self.persona_combo.findText(current_text)
                if index >= 0:
                    self.persona_combo.setCurrentIndex(index)
                    self.on_persona_changed(index)
                    return
        
        if current_text:
            index = self.persona_combo.findText(current_text)
            if index >= 0:
                self.persona_combo.setCurrentIndex(index)
                self.on_persona_changed(index)
    
    def on_persona_changed(self, index):
        """人格切换"""
        self.current_persona = self.persona_combo.currentText()
        self.current_system_prompt = self.persona_prompts[index]
        
        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue("last_persona", self.current_persona)
    
    def insert_phrase(self, phrase):
        """插入快捷短语"""
        current = self.input_text.toPlainText()
        if current:
            self.input_text.setPlainText(current + " " + phrase)
        else:
            self.input_text.setPlainText(phrase)
    
    def on_quick_phrase_selected(self, index):
        """快捷短语下拉框选择事件"""
        if index == 0:
            return
        
        phrase = self.quick_phrase_combo.currentText()
        self.insert_phrase(phrase)
        
        self.quick_phrase_combo.blockSignals(True)
        self.quick_phrase_combo.setCurrentIndex(0)
        self.quick_phrase_combo.blockSignals(False)
    
    def _toggle_auto_play(self):
        """切换自动播放语音状态"""
        self._auto_play_enabled = not self._auto_play_enabled
        self._update_auto_play_btn_style()
    
    def _update_auto_play_btn_style(self):
        """更新自动播放按钮样式"""
        if self._auto_play_enabled:
            self.auto_play_btn.setIcon(FIF.VOLUME)
            self.auto_play_btn.setToolTip("自动播放语音：开")
        else:
            self.auto_play_btn.setIcon(FIF.MUTE)
            self.auto_play_btn.setToolTip("自动播放语音：关")
    
    def get_or_create_session(self):
        """获取或创建快捷聊天专用会话"""
        if self.current_session_id:
            return self.current_session_id
        
        cursor = self.chat_db.conn.cursor()
        cursor.execute("""
            SELECT id, title FROM sessions 
            WHERE title = ?
        """, ("快捷聊天",))
        
        row = cursor.fetchone()
        if row:
            self.current_session_id = row[0]
            from src.core.logger import logger
            logger.info(f"[QuickChat] 找到快捷聊天会话：id={self.current_session_id}")
            return self.current_session_id
        
        self.current_session_id = self.chat_db.create_session("快捷聊天", self.current_system_prompt)
        from src.core.logger import logger
        logger.info(f"[QuickChat] 创建快捷聊天会话：id={self.current_session_id}")
        return self.current_session_id
    
    def send_message(self):
        """发送消息"""
        if self._is_generating:
            self.stop_generation()
            return
        
        user_input = self.input_text.toPlainText().strip()
        images_json = self.selected_images.copy() if self.selected_images else None
        
        if not user_input and not images_json:
            return
        
        from src.core.logger import logger
        
        session_id = self.get_or_create_session()
        
        logger.info(f"[QuickChat] 当前 session_id={session_id}, current_session_id={self.current_session_id}")
        
        msg_id = self.chat_db.add_message(
            session_id, 
            "user", 
            user_input,
            images=images_json
        )
        
        logger.info(f"[QuickChat] 用户消息已保存：msg_id={msg_id}, session_id={session_id}")
        
        self.add_message_to_ui("user", user_input, msg_id)
        
        self.input_text.clear()
        self.selected_images.clear()
        self.update_image_preview()
        
        self._is_generating = True
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        from src.core.logger import logger
        
        self.memory_manager.add_message("user", user_input, session_id)
        
        history = self.memory_manager.get_context(session_id)
        
        system_prompt = self.current_system_prompt
        if len(system_prompt) > 1000:
            if "你是 Doro" in system_prompt:
                system_prompt = "你是 Doro，一个可爱的白色小生物。你性格活泼、黏人，喜欢用可爱的语气和表情符号。请用中文回复，保持简短友好。"
        
        history.insert(0, {"role": "system", "content": system_prompt})
        
        logger.info(f"[QuickChat] 使用智能记忆系统，上下文消息数：{len(history)}")
        
        logger.info(f"[QuickChat] ====== 发送消息给 AI ======")
        logger.info(f"[QuickChat] 消息总数：{len(history)}")
        for i, msg in enumerate(history):
            content_preview = msg['content'][:300] if len(msg['content']) > 300 else msg['content']
            content_preview = content_preview.replace('\n', '\\n')
            logger.info(f"[QuickChat]   [{i}] {msg['role']}: {content_preview}...")
        logger.info(f"[QuickChat] ==========================")
        
        from src.core.database import DatabaseManager
        db_manager = DatabaseManager()
        active_model = db_manager.config.get_active_model()
        
        logger.info(f"[QuickChat] 获取活动模型：{active_model}")
        
        if not active_model or len(active_model) < 6:
            error_msg = "错误：请先在【模型配置】页面添加并选择一个有效的模型！"
            logger.error(f"[QuickChat] 活动模型配置无效：active_model={active_model}")
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        api_key = active_model[3] if len(active_model) > 3 else ""
        base_url = active_model[4] if len(active_model) > 4 else "https://api.openai.com/v1"
        model_name = active_model[5] if len(active_model) > 5 else ""
        
        logger.info(f"[QuickChat] 使用模型：{model_name}, base_url: {base_url[:30] if base_url else 'None'}..., api_key: {api_key[:10] if api_key else 'None'}...")
        
        if not api_key or not model_name or not base_url:
            error_msg = "错误：当前模型配置不完整（缺少 API Key、Base URL 或模型名称），请在【模型配置】页面重新配置！"
            logger.error(f"[QuickChat] 模型配置不完整：api_key={bool(api_key)}, base_url={bool(base_url)}, model_name={bool(model_name)}")
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        self.llm_worker = LLMWorker(
            api_key=api_key,
            base_url=base_url,
            messages=history,
            model=model_name,
            db=self.chat_db,
            is_thinking=0,
            enabled_plugins=[]
        )
        self.llm_worker.finished.connect(self.on_response_received)
        self.llm_worker.error.connect(self.on_error_occurred)
        self.llm_worker.start()
    
    def on_response_received(self, content, reasoning, tool_calls, generated_images):
        """接收 AI 响应"""
        if not content:
            content = reasoning if reasoning else ""
        
        if not content:
            error_msg = "错误：AI 未生成任何内容"
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        session_id = self.get_or_create_session()
        
        msg_id = self.chat_db.add_message(
            session_id,
            "assistant",
            content,
            images=None
        )
        
        self.memory_manager.add_message("assistant", content, session_id)
        
        self.add_message_to_ui("assistant", content, msg_id)
        
        if self._auto_play_enabled:
            clean_content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()
            if clean_content and hasattr(self, 'tts_manager'):
                self.tts_manager.speak(str(msg_id), clean_content)
        
        self._is_generating = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def on_error_occurred(self, error):
        """错误处理"""
        from src.core.logger import logger
        logger.error(f"[QuickChat] LLM 错误：{error}")
        
        self._is_generating = False
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.add_message_to_ui("assistant", f"⚠️ 生成失败：{str(error)}")
    
    def stop_generation(self):
        """停止生成"""
        if hasattr(self, 'llm_worker') and self.llm_worker.isRunning():
            self.llm_worker.stop()
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def load_settings(self):
        """加载设置"""
        settings = QSettings("DoroPet", "QuickChat")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(550, 800)
        
        auto_play = settings.value("auto_play_voice", False, type=bool)
        self._auto_play_enabled = auto_play
        self._update_auto_play_btn_style()
    
    def update_theme(self):
        """更新主题"""
        is_dark = isDarkTheme()
        
        if is_dark:
            setTheme(Theme.DARK)
            self.main_container.setStyleSheet("""
                QWidget#mainContainer {
                    background-color: rgba(32, 32, 32, 220);
                    border-radius: 10px;
                }
                QScrollArea {
                    background-color: rgba(0, 0, 0, 80);
                }
            """)
            self.chat_scroll.setStyleSheet("""
                QScrollArea {
                    background-color: rgba(20, 20, 20, 120);
                    border: 1px solid rgba(255, 255, 255, 20);
                    border-radius: 8px;
                }
                QScrollBar:vertical {
                    background-color: rgba(255, 255, 255, 30);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(255, 255, 255, 80);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(255, 255, 255, 120);
                }
            """)
        else:
            setTheme(Theme.LIGHT)
            self.main_container.setStyleSheet("""
                QWidget#mainContainer {
                    background-color: rgba(255, 255, 255, 180);
                    border-radius: 10px;
                    border: 1px solid rgba(0, 0, 0, 30);
                }
                QScrollArea {
                    background-color: rgba(255, 255, 255, 100);
                }
            """)
            self.chat_scroll.setStyleSheet("""
                QScrollArea {
                    background-color: rgba(255, 255, 255, 120);
                    border: 1px solid rgba(0, 0, 0, 20);
                    border-radius: 8px;
                }
                QScrollBar:vertical {
                    background-color: rgba(0, 0, 0, 30);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(0, 0, 0, 80);
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(0, 0, 0, 120);
                }
            """)
        
        self.load_chat_history()
        
        if hasattr(self, 'title_label'):
            if is_dark:
                self.title_label.setStyleSheet("""
                    color: rgba(255, 255, 255, 220);
                    font-size: 14px;
                    font-weight: bold;
                """)
            else:
                self.title_label.setStyleSheet("""
                    color: rgba(0, 0, 0, 200);
                    font-size: 14px;
                    font-weight: bold;
                """)
    
    def closeEvent(self, event):
        """保存设置并隐藏"""
        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("auto_play_voice", self._auto_play_enabled)
        self.hide()
        event.ignore()


from .quick_chat_window import QuickChatWindow
