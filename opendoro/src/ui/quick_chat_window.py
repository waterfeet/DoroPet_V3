import sys
import re
import uuid
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTextEdit, 
                             QPushButton, QLabel, QComboBox, QFrame, QApplication,
                             QScrollArea, QButtonGroup, QSizePolicy, QTextBrowser,
                             QGraphicsOpacityEffect, QMenu, QAction)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer, QSize
from PyQt5.QtGui import QFont, QPixmap, QIcon
from qfluentwidgets import (PushButton, PrimaryPushButton, TransparentToolButton, ToolButton, FluentIcon as FIF,
                            CardWidget, StrongBodyLabel, BodyLabel, setTheme, Theme,
                            isDarkTheme, TransparentTogglePushButton, MessageBox,
                            LineEdit, ComboBox, TextEdit, InfoBar, InfoBarPosition)

from src.core.database import ChatDatabase
from src.services.llm_service import LLMWorker
from src.core.memory_manager import MemoryManager, init_memory_database
from src.core.quick_chat_service import QuickChatService, ImageProcessor
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
            
            self.content_widget = QWidget(self.container)
            self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(8)
            self.content_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
            
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
                    self.content_layout.addWidget(text_label)
                
                if image_parts:
                    try:
                        if len(image_parts) == 1:
                            img_path = image_parts[0].get('_file_path')
                            from src.core.logger import logger
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
                                    self.content_layout.addWidget(img_label)
                                else:
                                    logger.warning(f"[QuickChat] 图片加载失败：{img_path}")
                                    error_label = QLabel(f"[图片加载失败：{os.path.basename(img_path)}]")
                                    error_label.setStyleSheet("background-color: transparent; color: white;")
                                    self.content_layout.addWidget(error_label)
                            else:
                                logger.warning(f"[QuickChat] 图片路径不存在：{img_path}")
                                error_label = QLabel(f"[图片不存在]")
                                error_label.setStyleSheet("background-color: transparent; color: white;")
                                self.content_layout.addWidget(error_label)
                        else:
                            from src.core.logger import logger
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
                                self.content_layout.addWidget(image_grid)
                            else:
                                logger.error(f"[QuickChat] 没有成功加载任何图片")
                                error_label = QLabel(f"[图片显示失败]")
                                error_label.setStyleSheet("background-color: transparent; color: white;")
                                self.content_layout.addWidget(error_label)
                    except Exception as e:
                        from src.core.logger import logger
                        import traceback
                        logger.error(f"[QuickChat] 显示图片时出错：{e}")
                        logger.error(f"[QuickChat] 错误堆栈：{traceback.format_exc()}")
                        error_label = QLabel(f"[显示错误：{str(e)[:50]}]")
                        error_label.setStyleSheet("background-color: transparent; color: white;")
                        self.content_layout.addWidget(error_label)
            else:
                self.content_label = QLabel(self.content)
                self.content_label.setWordWrap(True)
                self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                self.content_label.setStyleSheet("background-color: transparent; color: white;")
                self.content_layout.addWidget(self.content_label)
            
            self.container_layout.addWidget(self.content_widget)
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
            self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.content_browser.document().setDocumentMargin(0)
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
            self.content_browser.setMinimumWidth(300)
            self.content_browser.setMaximumWidth(600)
            self.content_browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            self.content_browser.document().adjustSize()
            doc_size = self.content_browser.document().size()
            needed_height = int(doc_size.height()) + 10
            
            self.content_browser.setMinimumHeight(max(50, needed_height))
            self.content_browser.setMaximumHeight(needed_height)
            
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
        """重置复制按钮图标"""
        self.btn_copy.setIcon(FIF.COPY)
        self.btn_copy.setToolTip("复制")


class QuickChatWindow(QWidget):
    """独立快捷聊天窗口"""
    
    def __init__(self, db=None, persona_db=None, live2d_widget=None):
        super().__init__()
        
        from src.core.database import DatabaseManager
        db_manager = DatabaseManager()
        
        self.chat_db = db or db_manager.chat
        self.persona_db = persona_db or db_manager.personas
        self.live2d_widget = live2d_widget
        
        init_memory_database(db_manager)
        self.memory_manager = MemoryManager(db_manager)
        
        from src.core.tts import TTSManager
        self.tts_manager = TTSManager(db_manager)
        
        self.chat_service = QuickChatService(
            chat_db=self.chat_db,
            persona_db=self.persona_db,
            memory_manager=self.memory_manager,
            tts_manager=self.tts_manager
        )
        
        self._is_generating = False
        self._enter_to_send = False
        
        self.selected_images = []
        
        self.message_widgets = {}
        
        self.persona_prompts = ["You are a helpful assistant."]
        self.persona_doro_tools = [False]
        
        icon_path = resource_path("data\\icons\\app.ico")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
        self.load_settings()
        self.load_tool_settings()
        
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
        """初始化快捷短语下拉框"""
        self.quick_phrase_combo.addItem("选择快捷用语...")
        self.quick_phrase_combo.setCurrentIndex(0)
        
        phrases = self.chat_service.get_all_phrases()
        for phrase in phrases:
            self.quick_phrase_combo.addItem(phrase)
        
        self.quick_phrase_combo.addItem("────────────")
        self.quick_phrase_combo.addItem("⚙ 管理快捷短语")
    
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
        
        logger.info(f"[QuickChat] 开始加载聊天历史")
        
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.message_widgets.clear()
        
        session_id = self.chat_service.get_or_create_session()
        logger.info(f"[QuickChat] 获取 session_id: {session_id}")
        
        if not session_id:
            logger.warning(f"[QuickChat] session_id 为空，无法加载历史")
            return
        
        db_msgs = self.chat_service.get_messages()
        
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
            
            if content or images:
                message_content = self.chat_service.build_history_message(content, images)
                
                bubble = QuickMessageBubble(role, message_content, msg_id, self)
                bubble.delete_requested.connect(self.delete_message)
                bubble.regenerate_requested.connect(self.regenerate_message)
                bubble.speak_requested.connect(self.speak_message)
                self.message_widgets[msg_id] = bubble
                
                insert_index = self.chat_layout.count() - 1
                self.chat_layout.insertWidget(insert_index, bubble)
                loaded_count += 1
        
        logger.info(f"[QuickChat] 成功加载 {loaded_count} 条消息到 UI")
    
    def render_markdown(self, text):
        """渲染 Markdown 为 HTML"""
        return self.chat_service.render_markdown(text)
    
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
        
        self.chat_service.delete_message(msg_id)
        
        if msg_id in self.message_widgets:
            bubble = self.message_widgets[msg_id]
            self.chat_layout.removeWidget(bubble)
            bubble.deleteLater()
            del self.message_widgets[msg_id]
        
        logger.info(f"[QuickChat] 删除消息：msg_id={msg_id}")
    
    def clear_chat_history(self):
        """清空所有聊天记录"""
        from src.core.logger import logger
        from qfluentwidgets import MessageBox
        
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
        
        session_id = self.chat_service.get_or_create_session()
        if session_id:
            self.chat_service.chat_db.delete_session(session_id)
            logger.info(f"[QuickChat] 已删除会话：session_id={session_id}")
        
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.message_widgets.clear()
        
        if self.chat_service.memory_manager:
            self.chat_service.memory_manager.short_term_messages.clear()
            logger.info("[QuickChat] 已清空短期记忆")
        
        self.chat_service.session_manager.current_session_id = None
        new_session_id = self.chat_service.get_or_create_session()
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
        """重新生成消息"""
        from src.core.logger import logger
        
        ids_to_delete = self.chat_service.delete_messages_from(msg_id)
        
        if not ids_to_delete:
            return
        
        w = MessageBox("确认重新生成", "重新生成将会删除此消息及其之后的所有对话记录，确定要继续吗？", self)
        if w.exec_():
            for mid in ids_to_delete:
                if mid in self.message_widgets:
                    bubble = self.message_widgets[mid]
                    self.chat_layout.removeWidget(bubble)
                    bubble.deleteLater()
                    del self.message_widgets[mid]
            
            self.chat_service.clear_memory()
            
            self.load_chat_history()
            
            self.trigger_llm_generation()
    
    def speak_message(self, msg_id, content):
        """朗读消息"""
        self.chat_service.speak(msg_id, content)
    
    def trigger_llm_generation(self):
        """触发 LLM 生成"""
        session_id = self.chat_service.get_or_create_session()
        
        history = self.chat_service.get_context_for_llm(session_id)
        
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
            enabled_plugins=self.chat_service.get_enabled_tools()
        )
        self.llm_worker.finished.connect(self.on_response_received)
        self.llm_worker.error.connect(self.on_error_occurred)
        self.llm_worker.start()
    
    def update_send_button_state(self):
        """根据输入内容更新发送按钮状态"""
        has_content = bool(self.input_text.toPlainText().strip()) or bool(self.selected_images)
        self.send_btn.setEnabled(has_content)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 处理回车发送"""
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
        """加载人格列表"""
        current_text = self.persona_combo.currentText()
        self.persona_combo.clear()
        
        names, prompts, doro_tools = self.chat_service.load_personas()
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
        """更新工具按钮图标样式"""
        enabled_tools = self.chat_service.tool_manager.get_enabled_tools()
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
            
            enabled_names = self.chat_service.tool_manager.get_enabled_tool_names()
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
        """显示工具选择菜单"""
        menu = QMenu(self)
        
        local_tools_label = QAction("── 本地工具 ──", self)
        local_tools_label.setEnabled(False)
        menu.addAction(local_tools_label)
        
        tool_manager = self.chat_service.tool_manager
        
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
                        from src.core.logger import logger
                        logger.error(f"[QuickChat] 加载技能 {skill_name} 时出错：{e}")
        except Exception as e:
            from src.core.logger import logger
            logger.error(f"[QuickChat] 加载技能管理器时出错：{e}")
        
        menu.exec_(self.tools_btn.mapToGlobal(self.tools_btn.rect().bottomLeft()))
    
    def toggle_tool(self, tool_name, enabled):
        """切换工具启用状态"""
        self.chat_service.toggle_tool(tool_name, enabled)
        self.update_tools_button_icon()
        
        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue(f"tool_{tool_name}_enabled", enabled)
        
        from src.core.logger import logger
        status = "启用" if enabled else "禁用"
        logger.info(f"[QuickChat] {status}工具：{tool_name}")
    
    def on_persona_changed(self, index):
        """人格切换"""
        self.chat_service.set_persona(
            self.persona_combo.currentText(),
            self.persona_prompts[index]
        )
        
        settings = QSettings("DoroPet", "QuickChat")
        settings.setValue("last_persona", self.persona_combo.currentText())
    
    def insert_phrase(self, phrase):
        """插入快捷短语"""
        current = self.input_text.toPlainText()
        if current:
            self.input_text.setPlainText(current + " " + phrase)
        else:
            self.input_text.setPlainText(phrase)
    
    def on_quick_phrase_selected(self, index):
        """快捷短语下拉框选择事件"""
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
        """显示快捷短语管理对话框"""
        from qfluentwidgets import MessageBox
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
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
            self.chat_service.save_phrases(settings, new_phrases)
            self.reload_quick_phrases(new_phrases)
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(on_cancel)
        
        dialog.exec_()
    
    def reload_quick_phrases(self, custom_phrases):
        """重新加载快捷短语列表"""
        self.quick_phrase_combo.currentIndexChanged.disconnect()
        
        current_text = self.quick_phrase_combo.currentText()
        self.quick_phrase_combo.clear()
        
        self.quick_phrase_combo.addItem("选择快捷用语...")
        
        all_phrases = self.chat_service.phrase_manager.get_all_phrases()
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
        
        session_id = self.chat_service.get_or_create_session()
        
        logger.info(f"[QuickChat] 当前 session_id={session_id}")
        
        msg_id = self.chat_service.add_message(
            "user", 
            user_input,
            images=images_json
        )
        
        logger.info(f"[QuickChat] 用户消息已保存：msg_id={msg_id}, session_id={session_id}")
        
        api_content, display_content = self.chat_service.build_user_message(user_input, images_json)
        
        self.add_message_to_ui("user", display_content, msg_id)
        
        self.input_text.clear()
        self.selected_images.clear()
        self.update_image_preview()
        
        self._is_generating = True
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        logger.info(f"[QuickChat] 准备发送消息：user_input={user_input[:50] if user_input else 'None'}, images={images_json}")
        
        self.chat_service.add_to_memory("user", api_content, session_id)
        
        history = self.chat_service.get_context_for_llm(session_id)
        
        logger.info(f"[QuickChat] 使用智能记忆系统，上下文消息数：{len(history)}")
        
        logger.info(f"[QuickChat] ====== 发送消息给 AI ======")
        logger.info(f"[QuickChat] 消息总数：{len(history)}")
        for i, msg in enumerate(history):
            content = msg['content']
            if isinstance(content, list):
                content_preview = f"[多模态消息] 文本 + {len([c for c in content if isinstance(c, dict) and c.get('type') == 'image_url'])} 张图片"
            else:
                content_preview = content[:300] if len(content) > 300 else content
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
        
        is_ollama = "ollama" in base_url.lower() or "localhost:11434" in base_url
        
        logger.info(f"[QuickChat] 使用模型：{model_name}, base_url: {base_url[:30] if base_url else 'None'}..., api_key: {api_key[:10] if api_key else 'None'}..., is_ollama={is_ollama}")
        
        if not model_name or not base_url:
            error_msg = "错误：当前模型配置不完整（缺少 Base URL 或模型名称），请在【模型配置】页面重新配置！"
            logger.error(f"[QuickChat] 模型配置不完整：base_url={bool(base_url)}, model_name={bool(model_name)}")
            self.add_message_to_ui("assistant", f"⚠️ {error_msg}")
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        if not api_key and not is_ollama:
            error_msg = "错误：当前模型配置不完整（缺少 API Key），请在【模型配置】页面重新配置！"
            logger.error(f"[QuickChat] 模型配置不完整：api_key={bool(api_key)}")
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
        
        session_id = self.chat_service.get_or_create_session()
        
        msg_id = self.chat_service.add_message(
            "assistant",
            content,
            images=None
        )
        
        self.chat_service.add_to_memory("assistant", content, session_id)
        
        self.add_message_to_ui("assistant", content, msg_id)
        
        if self._auto_play_enabled:
            self.chat_service.speak(msg_id, content)
        
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
        
        self.load_tool_settings()
    
    def load_tool_settings(self):
        """加载工具设置"""
        settings = QSettings("DoroPet", "QuickChat")
        self.chat_service.load_settings(settings)
        
        self._enter_to_send = settings.value("enter_to_send", False, type=bool)
        
        self.update_tools_button_icon()
    
    def update_theme(self):
        """更新主题"""
        is_dark = isDarkTheme()
        
        self.chat_service.set_theme(is_dark)
        
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
        settings.setValue("enter_to_send", self._enter_to_send)
        self.hide()
        event.ignore()


from .quick_chat_window import QuickChatWindow
