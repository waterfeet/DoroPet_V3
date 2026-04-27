import sys
import re
import uuid
import os
import base64
import threading
import datetime
import requests
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTextEdit,
                             QPushButton, QLabel, QComboBox, QFrame, QApplication,
                             QScrollArea, QButtonGroup, QSizePolicy, QTextBrowser,
                             QGraphicsOpacityEffect, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer, QSize, QUrl
from PyQt5.QtGui import QFont, QPixmap, QIcon, QImage, QTextDocument
from qfluentwidgets import (PushButton, PrimaryPushButton, TransparentToolButton, ToolButton, FluentIcon as FIF,
                            CardWidget, StrongBodyLabel, BodyLabel, setTheme, Theme,
                            isDarkTheme, TransparentTogglePushButton, MessageBox,
                            LineEdit, ComboBox, TextEdit, InfoBar, InfoBarPosition)

from src.core.logger import logger
from src.core.quick_chat_state import get_quick_chat_state, QuickChatState, GenerationState
from src.core.quick_chat_dependencies import get_quick_chat_deps
from src.core.quick_chat_service import get_quick_chat_service, QuickChatService
from src.core.quick_chat_errors import ErrorHandler, create_error_from_exception, QuickChatErrorType
from src.services.llm_service import LLMWorker
from datetime import datetime
from src.resource_utils import resource_path


class NetworkImageTextBrowser(QTextBrowser):
    imageLoaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from src.core.image_cache_manager import get_image_cache_manager
        self._cache_manager = get_image_cache_manager()
        self._loading_images = set()
        self._pending_images = {}
        self.setOpenLinks(False)
        self.setOpenExternalLinks(True)
        self.anchorClicked.connect(self._on_anchor_clicked)
        self._refresh_scheduled = False

    def _on_anchor_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith('http://') or url_str.startswith('https://'):
            import webbrowser
            webbrowser.open(url_str)

    def loadResource(self, resource_type, url):
        if resource_type == QTextDocument.ImageResource:
            url_str = url.toString()

            cached_path = self._cache_manager.get_cached_path(url_str)
            if cached_path and os.path.exists(cached_path):
                pixmap = QPixmap(cached_path)
                if not pixmap.isNull():
                    return pixmap

            if url_str.startswith('http://') or url_str.startswith('https://'):
                if url_str not in self._loading_images:
                    self._loading_images.add(url_str)
                    self._load_network_image(url_str)
                return QPixmap()

        return super().loadResource(resource_type, url)

    def _load_network_image(self, url_str):
        def download():
            try:
                logger.debug(f"[NetworkImageTextBrowser] 开始加载图片：url={url_str[:100]}...")
                
                if url_str.startswith('data:image'):
                    import re
                    match = re.match(r'data:image/([^;]+);base64,(.+)', url_str)
                    if match:
                        ext = match.group(1)
                        b64_data = match.group(2)
                        image_data = base64.b64decode(b64_data)

                        logger.info(f"[NetworkImageTextBrowser] base64 图片直接解码显示，不缓存")
                        import tempfile
                        import uuid
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        filename = f"temp_{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"
                        temp_path = os.path.join(tempfile.gettempdir(), "doropet_images", filename)
                        temp_dir = os.path.dirname(temp_path)
                        if not os.path.exists(temp_dir):
                            os.makedirs(temp_dir)
                        with open(temp_path, 'wb') as f:
                            f.write(image_data)
                        logger.info(f"[NetworkImageTextBrowser] 临时文件：{temp_path}")
                        QTimer.singleShot(0, lambda: self._on_image_loaded(url_str, temp_path))
                        return
                else:
                    logger.debug(f"[NetworkImageTextBrowser] 检查 HTTP 图片缓存...")
                    cached_path = self._cache_manager.get_cached_path(url_str)
                    if cached_path and os.path.exists(cached_path):
                        logger.debug(f"[NetworkImageTextBrowser] 缓存命中：{cached_path}")
                        QTimer.singleShot(0, lambda: self._on_image_loaded(url_str, cached_path))
                        return

                    logger.debug(f"[NetworkImageTextBrowser] 缓存未命中，开始下载...")

                    response = requests.get(url_str, timeout=15)
                    response.raise_for_status()

                    image_data = response.content

                    save_dir = self._cache_manager.cache_dir
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir)

                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    ext = ".jpg"
                    if ".png" in url_str.lower():
                        ext = ".png"
                    elif ".gif" in url_str.lower():
                        ext = ".gif"
                    elif ".webp" in url_str.lower():
                        ext = ".webp"

                    filename = f"cached_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
                    local_path = os.path.join(save_dir, filename)

                    with open(local_path, 'wb') as f:
                        f.write(image_data)

                    self._cache_manager.add_image(url_str, local_path)
                    logger.debug(f"[NetworkImageTextBrowser] 保存到：{local_path}")
                    QTimer.singleShot(0, lambda: self._on_image_loaded(url_str, local_path))

            except Exception as e:
                logger.error(f"[NetworkImageTextBrowser] Failed to load image: {e}")
                QTimer.singleShot(0, lambda: self._loading_images.discard(url_str))

        thread = threading.Thread(target=download, daemon=True)
        thread.start()

    def _on_image_loaded(self, url_str, local_path):
        if os.path.exists(local_path):
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                self._cache_manager.add_image(url_str, local_path)
                doc = self.document()
                doc.addResource(QTextDocument.ImageResource, QUrl(url_str), pixmap)
                self._schedule_refresh()
                self.imageLoaded.emit()

        self._loading_images.discard(url_str)

    def _schedule_refresh(self):
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        QTimer.singleShot(50, self._do_refresh)

    def _do_refresh(self):
        html = self.toHtml()
        self.setHtml(html)
        self._refresh_scheduled = False


class QuickMessageBubble(QFrame):
    delete_requested = pyqtSignal(int)
    regenerate_requested = pyqtSignal(int)
    speak_requested = pyqtSignal(int, str)
    speak_pause_requested = pyqtSignal(int)
    speak_resume_requested = pyqtSignal(int)
    speak_restart_requested = pyqtSignal(int, str)

    PLAYBACK_STOPPED = 0
    PLAYBACK_PLAYING = 1
    PLAYBACK_PAUSED = 2

    def __init__(self, role, content, msg_id, parent_window=None):
        super().__init__()
        self.role = role
        self.content = content
        self.msg_id = msg_id
        self.parent_window = parent_window
        self._text_browser = None
        self._playback_state = self.PLAYBACK_STOPPED

        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background-color: transparent;")

        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.container = QFrame(self)
        self.container.setAttribute(Qt.WA_StyledBackground, True)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)
        self.container_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.container.setMinimumWidth(300)

        is_dark = isDarkTheme()

        if self.role == "user":
            self.container.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 120, 215, 180);
                    color: white;
                    border-radius: 10px;
                }
            """)

            self._setup_user_content(is_dark)
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

            self._setup_assistant_content(is_dark)

        self._setup_action_buttons(is_dark)

        self.main_layout.addWidget(self.container)
        self.main_layout.addWidget(self.action_widget, 0, Qt.AlignRight if self.role == "user" else Qt.AlignLeft)

        self.opacity_effect = QGraphicsOpacityEffect(self.action_widget)
        self.opacity_effect.setOpacity(0.0)
        self.action_widget.setGraphicsEffect(self.opacity_effect)

    def _setup_user_content(self, is_dark):
        content_widget = QWidget(self.container)
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        content_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        if isinstance(self.content, list):
            text_parts = []
            image_parts = []

            for part in self.content:
                if isinstance(part, dict):
                    if part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                    elif part.get('type') == 'image_url':
                        image_parts.append(part)

            if text_parts:
                text_label = QLabel('\n'.join(text_parts))
                text_label.setWordWrap(True)
                text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                text_label.setStyleSheet("background-color: transparent; color: white;")
                content_layout.addWidget(text_label)

            if image_parts:
                self._add_image_grid(content_layout, image_parts, is_dark)
        else:
            content_label = QLabel(self.content)
            content_label.setWordWrap(True)
            content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            content_label.setStyleSheet("background-color: transparent; color: white;")
            content_layout.addWidget(content_label)

        self.container_layout.addWidget(content_widget)

    def _setup_assistant_content(self, is_dark):
        from src.core.message_parser import MessageParser, ContentType

        if isinstance(self.content, list):
            text_parts = []
            image_parts = []

            for part in self.content:
                if isinstance(part, dict):
                    if part.get('type') == 'text':
                        text_parts.append(part.get('text', ''))
                    elif part.get('type') == 'image_url':
                        image_parts.append(part)

            if text_parts:
                text_content = '\n'.join(text_parts)
                text_html = self.parent_window.render_markdown(text_content) if self.parent_window else f"<pre>{text_content}</pre>"
                text_browser = QTextBrowser()
                text_browser.setOpenExternalLinks(True)
                text_browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
                text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                text_browser.document().setDocumentMargin(0)
                text_browser.installEventFilter(self)
                if is_dark:
                    text_browser.setStyleSheet("""
                        QTextBrowser {
                            background-color: transparent;
                            color: rgba(255, 255, 255, 220);
                            border: none;
                        }
                    """)
                else:
                    text_browser.setStyleSheet("""
                        QTextBrowser {
                            background-color: transparent;
                            color: rgba(0, 0, 0, 200);
                            border: none;
                        }
                    """)
                text_browser.setHtml(text_html)
                self._text_browser = text_browser
                self.container_layout.addWidget(text_browser)

            if image_parts:
                for part in image_parts:
                    img_url = part.get('image_url', {})
                    if isinstance(img_url, dict):
                        img_url = img_url.get('url', '')
                    if img_url:
                        from src.ui.pages.chat_interface import NetworkImageLabel
                        img_label = NetworkImageLabel(img_url, None, max_width=400)
                        self.container_layout.addWidget(img_label)
            return

        thinking_text, display_text = MessageParser.extract_thinking(self.content)
        blocks = MessageParser._parse_display_content(display_text)

        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        for block in blocks:
            if block.is_code():
                code_browser = QTextBrowser()
                code_browser.setOpenExternalLinks(True)
                code_browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
                code_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                code_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                code_browser.document().setDocumentMargin(0)
                code_browser.installEventFilter(self)
                if is_dark:
                    code_browser.setStyleSheet("""
                        QTextBrowser {
                            background-color: transparent;
                            color: rgba(255, 255, 255, 220);
                            border: none;
                        }
                    """)
                else:
                    code_browser.setStyleSheet("""
                        QTextBrowser {
                            background-color: transparent;
                            color: rgba(0, 0, 0, 200);
                            border: none;
                        }
                    """)
                code_html = self.parent_window.render_markdown(f"```{block.language or ''}\n{block.content}\n```") if self.parent_window else f"<pre>{block.content}</pre>"
                code_browser.setHtml(code_html)
                self._text_browser = code_browser
                content_layout.addWidget(code_browser)
            elif block.is_image():
                img_url = block.image_url
                if img_url:
                    from src.ui.pages.chat_interface import NetworkImageLabel
                    img_label = NetworkImageLabel(img_url, content_container, max_width=400)
                    content_layout.addWidget(img_label)
            else:
                text_browser = QTextBrowser()
                text_browser.setOpenExternalLinks(True)
                text_browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
                text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                text_browser.document().setDocumentMargin(0)
                text_browser.installEventFilter(self)
                if is_dark:
                    text_browser.setStyleSheet("""
                        QTextBrowser {
                            background-color: transparent;
                            color: rgba(255, 255, 255, 220);
                            border: none;
                        }
                    """)
                else:
                    text_browser.setStyleSheet("""
                        QTextBrowser {
                            background-color: transparent;
                            color: rgba(0, 0, 0, 200);
                            border: none;
                        }
                    """)
                text_html = self.parent_window.render_markdown(block.content) if self.parent_window else block.content
                text_browser.setHtml(text_html)
                self._text_browser = text_browser
                content_layout.addWidget(text_browser)

        if not blocks:
            text_browser = QTextBrowser()
            text_browser.setOpenExternalLinks(True)
            text_browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            text_browser.document().setDocumentMargin(0)
            text_browser.installEventFilter(self)
            if is_dark:
                text_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: transparent;
                        color: rgba(255, 255, 255, 220);
                        border: none;
                    }
                """)
            else:
                text_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: transparent;
                        color: rgba(0, 0, 0, 200);
                        border: none;
                    }
                """)
            self._text_browser = text_browser
            content_layout.addWidget(text_browser)

        self.container_layout.addWidget(content_container)

    def _add_image_grid(self, content_layout, image_parts, is_dark):
        try:
            if len(image_parts) == 1:
                img_path = image_parts[0].get('_file_path')
                logger.info(f"[QuickChat] 尝试加载单张图片：{img_path}, exists={os.path.exists(img_path) if img_path else False}")
                if img_path and os.path.exists(img_path):
                    img_label = QLabel()
                    pixmap = QPixmap(img_path)
                    logger.info(f"[QuickChat] QPixmap 加载结果：isNull={pixmap.isNull()}, size={pixmap.size()}")
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        img_label.setPixmap(scaled_pixmap)
                        img_label.setAlignment(Qt.AlignLeft)
                        img_label.setStyleSheet("background-color: transparent; color: white; border-radius: 5px;")
                        content_layout.addWidget(img_label)
                    else:
                        logger.warning(f"[QuickChat] 图片加载失败：{img_path}")
                        error_label = QLabel(f"[图片加载失败：{os.path.basename(img_path)}]")
                        error_label.setStyleSheet("background-color: transparent; color: white;")
                        content_layout.addWidget(error_label)
                else:
                    logger.warning(f"[QuickChat] 图片路径不存在：{img_path}")
                    error_label = QLabel(f"[图片不存在]")
                    error_label.setStyleSheet("background-color: transparent; color: white;")
                    content_layout.addWidget(error_label)
            else:
                logger.info(f"[QuickChat] 尝试加载 {len(image_parts)} 张图片的网格")
                image_grid = QWidget()
                grid_layout = QGridLayout(image_grid)
                grid_layout.setContentsMargins(0, 0, 0, 0)
                grid_layout.setSpacing(5)

                cols = 2
                valid_count = 0
                for idx, img_part in enumerate(image_parts):
                    img_path = img_part.get('_file_path')
                    logger.info(f"[QuickChat]   图片 {idx+1}: {img_path}, exists={os.path.exists(img_path) if img_path else False}")
                    if img_path and os.path.exists(img_path):
                        pixmap = QPixmap(img_path)
                        if not pixmap.isNull():
                            row = valid_count // cols
                            col = valid_count % cols

                            img_label = QLabel()
                            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            img_label.setPixmap(scaled_pixmap)
                            img_label.setAlignment(Qt.AlignCenter)
                            img_label.setStyleSheet("background-color: transparent; border-radius: 5px;")
                            img_label.setFixedSize(100, 100)

                            grid_layout.addWidget(img_label, row, col)
                            valid_count += 1
                        else:
                            logger.warning(f"[QuickChat] 图片加载失败：{img_path}")
                    else:
                        logger.warning(f"[QuickChat] 图片路径不存在：{img_path}")

                if valid_count > 0:
                    logger.info(f"[QuickChat] 成功加载 {valid_count} 张图片")
                    content_layout.addWidget(image_grid)
                else:
                    logger.error(f"[QuickChat] 没有成功加载任何图片")
                    error_label = QLabel(f"[图片显示失败]")
                    error_label.setStyleSheet("background-color: transparent; color: white;")
                    content_layout.addWidget(error_label)
        except Exception as e:
            import traceback
            logger.error(f"[QuickChat] 显示图片时出错：{e}")
            logger.error(f"[QuickChat] 错误堆栈：{traceback.format_exc()}")
            error_label = QLabel(f"[显示错误：{str(e)[:50]}]")
            error_label.setStyleSheet("background-color: transparent; color: white;")
            content_layout.addWidget(error_label)

    def _setup_action_buttons(self, is_dark):
        self.action_widget = QWidget(self)
        self.action_layout = QHBoxLayout(self.action_widget)
        self.action_layout.setContentsMargins(10, 5, 10, 0)
        self.action_layout.setSpacing(5)

        if is_dark:
            btn_style = """
                ToolButton {
                    background-color: rgba(50, 50, 50, 180);
                    border: none;
                    border-radius: 3px;
                }
                ToolButton:hover {
                    background-color: rgba(70, 70, 70, 220);
                }
            """
        else:
            btn_style = """
                ToolButton {
                    background-color: rgba(200, 200, 200, 180);
                    border: none;
                    border-radius: 3px;
                }
                ToolButton:hover {
                    background-color: rgba(180, 180, 180, 220);
                }
            """

        self.btn_copy = ToolButton(FIF.COPY, self.action_widget)
        self.btn_copy.setFixedSize(28, 28)
        self.btn_copy.setToolTip("复制")
        self.btn_copy.setIconSize(QSize(16, 16))
        self.btn_copy.setStyleSheet(btn_style)
        self.btn_copy.clicked.connect(self.copy_content)
        self.action_layout.addWidget(self.btn_copy)

        self.btn_delete = ToolButton(FIF.DELETE, self.action_widget)
        self.btn_delete.setFixedSize(28, 28)
        self.btn_delete.setToolTip("删除")
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.setStyleSheet(btn_style)
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.msg_id))
        self.action_layout.addWidget(self.btn_delete)

        if self.role == "assistant":
            self.btn_regen = ToolButton(FIF.SYNC, self.action_widget)
            self.btn_regen.setFixedSize(28, 28)
            self.btn_regen.setToolTip("重新生成")
            self.btn_regen.setIconSize(QSize(16, 16))
            self.btn_regen.setStyleSheet(btn_style)
            self.btn_regen.clicked.connect(lambda: self.regenerate_requested.emit(self.msg_id))
            self.action_layout.addWidget(self.btn_regen)

            self.btn_read = ToolButton(FIF.PLAY, self.action_widget)
            self.btn_read.setFixedSize(28, 28)
            self.btn_read.setToolTip("朗读")
            self.btn_read.setIconSize(QSize(16, 16))
            self.btn_read.setStyleSheet(btn_style)
            self.btn_read.clicked.connect(self._on_read_button_clicked)
            self.btn_read.setContextMenuPolicy(Qt.CustomContextMenu)
            self.btn_read.customContextMenuRequested.connect(self._show_read_context_menu)
            self.action_layout.addWidget(self.btn_read)

        self.action_layout.addStretch()

    def _on_read_button_clicked(self):
        if self._playback_state == self.PLAYBACK_STOPPED:
            self.speak_requested.emit(self.msg_id, self.content)
        elif self._playback_state == self.PLAYBACK_PLAYING:
            self.speak_pause_requested.emit(self.msg_id)
        elif self._playback_state == self.PLAYBACK_PAUSED:
            self.speak_resume_requested.emit(self.msg_id)

    def _show_read_context_menu(self, pos):
        menu = QMenu(self)
        restart_action = menu.addAction("从头开始朗读")
        restart_action.triggered.connect(lambda: self.speak_restart_requested.emit(self.msg_id, self.content))
        menu.exec_(self.btn_read.mapToGlobal(pos))

    def update_playback_state(self, state):
        self._playback_state = state
        self._update_read_button()

    def _update_read_button(self):
        if self._playback_state == self.PLAYBACK_STOPPED:
            self.btn_read.setIcon(FIF.PLAY)
            self.btn_read.setToolTip("朗读")
        elif self._playback_state == self.PLAYBACK_PLAYING:
            self.btn_read.setIcon(FIF.PAUSE)
            self.btn_read.setToolTip("暂停")
        elif self._playback_state == self.PLAYBACK_PAUSED:
            self.btn_read.setIcon(FIF.PLAY)
            self.btn_read.setToolTip("继续播放")

    def update_content(self, new_content):
        self.content = new_content
        if 'data:image' in new_content:
            while self.container_layout.count():
                item = self.container_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._text_browser = None
            is_dark = isDarkTheme()
            self._setup_assistant_content(is_dark)
        elif self._text_browser:
            html = self.parent_window.render_markdown(new_content) if self.parent_window else new_content
            self._text_browser.setHtml(html)

    def update_msg_id(self, new_msg_id):
        old_msg_id = self.msg_id
        self.msg_id = new_msg_id
        if self.parent_window and old_msg_id in self.parent_window.message_widgets:
            self.parent_window.message_widgets[new_msg_id] = self.parent_window.message_widgets.pop(old_msg_id)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        from PyQt5.QtGui import QWheelEvent
        if event.type() == QEvent.Wheel:
            wheel_event = event
            if wheel_event.modifiers() == Qt.ControlModifier:
                wheel_event.accept()
                return True
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self.opacity_effect.setOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.opacity_effect.setOpacity(0.0)
        super().leaveEvent(event)

    def copy_content(self):
        if isinstance(self.content, list):
            text_parts = []
            for part in self.content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    text_parts.append(part.get('text', ''))
            clipboard_text = '\n'.join(text_parts)
        else:
            clipboard_text = self.content
        QApplication.clipboard().setText(clipboard_text)
        self.btn_copy.setIcon(FIF.ACCEPT)
        self.btn_copy.setToolTip("已复制")
        QTimer.singleShot(1500, self.reset_copy_icon)

    def reset_copy_icon(self):
        self.btn_copy.setIcon(FIF.COPY)
        self.btn_copy.setToolTip("复制")


class QuickChatWindow(QWidget):
    def __init__(self, db=None, persona_db=None, live2d_widget=None):
        super().__init__()

        deps = get_quick_chat_deps()
        self._chat_db = db or deps.chat_db
        self._persona_db = persona_db or deps.persona_db
        self.live2d_widget = live2d_widget

        self._state = get_quick_chat_state()
        self._service = get_quick_chat_service()

        self._init_managers()

        self._is_generating = False
        self._enter_to_send = False
        self._streaming_buffer = ""
        self._streaming_bubble = None

        self.selected_images = []

        self.message_widgets = {}

        self.persona_prompts = ["You are a helpful assistant."]
        self.persona_doro_tools = [False]

        icon_path = resource_path(os.path.join("data", "icons", "app.ico"))
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._bind_state_signals()
        self.init_ui()
        self.load_settings()

    def _init_managers(self):
        from src.core.memory_manager import MemoryManager, init_memory_database
        init_memory_database(get_quick_chat_deps().db_manager)
        self._memory_manager = MemoryManager(get_quick_chat_deps().db_manager)
        self._service.set_memory_manager(self._memory_manager)

        from src.core.tts import TTSManager
        self._tts_manager = TTSManager(get_quick_chat_deps().db_manager)
        self._service.set_tts_manager(self._tts_manager)
        
        self._tts_manager.playback_started.connect(self._on_playback_started)
        self._tts_manager.playback_stopped.connect(self._on_playback_stopped)
        self._tts_manager.playback_paused.connect(self._on_playback_paused)
        self._tts_manager.playback_resumed.connect(self._on_playback_resumed)

        self._error_handler = ErrorHandler(self._state)
        self._error_handler.error_handled.connect(self._on_error_handled)
        self._error_handler.show_message.connect(self._show_error_message)

    def _on_error_handled(self, error_type, error_message):
        pass

    def _on_playback_started(self, msg_id_str):
        msg_id = int(msg_id_str)
        if msg_id in self.message_widgets:
            self.message_widgets[msg_id].update_playback_state(QuickMessageBubble.PLAYBACK_PLAYING)

    def _on_playback_stopped(self, msg_id_str):
        msg_id = int(msg_id_str)
        if msg_id in self.message_widgets:
            self.message_widgets[msg_id].update_playback_state(QuickMessageBubble.PLAYBACK_STOPPED)

    def _on_playback_paused(self, msg_id_str):
        msg_id = int(msg_id_str)
        if msg_id in self.message_widgets:
            self.message_widgets[msg_id].update_playback_state(QuickMessageBubble.PLAYBACK_PAUSED)

    def _on_playback_resumed(self, msg_id_str):
        msg_id = int(msg_id_str)
        if msg_id in self.message_widgets:
            self.message_widgets[msg_id].update_playback_state(QuickMessageBubble.PLAYBACK_PLAYING)

    def _show_error_message(self, title, message, with_retry):
        if with_retry:
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                title,
                message,
                QMessageBox.Retry | QMessageBox.Cancel,
                QMessageBox.Retry
            )
            if reply == QMessageBox.Retry:
                self._error_handler.retry()
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, title, message, QMessageBox.Ok)

    def _bind_state_signals(self):
        self._state.generation_state_changed.connect(self._on_generation_state_changed)
        self._state.error_occurred.connect(self._on_error_occurred)

    def _bind_llm_signals(self):
        if hasattr(self, 'llm_worker') and self.llm_worker:
            self.llm_worker.chunk_received.connect(self._on_llm_chunk_received)
            self.llm_worker.thinking_chunk.connect(self._on_thinking_chunk)

    def _on_llm_chunk_received(self, chunk):
        self._streaming_buffer += chunk
        self._state.current_streaming_content = self._streaming_buffer
        if self._streaming_bubble:
            self._streaming_bubble.update_content(self._streaming_buffer)
            self._scroll_to_bottom()

    def _on_thinking_chunk(self, chunk):
        pass

    def _scroll_to_bottom(self):
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def _on_generation_state_changed(self, state_value):
        state = GenerationState(state_value)
        self._is_generating = (state == GenerationState.STREAMING or state == GenerationState.PREPARING)
        self.send_btn.setEnabled(not self._is_generating and (bool(self.input_text.toPlainText().strip()) or bool(self.selected_images)))
        self.stop_btn.setEnabled(self._is_generating)

    def _on_error_occurred(self, error_type, error_message):
        self.add_message_to_ui("assistant", f"⚠️ {error_message}")

    def init_ui(self):
        self.setWindowTitle("Doro 沉浸聊天")
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
        self.chat_layout.setStretch(0, 1)

        self.chat_scroll.setWidget(self.chat_content)
        main_layout.addWidget(self.chat_scroll, stretch=10)

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
        self.input_text.setMaximumHeight(120)
        self.input_text.setMinimumHeight(50)
        self.input_text.textChanged.connect(self.update_send_button_state)
        self.input_text.installEventFilter(self)
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

        self._init_quick_phrases()

        self.quick_phrase_combo.currentIndexChanged.connect(self.on_quick_phrase_selected)
        bottom_row.addWidget(self.quick_phrase_combo)

        self.tools_btn = TransparentToolButton(FIF.APPLICATION, self)
        self.tools_btn.setFixedSize(30, 30)
        self.tools_btn.setToolTip("选择工具插件")
        self.tools_btn.clicked.connect(self.show_tools_menu)
        self.update_tools_button_icon()
        bottom_row.addWidget(self.tools_btn)

        self.persona_combo = ComboBox()
        self.persona_combo.setFixedHeight(30)
        self.load_personas()
        self.persona_combo.currentIndexChanged.connect(self.on_persona_changed)
        bottom_row.addWidget(self.persona_combo, 1)

        self.send_btn = ToolButton(FIF.SEND, self)
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)
        bottom_row.addWidget(self.send_btn)

        self.stop_btn = ToolButton(FIF.CANCEL, self)
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_generation)
        bottom_row.addWidget(self.stop_btn)

        control_layout.addLayout(bottom_row)

        main_layout.addWidget(control_panel)

        self.load_chat_history()

    def _init_quick_phrases(self):
        self.quick_phrase_combo.addItem("选择快捷用语...")
        self.quick_phrase_combo.setCurrentIndex(0)

        phrases = self._service.get_all_phrases()
        for phrase in phrases:
            self.quick_phrase_combo.addItem(phrase)

        self.quick_phrase_combo.addItem("────────────")
        self.quick_phrase_combo.addItem("⚙ 管理快捷短语")

    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(10, 0, 5, 0)

        is_dark = isDarkTheme()

        self.title_label = QLabel("💬 Doro 沉浸聊天")
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

        self.clear_history_btn = TransparentToolButton(FIF.DELETE, self)
        self.clear_history_btn.setFixedSize(25, 25)
        self.clear_history_btn.setToolTip("清空聊天记录")
        if is_dark:
            self.clear_history_btn.setStyleSheet("""
                TransparentToolButton {
                    border: none;
                    border-radius: 3px;
                    background-color: rgba(255, 255, 255, 30);
                }
                TransparentToolButton:hover {
                    background-color: rgba(255, 100, 100, 100);
                }
            """)
        else:
            self.clear_history_btn.setStyleSheet("""
                TransparentToolButton {
                    border: none;
                    border-radius: 3px;
                    background-color: rgba(0, 0, 0, 30);
                }
                TransparentToolButton:hover {
                    background-color: rgba(255, 100, 100, 100);
                }
            """)
        self.clear_history_btn.clicked.connect(self.clear_chat_history)
        layout.addWidget(self.clear_history_btn)

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
        if event.button() == Qt.LeftButton:
            if event.y() < 40:
                self._mouse_pressed = True
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._mouse_pressed:
            self.move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._mouse_pressed = False

    def take_screenshot(self):
        if self.window():
            self.window().hide()

        QTimer.singleShot(300, self.start_capture_tool)

    def start_capture_tool(self):
        try:
            from src.ui.widgets.screenshot_tool import ScreenCaptureTool
            self.capture_tool = ScreenCaptureTool()
            self.capture_tool.screenshot_captured.connect(self.on_screenshot_captured)
            self.capture_tool.canceled.connect(self.on_screenshot_canceled)
            self.capture_tool.show()
        except ImportError:
            logger.error("[QuickChat] 无法导入 ScreenCaptureTool")
            self.restore_window()

    def on_screenshot_captured(self, file_path):
        self.selected_images.append(file_path)
        self.update_image_preview()
        self.restore_window()

    def on_screenshot_canceled(self):
        self.restore_window()

    def restore_window(self):
        if self.window():
            self.window().show()
            self.window().activateWindow()

    def update_image_preview(self):
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
        if img_path in self.selected_images:
            self.selected_images.remove(img_path)
            self.update_image_preview()

    def load_chat_history(self):
        logger.info(f"[QuickChat] load_chat_history: START")
        logger.info(f"[QuickChat] load_chat_history: _streaming_bubble = {self._streaming_bubble}")
        logger.info(f"[QuickChat] load_chat_history: chat_layout count before = {self.chat_layout.count()}")

        items_to_remove = []
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item.widget():
                items_to_remove.append(item.widget())

        for widget in items_to_remove:
            logger.info(f"[QuickChat] load_chat_history: removing {widget}")
            self.chat_layout.removeWidget(widget)
            widget.deleteLater()
            widget.setParent(None)

        self.message_widgets.clear()
        logger.info(f"[QuickChat] load_chat_history: message_widgets cleared")
        logger.info(f"[QuickChat] load_chat_history: chat_layout count after = {self.chat_layout.count()}")

        session_id = self._service.get_or_create_session()

        if not session_id:
            logger.warning(f"[QuickChat] session_id 为空，无法加载历史")
            return

        db_msgs = self._service.get_messages()

        logger.info(f"[QuickChat] 从数据库加载消息：session_id={session_id}, 消息数={len(db_msgs)}")
        for i, msg in enumerate(db_msgs[:5]):
            logger.info(f"[QuickChat]   消息 {i+1}: id={msg[0]}, role={msg[1]}, content_len={len(msg[2]) if msg[2] else 0}, images={msg[3] if len(msg) > 3 else None}")

        if len(db_msgs) > 5:
            logger.info(f"[QuickChat]   ... 还有 {len(db_msgs) - 5} 条消息")

        loaded_count = 0
        for msg in db_msgs:
            msg_id = msg[0]
            role = msg[1]
            content = msg[2] if msg[2] else ""
            images = msg[3] if len(msg) > 3 and msg[3] else None

            logger.info(f"[QuickChat] 加载消息 msg_id={msg_id}, images={images}")

            if content or images:
                message_content = self._service.build_history_message(content, images)
                
                logger.info(f"[QuickChat] build_history_message 返回类型：{type(message_content)}, 长度={len(str(message_content)[:200])}")

                bubble = QuickMessageBubble(role, message_content, msg_id, self)
                bubble.delete_requested.connect(self.delete_message)
                bubble.regenerate_requested.connect(self.regenerate_message)
                bubble.speak_requested.connect(self.speak_message)
                bubble.speak_pause_requested.connect(self.speak_pause_message)
                bubble.speak_resume_requested.connect(self.speak_resume_message)
                bubble.speak_restart_requested.connect(self.speak_restart_message)
                self.message_widgets[msg_id] = bubble

                insert_index = self.chat_layout.count() - 1
                self.chat_layout.insertWidget(insert_index, bubble)
                loaded_count += 1

        logger.info(f"[QuickChat] 成功加载 {loaded_count} 条消息到 UI")

    def render_markdown(self, text):
        return self._service.render_markdown(text)

    def add_message_to_ui(self, role, content, msg_id=None, allow_empty=False):
        logger.info(f"[QuickChat] add_message_to_ui: role={role}, msg_id={msg_id}, allow_empty={allow_empty}")
        logger.info(f"[QuickChat] add_message_to_ui: chat_layout count before = {self.chat_layout.count()}")

        if not content and not allow_empty:
            return None

        if msg_id is None:
            msg_id = int(uuid.uuid4().hex[:8], 16)

        bubble = QuickMessageBubble(role, content, msg_id, self)

        bubble.delete_requested.connect(self.delete_message)
        bubble.regenerate_requested.connect(self.regenerate_message)
        bubble.speak_requested.connect(self.speak_message)
        bubble.speak_pause_requested.connect(self.speak_pause_message)
        bubble.speak_resume_requested.connect(self.speak_resume_message)
        bubble.speak_restart_requested.connect(self.speak_restart_message)

        self.message_widgets[msg_id] = bubble

        insert_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_index, bubble)

        logger.info(f"[QuickChat] add_message_to_ui: chat_layout count after = {self.chat_layout.count()}")

        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

        return bubble

    def delete_message(self, msg_id):
        self._service.delete_message(msg_id)

        if msg_id in self.message_widgets:
            bubble = self.message_widgets[msg_id]
            self.chat_layout.removeWidget(bubble)
            bubble.deleteLater()
            del self.message_widgets[msg_id]

        logger.info(f"[QuickChat] 删除消息：msg_id={msg_id}")

    def clear_chat_history(self):
        box = MessageBox(
            "确认清空",
            "确定要清空所有聊天记录吗？\n\n此操作不可恢复！",
            self
        )
        box.yesButton.setText("清空")
        box.cancelButton.setText("取消")

        if not box.exec_():
            return

        logger.info("[QuickChat] 清空聊天记录")

        session_id = self._service.get_or_create_session()
        if session_id:
            self._chat_db.delete_session(session_id)
            logger.info(f"[QuickChat] 已删除会话：session_id={session_id}")

        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.message_widgets.clear()

        if self._memory_manager:
            self._memory_manager.short_term_messages.clear()
            logger.info("[QuickChat] 已清空短期记忆")

        self._service.session_manager.current_session_id = None
        new_session_id = self._service.get_or_create_session()
        logger.info(f"[QuickChat] 已创建新会话：session_id={new_session_id}")

        InfoBar.success(
            title="已清空",
            content="聊天记录已清空",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def regenerate_message(self, msg_id):
        logger.info(f"[QuickChat] regenerate_message called with msg_id={msg_id}")

        w = MessageBox("确认重新生成", "重新生成将会删除此消息及其之后的所有对话记录，确定要继续吗？", self)
        if w.exec_():
            logger.info(f"[QuickChat] user confirmed regenerate")

            ids_to_delete = self._service.delete_messages_from(msg_id)
            logger.info(f"[QuickChat] ids_to_delete from service: {ids_to_delete}")

            old_streaming = self._streaming_bubble
            logger.info(f"[QuickChat] old _streaming_bubble: {old_streaming}")

            if old_streaming is not None:
                logger.info(f"[QuickChat] removing old streaming bubble from layout")
                self.chat_layout.removeWidget(old_streaming)
                old_streaming.deleteLater()
                old_streaming.setParent(None)

            self._streaming_bubble = None
            self._streaming_buffer = ""

            for mid in ids_to_delete:
                if mid in self.message_widgets:
                    bubble = self.message_widgets[mid]
                    self.chat_layout.removeWidget(bubble)
                    bubble.deleteLater()
                    bubble.setParent(None)
                    del self.message_widgets[mid]

            QApplication.processEvents()

            self._service.reload_memory_from_db()

            logger.info(f"[QuickChat] calling load_chat_history")
            self.load_chat_history()

            logger.info(f"[QuickChat] calling trigger_llm_generation")
            self.trigger_llm_generation()
        else:
            logger.info(f"[QuickChat] user cancelled regenerate")

    def speak_message(self, msg_id, content):
        self._service.speak(msg_id, content)

    def speak_pause_message(self, msg_id):
        self._service.pause_speak(msg_id)

    def speak_resume_message(self, msg_id):
        self._service.resume_speak(msg_id)

    def speak_restart_message(self, msg_id, content):
        self._service.speak(msg_id, content, force_restart=True)

    def trigger_llm_generation(self):
        session_id = self._service.get_or_create_session()

        history = self._service.get_context_for_llm(session_id)

        history = self._preprocess_history_images(history)

        deps = get_quick_chat_deps()
        active_model = deps.get_active_model()

        if not active_model or len(active_model) < 6:
            return

        api_key = active_model[3] if len(active_model) > 3 else ""
        base_url = active_model[4] if len(active_model) > 4 else "https://api.openai.com/v1"
        model_name = active_model[5] if len(active_model) > 5 else ""

        if not api_key or not model_name or not base_url:
            return

        self._state.generation_state = GenerationState.PREPARING

        self._streaming_buffer = ""
        self._streaming_bubble = None

        self.llm_worker = LLMWorker(
            api_key=api_key,
            base_url=base_url,
            messages=history,
            model=model_name,
            db=self._chat_db,
            is_thinking=0,
            enabled_plugins=self._service.get_enabled_tools()
        )
        self._streaming_bubble = self.add_message_to_ui("assistant", "", None, allow_empty=True)
        self._streaming_buffer = ""
        self.llm_worker.chunk_received.connect(self._on_llm_chunk_received)
        self.llm_worker.thinking_chunk.connect(self._on_thinking_chunk)
        self.llm_worker.finished.connect(self.on_response_received)
        self.llm_worker.error.connect(self.on_error_occurred)
        self.llm_worker.start()

    def _preprocess_history_images(self, history):
        import re
        result = []
        for i, msg in enumerate(history):
            if isinstance(msg, dict) and msg.get('content'):
                content = msg['content']
                if isinstance(content, str):
                    if 'data:image' in content and i < len(history) - 1:
                        content = re.sub(r'!\[.*?\]\(data:image/[^;]+;base64,.*?\)', '[图片]', content)
                        msg = dict(msg)
                        msg['content'] = content
                elif isinstance(content, list):
                    if i < len(history) - 1:
                        new_content = []
                        for part in content:
                            if isinstance(part, dict):
                                if part.get('type') == 'image_url' and isinstance(part.get('image_url'), dict):
                                    url = part['image_url'].get('url', '')
                                    if url and url.startswith('data:image'):
                                        continue
                                new_content.append(part)
                            else:
                                new_content.append(part)
                        msg = dict(msg)
                        msg['content'] = new_content
            result.append(msg)
        return result

    def update_send_button_state(self):
        has_content = bool(self.input_text.toPlainText().strip()) or bool(self.selected_images)
        self.send_btn.setEnabled(has_content and not self._is_generating)

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        from PyQt5.QtGui import QKeyEvent

        if obj == self.input_text and event.type() == QEvent.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key_Return or key_event.key() == Qt.Key_Enter:
                if key_event.modifiers() == Qt.ControlModifier:
                    if self.send_btn.isEnabled():
                        self.send_message()
                    return True
                elif not self._enter_to_send:
                    return True
                elif self._enter_to_send and self.send_btn.isEnabled():
                    self.send_message()
                    return True

        return super().eventFilter(obj, event)

    def load_personas(self):
        current_text = self.persona_combo.currentText()
        self.persona_combo.clear()

        names, prompts, doro_tools = self._service.load_personas()
        self.persona_prompts = prompts
        self.persona_doro_tools = doro_tools

        for name in names:
            self.persona_combo.addItem(name)

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

    def update_tools_button_icon(self):
        enabled_tools = self._service.tool_manager.get_enabled_tools()
        enabled_count = len(enabled_tools)

        if enabled_count > 0:
            self.tools_btn.setStyleSheet("""
                TransparentToolButton {
                    border: 1px solid rgba(0, 120, 215, 200);
                    border-radius: 5px;
                    background-color: rgba(0, 120, 215, 50);
                }
                TransparentToolButton:hover {
                    background-color: rgba(0, 120, 215, 80);
                }
            """)

            enabled_names = self._service.tool_manager.get_enabled_tool_names()
            skill_count = sum(1 for t in enabled_tools if t.startswith("skill:"))

            tooltip = f"已启用工具：{', '.join(enabled_names)}"
            if skill_count > 0:
                tooltip += f"\n已启用技能：{skill_count} 个"
            tooltip += "\n\n点击切换工具"
            self.tools_btn.setToolTip(tooltip)
        else:
            self.tools_btn.setStyleSheet("")
            self.tools_btn.setToolTip("选择工具插件\n\n当前未启用任何工具")

    def show_tools_menu(self):
        menu = QMenu(self)

        local_tools_label = QAction("── 本地工具 ──", self)
        local_tools_label.setEnabled(False)
        menu.addAction(local_tools_label)

        tool_manager = self._service.tool_manager

        action_search = QAction("🔍 联网搜索", self, checkable=True)
        action_search.setChecked(tool_manager.is_tool_enabled("search"))
        action_search.triggered.connect(lambda checked: self.toggle_tool("search", checked))
        menu.addAction(action_search)

        action_image = QAction("🎨 图片生成", self, checkable=True)
        action_image.setChecked(tool_manager.is_tool_enabled("image"))
        action_image.triggered.connect(lambda checked: self.toggle_tool("image", checked))
        menu.addAction(action_image)

        action_coding = QAction("💻 代码执行", self, checkable=True)
        action_coding.setChecked(tool_manager.is_tool_enabled("coding"))
        action_coding.triggered.connect(lambda checked: self.toggle_tool("coding", checked))
        menu.addAction(action_coding)

        action_file = QAction("📁 文件操作", self, checkable=True)
        action_file.setChecked(tool_manager.is_tool_enabled("file"))
        action_file.triggered.connect(lambda checked: self.toggle_tool("file", checked))
        menu.addAction(action_file)

        try:
            from src.core.skill_manager import SkillManager
            skill_mgr = SkillManager()

            if skill_mgr and hasattr(skill_mgr, 'skills') and skill_mgr.skills:
                skill_label = QAction("── 技能插件 ──", self)
                skill_label.setEnabled(False)
                menu.addAction(skill_label)

                for skill_name, skill_info in skill_mgr.skills.items():
                    try:
                        skill_display = skill_info.get("name", skill_name) if isinstance(skill_info, dict) else skill_name
                        action = QAction(f"🔌 {skill_display}", self, checkable=True)
                        is_enabled = tool_manager.is_tool_enabled(f"skill:{skill_name}")
                        action.setChecked(is_enabled)
                        action.triggered.connect(lambda checked, name=skill_name: self.toggle_tool(f"skill:{name}", checked))
                        menu.addAction(action)
                    except Exception as e:
                        logger.error(f"[QuickChat] 加载技能 {skill_name} 时出错：{e}")
        except Exception as e:
            logger.error(f"[QuickChat] 加载技能管理器时出错：{e}")

        menu.exec_(self.tools_btn.mapToGlobal(self.tools_btn.rect().bottomLeft()))

    def toggle_tool(self, tool_name, enabled):
        self._service.toggle_tool(tool_name, enabled)
        self.update_tools_button_icon()

        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue(f"tool_{tool_name}_enabled", enabled)

        status = "启用" if enabled else "禁用"
        logger.info(f"[QuickChat] {status}工具：{tool_name}")

    def on_persona_changed(self, index):
        self._service.set_persona(
            self.persona_combo.currentText(),
            self.persona_prompts[index]
        )

        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue("last_persona", self.persona_combo.currentText())

    def insert_phrase(self, phrase):
        current = self.input_text.toPlainText()
        if current:
            self.input_text.setPlainText(current + " " + phrase)
        else:
            self.input_text.setPlainText(phrase)

    def on_quick_phrase_selected(self, index):
        current_text = self.quick_phrase_combo.itemText(index)

        if not current_text or current_text == "选择快捷用语..." or current_text.startswith("──"):
            self.quick_phrase_combo.setCurrentIndex(0)
            return

        if current_text == "⚙ 管理快捷短语":
            self.show_quick_phrase_manager()
            self.quick_phrase_combo.setCurrentIndex(0)
            return

        self.insert_phrase(current_text)
        self.quick_phrase_combo.setCurrentIndex(0)

    def show_quick_phrase_manager(self):
        from PyQt5.QtWidgets import QDialog
        from PyQt5.QtCore import Qt

        settings = QSettings("DoroPet", "QuickChat")
        saved_phrases = settings.value("custom_quick_phrases", [])
        if not isinstance(saved_phrases, list):
            saved_phrases = saved_phrases.split('||') if saved_phrases else []

        dialog = QDialog(self)
        dialog.setWindowTitle("管理快捷短语")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        info_label = QLabel("⚙ 管理快捷短语\n\n每行一个快捷短语，点击确定保存：\n删除某行即可删除该短语")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)

        phrase_edit = QTextEdit()
        phrase_edit.setPlaceholderText("输入快捷短语，每行一个\n删除某行即可删除该短语")
        phrase_edit.setPlainText('\n'.join(saved_phrases))
        phrase_edit.setMinimumHeight(150)
        phrase_edit.setMaximumHeight(200)
        layout.addWidget(phrase_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(80)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

        def on_ok():
            new_phrases = [p.strip() for p in phrase_edit.toPlainText().split('\n') if p.strip()]
            self._service.save_phrases(settings, new_phrases)
            self.reload_quick_phrases(new_phrases)
            dialog.accept()

        def on_cancel():
            dialog.reject()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(on_cancel)

        dialog.exec_()

    def reload_quick_phrases(self, custom_phrases):
        self.quick_phrase_combo.currentIndexChanged.disconnect()

        current_text = self.quick_phrase_combo.currentText()
        self.quick_phrase_combo.clear()

        self.quick_phrase_combo.addItem("选择快捷用语...")

        all_phrases = self._service.phrase_manager.get_all_phrases()
        for phrase in all_phrases:
            self.quick_phrase_combo.addItem(phrase)

        self.quick_phrase_combo.addItem("────────────")
        self.quick_phrase_combo.addItem("⚙ 管理快捷短语")

        if current_text and current_text != "选择快捷用语..." and not current_text.startswith("──"):
            index = self.quick_phrase_combo.findText(current_text)
            if index >= 0:
                self.quick_phrase_combo.setCurrentIndex(index)

        self.quick_phrase_combo.currentIndexChanged.connect(self.on_quick_phrase_selected)

    def _toggle_auto_play(self):
        self._auto_play_enabled = not self._auto_play_enabled
        self._update_auto_play_btn_style()

    def _update_auto_play_btn_style(self):
        if self._auto_play_enabled:
            self.auto_play_btn.setIcon(FIF.VOLUME)
            self.auto_play_btn.setToolTip("自动播放语音：开")
        else:
            self.auto_play_btn.setIcon(FIF.MUTE)
            self.auto_play_btn.setToolTip("自动播放语音：关")

    def send_message(self):
        if self._is_generating:
            self.stop_generation()
            return

        user_input = self.input_text.toPlainText().strip()
        images_json = self.selected_images.copy() if self.selected_images else None

        if not user_input and not images_json:
            return

        session_id = self._service.get_or_create_session()

        logger.info(f"[QuickChat] 当前 session_id={session_id}")

        msg_id = self._service.add_message(
            "user",
            user_input,
            images=images_json
        )

        logger.info(f"[QuickChat] 用户消息已保存：msg_id={msg_id}, session_id={session_id}")

        api_content, display_content = self._service.build_user_message(user_input, images_json)

        self.add_message_to_ui("user", display_content, msg_id)

        self.input_text.clear()
        self.selected_images.clear()
        self.update_image_preview()

        self._state.generation_state = GenerationState.PREPARING

        self._service.add_to_memory("user", api_content, session_id)

        history = self._service.get_context_for_llm(session_id)
        
        history = self._preprocess_history_images(history)

        logger.info(f"[QuickChat] 使用智能记忆系统，上下文消息数：{len(history)}")

        deps = get_quick_chat_deps()
        active_model = deps.get_active_model()

        logger.info(f"[QuickChat] 获取活动模型：{active_model}")

        if not active_model or len(active_model) < 6:
            error_msg = "错误：请先在【模型配置】页面添加并选择一个有效的模型！"
            logger.error(f"[QuickChat] 活动模型配置无效：active_model={active_model}")
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._state.generation_state = GenerationState.IDLE
            return

        api_key = active_model[3] if len(active_model) > 3 else ""
        base_url = active_model[4] if len(active_model) > 4 else "https://api.openai.com/v1"
        model_name = active_model[5] if len(active_model) > 5 else ""

        is_ollama = "ollama" in base_url.lower() or "localhost:11434" in base_url

        logger.info(f"[QuickChat] 使用模型：{model_name}, base_url: {base_url[:30] if base_url else 'None'}..., api_key: {api_key[:10] if api_key else 'None'}..., is_ollama={is_ollama}")

        if not model_name or not base_url:
            error_msg = "错误：当前模型配置不完整（缺少 Base URL 或模型名称），请在【模型配置】页面重新配置！"
            logger.error(f"[QuickChat] 模型配置不完整：base_url={bool(base_url)}, model_name={bool(model_name)}")
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._state.generation_state = GenerationState.IDLE
            return

        if not api_key and not is_ollama:
            error_msg = "错误：当前模型配置不完整（缺少 API Key），请在【模型配置】页面重新配置！"
            logger.error(f"[QuickChat] 模型配置不完整：api_key={bool(api_key)}")
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._state.generation_state = GenerationState.IDLE
            return

        self.llm_worker = LLMWorker(
            api_key=api_key,
            base_url=base_url,
            messages=history,
            model=model_name,
            db=self._chat_db,
            is_thinking=0,
            enabled_plugins=self._service.get_enabled_tools()
        )
        self.llm_worker.finished.connect(self.on_response_received)
        self.llm_worker.error.connect(self.on_error_occurred)
        self.llm_worker.start()

    def _clear_streaming_bubble(self):
        if self._streaming_bubble is not None:
            logger.info(f"[QuickChat] _clear_streaming_bubble: removing old streaming bubble")
            self.chat_layout.removeWidget(self._streaming_bubble)
            self._streaming_bubble.deleteLater()
            self._streaming_bubble.setParent(None)
            self._streaming_bubble = None
        self._streaming_buffer = ""

    def on_response_received(self, content, reasoning, tool_calls, generated_images):
        logger.info(f"[QuickChat] on_response_received: _streaming_bubble = {self._streaming_bubble}")
        logger.info(f"[QuickChat] on_response_received: _streaming_buffer length = {len(self._streaming_buffer)}")
        logger.info(f"[QuickChat] on_response_received: generated_images = {generated_images}")

        if not content:
            content = reasoning if reasoning else ""

        if not content:
            if self._streaming_bubble is not None:
                self.chat_layout.removeWidget(self._streaming_bubble)
                self._streaming_bubble.deleteLater()
                self._streaming_bubble.setParent(None)
                self._streaming_bubble = None
            self._streaming_buffer = ""
            error_msg = "错误：AI 未生成任何内容"
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._state.generation_state = GenerationState.IDLE
            return

        display_content = content
        logger.info(f"[QuickChat] on_response_received: display_content 长度={len(display_content)}, 包含base64={'data:image' in display_content if display_content else False}")
        if not generated_images and 'data:image' in content:
            import re
            display_content = content
            logger.info(f"[QuickChat] on_response_received: content包含base64图片")
        elif generated_images:
            for img_path in generated_images:
                try:
                    with open(img_path, 'rb') as f:
                        image_data = f.read()
                    b64_data = base64.b64encode(image_data).decode('utf-8')
                    ext = os.path.splitext(img_path)[1].lower().replace('.', '')
                    if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                        ext = 'png'
                    data_uri = f"data:image/{ext};base64,{b64_data}"
                    logger.info(f"[QuickChat] 添加 base64 图片到显示内容")
                    display_content += f"\n\n![Generated Image]({data_uri})"
                except Exception as e:
                    logger.error(f"[QuickChat] 转换图片到 base64 失败：{e}")

        session_id = self._service.get_or_create_session()

        msg_id = self._service.add_message(
            "assistant",
            display_content,
            images=None
        )

        self._service.add_to_memory("assistant", content, session_id)

        if self._streaming_bubble is not None:
            logger.info(f"[QuickChat] on_response_received: updating existing streaming bubble with final content")
            self._streaming_bubble.update_content(display_content)
            self._streaming_bubble.update_msg_id(msg_id)
            self._streaming_bubble = None
            self._streaming_buffer = ""
        else:
            logger.info(f"[QuickChat] on_response_received: creating new bubble")
            self.add_message_to_ui("assistant", display_content, msg_id)

        if self._auto_play_enabled:
            self._service.speak(msg_id, content)

        self._state.generation_state = GenerationState.COMPLETED

    def on_error_occurred(self, error):
        logger.error(f"[QuickChat] LLM 错误：{error}")

        if self._streaming_bubble is not None:
            self.chat_layout.removeWidget(self._streaming_bubble)
            self._streaming_bubble.deleteLater()
            self._streaming_bubble.setParent(None)

        self._streaming_bubble = None
        self._streaming_buffer = ""

        self.add_message_to_ui("assistant", f"⚠️ 生成失败：{str(error)}")

        self._state.generation_state = GenerationState.ERROR

        chat_error = create_error_from_exception(error, {"source": "llm_worker"})
        self._error_handler.handle_error(chat_error, retry_callback=self._retry_send_message)

    def _retry_send_message(self):
        self.send_message()

    def stop_generation(self):
        if hasattr(self, 'llm_worker') and self.llm_worker.isRunning():
            self.llm_worker.stop()

        if self._streaming_bubble is not None:
            self.chat_layout.removeWidget(self._streaming_bubble)
            self._streaming_bubble.deleteLater()
            self._streaming_bubble.setParent(None)

        self._streaming_bubble = None
        self._streaming_buffer = ""

        self._state.generation_state = GenerationState.STOPPED

    def load_settings(self):
        settings = QSettings("DoroPet", "QuickChat")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(550, 800)

        auto_play = settings.value("auto_play_voice", False, type=bool)
        self._auto_play_enabled = auto_play
        self._update_auto_play_btn_style()

        self._service.load_settings(settings)

        self._enter_to_send = settings.value("enter_to_send", False, type=bool)

        self.update_tools_button_icon()

        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._periodic_cleanup)
        self._cleanup_timer.start(5 * 60 * 1000)

    def _periodic_cleanup(self):
        from src.core.image_cache_manager import get_image_cache_manager
        cache_mgr = get_image_cache_manager()
        stats = cache_mgr.get_cache_stats()
        logger.debug(f"[QuickChat] 图片缓存统计: {stats['file_count']} 个文件, {stats['total_size_mb']:.1f}MB")

    def update_theme(self):
        is_dark = isDarkTheme()

        self._service.set_theme(is_dark)

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
        if hasattr(self, '_cleanup_timer'):
            self._cleanup_timer.stop()
        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("auto_play_voice", self._auto_play_enabled)
        settings.setValue("enter_to_send", self._enter_to_send)
        self.hide()
        event.ignore()


