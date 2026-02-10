import sys
import sqlite3
import datetime
import base64
import os
import tempfile
import uuid
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QDialog, QFormLayout, QFrame, QSizePolicy, QMenu,
                             QListWidgetItem, QToolButton, QGraphicsOpacityEffect, QFileDialog, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QFont, QDesktopServices, QClipboard, QPixmap, QIcon, QPalette, QColor, QMovie, QImage
import re

from qfluentwidgets import (ListWidget, TextEdit, LineEdit, 
                            PrimaryPushButton, PushButton, ScrollArea, 
                            StrongBodyLabel, BodyLabel, FluentIcon, MessageBox, ComboBox,
                            ToolButton, isDarkTheme, themeColor)

from src.core.database import ChatDatabase
from src.services.llm_service import LLMWorker
from src.core.voice import VoiceAssistant
from src.core.tts import TTSManager
from src.resource_utils import resource_path
from src.core.logger import logger

# ---------------------------------------------------------
# Part 3: UI Components
# ---------------------------------------------------------

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
        self.layout.setSpacing(5)

        # Header (Clickable to toggle)
        self.header_btn = PushButton(FluentIcon.chevron_down, "思考过程 (点击展开)", self)
        self.header_btn.setFixedHeight(30)
        self.header_btn.setObjectName("thinkingHeader")
        self.header_btn.clicked.connect(self.toggle_content)
        
        # Content
        self.content_label = QLabel(thought_content, self)
        self.content_label.setWordWrap(True)
        self.content_label.setObjectName("thinkingContent")
        self.content_label.hide() # Default hidden

        self.layout.addWidget(self.header_btn)
        self.layout.addWidget(self.content_label)
        
    def toggle_content(self):
        if self.content_label.isVisible():
            self.content_label.hide()
            self.header_btn.setText("思考过程 (点击展开)")
            self.header_btn.setIcon(FluentIcon.CHEVRON_DOWN)
        else:
            self.content_label.show()
            self.header_btn.setText("思考过程 (点击收起)")
            self.header_btn.setIcon(FluentIcon.CHEVRON_UP)

class ChatTextEdit(QTextEdit):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(0)
        self.setObjectName("chatContent")
        self.setContextMenuPolicy(Qt.NoContextMenu)
        
        # Force transparency via Palette and Viewport attributes
        # This is critical to allow the parent QFrame background to show through
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.Window, QColor(0, 0, 0, 0))
        self.setPalette(palette)
        
        self.viewport().setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Explicitly set transparent background in stylesheet
        self.setStyleSheet("background: transparent; background-color: transparent; border: none;")
        
        font = QFont("Microsoft YaHei")
        font.setPixelSize(14)
        self.setFont(font)
        
        self.setMarkdown(text)
        self.document().contentsChanged.connect(self.adjust_height)
        
    def adjust_height(self):
        width = self.viewport().width()
        if width <= 0:
            width = self.width()
            
        if width > 0:
            self.document().setTextWidth(width)
            
        doc_height = self.document().size().height()
        # Add a small buffer and ensure minimum height
        target_height = int(doc_height + 10)
        if target_height < 30: target_height = 30
        
        if self.height() != target_height:
            self.setFixedHeight(target_height)
        
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

class MessageBubble(QFrame):
    def __init__(self, role, content, msg_id, parent_window, images=None):
        super().__init__()
        self.role = role.lower() if role else "user"
        self.content = content
        self.msg_id = msg_id
        self.parent_window = parent_window 
        self.images = images or []
        
        # self.setFrameShape(QFrame.NoFrame)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Container for style
        self.container = QFrame(self)
        self.container.setObjectName(f"messageContainer_{self.role}")
        print(f"messageContainer_{self.role}")
        # self.container.setProperty("role", self.role)
        # Ensure the container paints its background for QSS
        self.container.setAttribute(Qt.WA_StyledBackground, True)
        # self.container.setAutoFillBackground(True)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        # 允许容器根据内容自动拉伸高度，宽度由布局控制
        self.container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        
        if role == "user":
            self.layout.addWidget(self.container, 0, Qt.AlignRight)
        else:
            self.layout.addWidget(self.container, 0, Qt.AlignLeft)

        # --- Display Images ---
        if self.images:
            # Container for images (no scroll area, let it expand)
            img_content = QWidget()
            img_content.setStyleSheet("background-color: transparent;")
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

        # Parse content for <think> tags
        thought_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        
        if thought_match:
            thought_text = thought_match.group(1).strip()
            display_text = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            # Add Thinking Widget
            if thought_text:
                self.thinking_widget = ThinkingWidget(thought_text, self.container)
                self.container_layout.addWidget(self.thinking_widget)
        else:
            display_text = content.strip()

        # Use custom ChatTextEdit
        self.text_label = ChatTextEdit(display_text, self.container)
        
        self.container_layout.addWidget(self.text_label)

        # --- Action Widget (Hidden opacity by default, but occupies space) ---
        self.action_widget = QWidget(self)
        self.action_layout = QHBoxLayout(self.action_widget)
        self.action_layout.setContentsMargins(0, 5, 0, 0)
        self.action_layout.setSpacing(5)
        
        # Action buttons will be styled via QSS using ID "chatActionButton"
        
        # Copy Button
        self.btn_copy = ToolButton(FluentIcon.COPY, self.action_widget)
        self.btn_copy.setFixedSize(20, 20)
        # self.btn_copy.setToolTip("复制")
        self.btn_copy.setObjectName("chatActionButton")
        self.btn_copy.setIconSize(QSize(14, 14))
        self.btn_copy.clicked.connect(self.copy_content)
        self.action_layout.addWidget(self.btn_copy)
        
        # Delete Button
        self.btn_delete = ToolButton(FluentIcon.DELETE, self.action_widget)
        self.btn_delete.setFixedSize(20, 20)
        # self.btn_delete.setToolTip("删除")
        self.btn_delete.setObjectName("chatActionButton")
        self.btn_delete.setIconSize(QSize(14, 14))
        self.btn_delete.clicked.connect(lambda: self.parent_window.delete_message(self.msg_id))
        self.action_layout.addWidget(self.btn_delete)
        
        if role == "assistant":
            # Regenerate Button
            self.btn_regen = ToolButton(FluentIcon.SYNC, self.action_widget)
            self.btn_regen.setFixedSize(20, 20)
            # self.btn_regen.setToolTip("重新生成")
            self.btn_regen.setObjectName("chatActionButton")
            self.btn_regen.setIconSize(QSize(14, 14))
            self.btn_regen.clicked.connect(lambda: self.parent_window.regenerate_message(self.msg_id))
            self.action_layout.addWidget(self.btn_regen)

            # TTS Read Button
            self.btn_read = ToolButton(FluentIcon.PLAY, self.action_widget)
            self.btn_read.setFixedSize(20, 20)
            # self.btn_read.setToolTip("朗读")
            self.btn_read.setObjectName("chatActionButton")
            self.btn_read.setIconSize(QSize(14, 14))
            self.btn_read.clicked.connect(lambda: self.parent_window.speak_message(self.msg_id, self.content))
            self.action_layout.addWidget(self.btn_read)

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
        # Limit container max width to 85% of bubble width to ensure wrapping and aesthetics
        if self.parent():
            max_w = int(self.width() * 0.85)
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
        self.parent_window.show_message_context_menu(self.msg_id, self.role, self.content, event.globalPos())

    def update_content(self, content):
        self.content = content
        
        # Parse content for <think> tags
        thought_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        
        if thought_match:
            thought_text = thought_match.group(1).strip()
            display_text = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            if hasattr(self, 'thinking_widget') and self.thinking_widget:
                self.thinking_widget.content_label.setText(thought_text)
            elif thought_text:
                # Create thinking widget if it doesn't exist
                self.thinking_widget = ThinkingWidget(thought_text, self.container)
                self.container_layout.insertWidget(0, self.thinking_widget)
        else:
            display_text = content.strip()

        self.text_label.setPlainText(display_text)
        
        # Trigger resize to ensure wrapping
        if self.parent():
            max_w = int(self.width() * 0.85)
            self.container.setMaximumWidth(max_w)
        
        # Notify layout about content change
        self.text_label.adjust_height()
        self.container.updateGeometry()
        self.updateGeometry()


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
        self.current_system_prompt = ""
        self.streaming_bubble = None
        self.thinking_bubble = None
        self.streaming_content = ""
        self.selected_images = []
        
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

    def update_voice_ui_visibility(self):
        # Check if voice is enabled in settings
        settings = self.db.get_voice_settings()
        if settings:
            is_enabled = bool(settings[0])
            self.btn_voice.setVisible(is_enabled)
            
            # If disabled, ensure assistant is stopped
            if not is_enabled and self.voice_assistant.isRunning():
                self.toggle_voice_assistant() # This stops it
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
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        btn_new_chat = PushButton(FluentIcon.ADD, "新建会话", left_panel)
        btn_new_chat.clicked.connect(self.create_new_session)
        
        self.session_list = ListWidget(left_panel)
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
        
        self.persona_combo = ComboBox(right_panel)
        self.persona_combo.setPlaceholderText("选择一个人格...")
        self.persona_prompts = []  # Store prompts separately to avoid itemData issues
        self.load_personas_to_combo()
        self.persona_combo.currentIndexChanged[int].connect(self.on_persona_changed)
        
        btn_refresh = PushButton(FluentIcon.SYNC, "刷新", right_panel)
        btn_refresh.setFixedWidth(80)
        btn_refresh.clicked.connect(self.load_personas_to_combo)
        
        prompt_layout.addWidget(self.persona_combo, 1)
        prompt_layout.addWidget(btn_refresh)
        
        # 2. 中间：滚动聊天区
        self.scroll_area = ScrollArea(right_panel)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.chat_content_widget = QWidget()
        self.chat_content_widget.setStyleSheet("background-color: transparent;")
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

        # 模型选择下拉框
        self.model_combo = ComboBox(right_panel)
        self.model_combo.setPlaceholderText("选择模型")
        self.model_combo.setFixedWidth(150) # 固定宽度
        self.load_models_to_combo()
        
        # 发送按钮
        self.btn_send = PrimaryPushButton(FluentIcon.SEND, "发送", right_panel)
        self.btn_send.setFixedSize(100, 32) # 调整为更扁平的标准按钮尺寸
        self.btn_send.clicked.connect(self.send_message)
        
        bottom_toolbar_layout.addWidget(self.model_combo)
        bottom_toolbar_layout.addWidget(self.btn_send)
        
        # 将文本框和工具栏加入主输入容器
        input_container_layout.addWidget(self.input_text)
        input_container_layout.addLayout(bottom_toolbar_layout)

        right_layout.addLayout(prompt_layout)
        right_layout.addWidget(self.scroll_area)
        right_layout.addLayout(input_container_layout)

        # 布局
        left_panel.setFixedWidth(250)
        main_layout.addWidget(left_panel)
        
        # Add Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #E0E0E0; border: none;")
        main_layout.addWidget(separator)
        
        main_layout.addWidget(right_panel)

    def showEvent(self, event):
        self.load_models_to_combo()
        super().showEvent(event)

    def load_sessions_list(self):
        self.session_list.clear()
        sessions = self.db.get_sessions()
        for sess in sessions:
            item = QListWidgetItem(sess[1], self.session_list) 
            item.setData(Qt.UserRole, sess[0])
            item.setData(Qt.UserRole + 1, sess[2])
            self.session_list.addItem(item)

    def create_new_session(self):
        session_id = self.db.create_session()
        self.load_sessions_list()
        self.session_list.setCurrentRow(0)
        self.on_session_selected(self.session_list.item(0))
        self.input_text.setFocus()

    def on_session_selected(self, item):
        if not item: return
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
        
        # Default
        self.persona_combo.addItem("默认助手")
        self.persona_prompts.append("You are a helpful assistant.")
        
        personas = self.db.get_personas()
        for p in personas:
            # p: id, name, desc, system_prompt, avatar
            self.persona_combo.addItem(p[1])
            self.persona_prompts.append(p[3])
            
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

    def load_models_to_combo(self):
        current_data = self.model_combo.currentData()
        self.model_combo.clear()
        models = self.db.get_models()
        # models: id, name, provider, api_key, base_url, model_name, is_active
        
        active_index = 0
        target_index = -1

        for i, m in enumerate(models):
            data = (m[3], m[4], m[5]) # api_key, base_url, model_name
            self.model_combo.addItem(m[1], userData=data)
            if m[6] == 1: # is_active
                active_index = i
            if current_data and data == current_data:
                target_index = i
        
        if target_index != -1:
            self.model_combo.setCurrentIndex(target_index)
        elif models:
            self.model_combo.setCurrentIndex(active_index)
        else:
            # Fallback if no models in DB (shouldn't happen if migrated, but just in case)
            self.model_combo.addItem("Default (OpenAI)")
            # Try to read from QSettings as fallback?
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")
            self.model_combo.setItemData(0, (api_key, base_url, model))


    def show_session_context_menu(self, pos):
        item = self.session_list.itemAt(pos)
        if not item: return
        
        menu = QMenu()
        delete_action = menu.addAction("删除会话")
        action = menu.exec_(self.session_list.mapToGlobal(pos))
        
        if action == delete_action:
            sess_id = item.data(Qt.UserRole)
            self.db.delete_session(sess_id)
            self.load_sessions_list()
            self.clear_chat_area()
            self.current_session_id = None

    def clear_chat_area(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.chat_layout.addStretch() 

    def load_chat_history(self):
        self.clear_chat_area()
        if not self.current_session_id: return
        
        item = self.chat_layout.takeAt(0) 
        if item: del item

        messages = self.db.get_messages(self.current_session_id)
        for msg_id, role, content, images in messages:
            self.add_message_to_ui(role, content, msg_id, images)
        
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

    def update_theme(self):
        """Update styles when theme changes"""
        # Update voice button style based on current state
        # state = "idle"
        # if hasattr(self, 'voice_assistant') and self.voice_assistant.state == "LISTENING":
        #      state = "listening"
        
        # self.btn_voice.setStyleSheet(self.get_voice_button_style(state))
        
        # We can also update other UI elements here if needed
        pass

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
        self.tts_manager.speak(msg_id, content)

    def on_tts_started(self, msg_id):
        bubble = self.get_bubble_by_id(msg_id)
        if bubble and hasattr(bubble, 'btn_read'):
            bubble.btn_read.setIcon(FluentIcon.PAUSE) 
            bubble.btn_read.setToolTip("停止播放")

    def on_tts_stopped(self, msg_id):
        bubble = self.get_bubble_by_id(msg_id)
        if bubble and hasattr(bubble, 'btn_read'):
            bubble.btn_read.setIcon(FluentIcon.PLAY)
            bubble.btn_read.setToolTip("朗读")

    def on_tts_error(self, msg_id, error_msg):
        self.on_tts_stopped(msg_id)
        logger.error(f"TTS Error for msg {msg_id}: {error_msg}")
        bubble = self.get_bubble_by_id(msg_id)
        if bubble and hasattr(bubble, 'btn_read'):
             bubble.btn_read.setToolTip(f"错误: {error_msg}")

    def get_bubble_by_id(self, msg_id):
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, MessageBubble) and widget.msg_id == msg_id:
                    return widget
        return None

    def add_message_to_ui(self, role, content, msg_id, images=None):
        bubble = MessageBubble(role, content, msg_id, self, images)
        count = self.chat_layout.count()
        if count > 0:
            self.chat_layout.insertWidget(count, bubble)
        else:
            self.chat_layout.addWidget(bubble)
            
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
                 lbl.setStyleSheet("border: 1px solid #ccc;")
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

    def send_message(self):
        user_input = self.input_text.toPlainText().strip()
        if (not user_input and not self.selected_images) or not self.current_session_id:
            return
        
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

    def trigger_llm_generation(self):
        logger.info("Starting LLM generation...")
        self.btn_send.setEnabled(False)
        self.btn_send.setText("...")
        
        # Get model config from combo
        model_data = self.model_combo.currentData()
        
        if model_data:
            api_key, base_url, model = model_data
        else:
            # Fallback to QSettings if combo is empty or failed
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")

        if not api_key:
            w = MessageBox("提示", "请先在【模型配置】页面添加并选择一个有效的模型！", self)
            w.exec_()
            self.btn_send.setEnabled(True)
            self.btn_send.setText("发送")
            return

        history = [{"role": "system", "content": self.current_system_prompt}]
        db_msgs = self.db.get_messages(self.current_session_id)
        for _, role, content, images in db_msgs:
            if not images:
                history.append({"role": role, "content": content})
            else:
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
                            }
                        })
                history.append({"role": role, "content": content_list})

        self.worker = LLMWorker(api_key, base_url, history, model, self.db)
        self.worker.chunk_received.connect(self.handle_llm_chunk)
        self.worker.finished.connect(self.handle_llm_response)
        self.worker.error.connect(self.handle_llm_error)
        
        # Reset streaming state
        self.streaming_bubble = None
        self.streaming_content = ""
        
        # Add thinking bubble
        stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
        self.thinking_bubble = ThinkingBubble(self)
        self.chat_layout.addWidget(self.thinking_bubble)
        if stretch_item: self.chat_layout.addItem(stretch_item)
        
        self.scroll_to_bottom()
        
        self.worker.start()

    def handle_llm_chunk(self, chunk):
        # Remove thinking bubble if exists
        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        self.streaming_content += chunk
        
        if not self.streaming_bubble:
            # Temporarily remove stretch item to insert bubble before it
            stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
            
            # Create a new bubble for streaming with dummy ID
            self.streaming_bubble = MessageBubble("assistant", "", -1, self)
            self.chat_layout.addWidget(self.streaming_bubble)
            
            if stretch_item: self.chat_layout.addItem(stretch_item)
            
        self.streaming_bubble.update_content(self.streaming_content)
        self.scroll_to_bottom()

    def handle_llm_response(self, content, generated_images=[]):
        # Remove thinking bubble if exists (in case of non-streaming or error handling logic flow)
        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        # If we were streaming, we already have a bubble.
        if self.streaming_bubble:
            # Save to DB now
            msg_id = self.db.add_message(self.current_session_id, "assistant", content, generated_images)
            
            # Update the bubble's ID and images
            self.streaming_bubble.msg_id = msg_id
            
            # If there are images, we might need to refresh the bubble to show them
            # because streaming_bubble was created without images.
            if generated_images:
                # Easiest way is to remove and re-add, or update bubble class to support dynamic image adding
                # But MessageBubble takes images in init.
                # Let's replace the streaming bubble with a proper one.
                self.streaming_bubble.deleteLater()
                self.streaming_bubble = None
                self.add_message_to_ui("assistant", content, msg_id, generated_images)
            
            # Reset streaming state
            self.streaming_bubble = None
            self.streaming_content = ""
        else:
            # Fallback for non-streaming
            stretch_item = self.chat_layout.takeAt(self.chat_layout.count() - 1)
            
            msg_id = self.db.add_message(self.current_session_id, "assistant", content, generated_images)
            self.add_message_to_ui("assistant", content, msg_id, generated_images)
            
            if stretch_item: self.chat_layout.addItem(stretch_item)
        
        QApplication.processEvents()
        self.scroll_to_bottom()
        
        self.btn_send.setEnabled(True)
        self.btn_send.setText("发送")

    def handle_llm_error(self, err_msg):
        logger.error(f"LLM Error: {err_msg}")
        # Remove thinking bubble if exists
        if self.thinking_bubble:
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        w = MessageBox("API 错误", err_msg, self)
        w.exec_()
        self.btn_send.setEnabled(True)
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
