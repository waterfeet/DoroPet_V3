import os
import random
from enum import Enum
from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal, QPoint, QEvent, QRect
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QStyle, QFrame, QScrollArea, QSizePolicy, QApplication, QLineEdit, QPushButton, QComboBox
from PyQt5.QtGui import QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QVideoWidget

from qfluentwidgets import CardWidget, PushButton, TransparentToolButton, FluentIcon as FIF

from src.services.music_service import MusicService, SongInfo


class PlayMode(Enum):
    SEQUENCE = "sequence"
    LIST_LOOP = "list_loop"
    SINGLE_LOOP = "single_loop"
    SHUFFLE = "shuffle"


class SongListItem(QFrame):
    clicked = pyqtSignal(int)
    
    def __init__(self, index: int, name: str, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self._is_current = is_current
        self._is_hovered = False
        
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)
        
        self.index_label = QLabel(f"{index + 1}")
        self.index_label.setFixedWidth(20)
        self.index_label.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
        
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-size: 12px;")
        
        self.current_icon = QLabel("▶")
        self.current_icon.setStyleSheet("font-size: 10px; color: #0078d4;")
        self.current_icon.setFixedWidth(12)
        self.current_icon.setVisible(is_current)
        
        layout.addWidget(self.index_label)
        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.current_icon)
        
        self._update_style()
    
    def set_current(self, is_current: bool):
        self._is_current = is_current
        self.current_icon.setVisible(is_current)
        self._update_style()
    
    def _update_style(self):
        if self._is_current:
            bg_color = "rgba(0, 120, 212, 0.1)"
            text_color = "#0078d4"
        else:
            bg_color = "transparent"
            text_color = "#333"
        
        self.setStyleSheet(f"""
            SongListItem {{
                background-color: {bg_color};
                border-radius: 4px;
                border: none;
            }}
        """)
        self.name_label.setStyleSheet(f"font-size: 12px; color: {text_color}; background: transparent;")
        self.index_label.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
    
    def enterEvent(self, event):
        self._is_hovered = True
        if not self._is_current:
            self.setStyleSheet("""
                SongListItem {
                    background-color: rgba(0, 0, 0, 0.05);
                    border-radius: 4px;
                    border: none;
                }
            """)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
    
    def update_theme(self, is_dark: bool):
        index_color = "#aaa" if is_dark else "#888"
        
        if self._is_current:
            text_color = "#60a5fa" if is_dark else "#0078d4"
            icon_color = "#60a5fa" if is_dark else "#0078d4"
        else:
            text_color = "#e0e0e0" if is_dark else "#333"
            icon_color = "#60a5fa" if is_dark else "#0078d4"
        
        self.name_label.setStyleSheet(f"font-size: 12px; color: {text_color}; background: transparent;")
        self.index_label.setStyleSheet(f"font-size: 11px; color: {index_color}; background: transparent;")
        self.current_icon.setStyleSheet(f"font-size: 10px; color: {icon_color}; background: transparent;")
        
        self._update_style()


class SongListPopup(QFrame):
    song_selected = pyqtSignal(int)
    
    RESIZE_MARGIN = 6
    
    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setMinimumSize(180, 150)
        self.resize(200, 250)
        
        self._drag_pos = None
        self._resize_dir = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        
        self.setMouseTracking(True)
        
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(4)
        
        title = QLabel("歌曲列表")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #333; padding: 4px;")
        self._main_layout.addWidget(title)
        
        self._scroll_area = QScrollArea()
        self._setup_scroll_area()
    
    def _get_resize_direction(self, pos):
        rect = self.rect()
        x, y = pos.x(), pos.y()
        margin = self.RESIZE_MARGIN
        
        on_left = x <= margin
        on_right = x >= rect.width() - margin
        on_top = y <= margin
        on_bottom = y >= rect.height() - margin
        
        if on_top and on_left:
            return 'topleft'
        elif on_top and on_right:
            return 'topright'
        elif on_bottom and on_left:
            return 'bottomleft'
        elif on_bottom and on_right:
            return 'bottomright'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'
        return None
    
    def _update_cursor(self, direction):
        cursors = {
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'topleft': Qt.SizeFDiagCursor,
            'bottomright': Qt.SizeFDiagCursor,
            'topright': Qt.SizeBDiagCursor,
            'bottomleft': Qt.SizeBDiagCursor,
        }
        if direction and direction in cursors:
            self.setCursor(cursors[direction])
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resize_dir = self._get_resize_direction(event.pos())
            if self._resize_dir:
                self._resize_start_pos = event.globalPos()
                self._resize_start_geom = self.geometry()
            else:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._resize_dir and self._resize_start_geom:
                self._handle_resize(event.globalPos())
            elif self._drag_pos is not None:
                self.move(event.globalPos() - self._drag_pos)
        else:
            direction = self._get_resize_direction(event.pos())
            self._update_cursor(direction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resize_dir = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)
    
    def _handle_resize(self, global_pos):
        delta = global_pos - self._resize_start_pos
        geom = QRect(self._resize_start_geom)
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        
        if 'right' in self._resize_dir:
            new_w = geom.width() + delta.x()
            if new_w >= min_w:
                geom.setWidth(new_w)
        if 'left' in self._resize_dir:
            new_w = geom.width() - delta.x()
            if new_w >= min_w:
                geom.setLeft(geom.left() + delta.x())
        if 'bottom' in self._resize_dir:
            new_h = geom.height() + delta.y()
            if new_h >= min_h:
                geom.setHeight(new_h)
        if 'top' in self._resize_dir:
            new_h = geom.height() - delta.y()
            if new_h >= min_h:
                geom.setTop(geom.top() + delta.y())
        
        self.setGeometry(geom)
    
    def _setup_scroll_area(self):
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #999;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        
        self._scroll_area.setWidget(self._list_container)
        self._main_layout.addWidget(self._scroll_area)
        
        self._song_items = []
        self._current_index = -1
        
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            SongListPopup {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
    
    def showEvent(self, event):
        super().showEvent(event)
        QApplication.instance().installEventFilter(self)
    
    def hideEvent(self, event):
        super().hideEvent(event)
        QApplication.instance().removeEventFilter(self)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not self.rect().contains(self.mapFromGlobal(event.globalPos())):
                self.hide()
                return True
        return super().eventFilter(obj, event)
    
    def set_songs(self, songs: list, current_index: int):
        for item in self._song_items:
            item.deleteLater()
        self._song_items.clear()
        
        self._current_index = current_index
        
        for i, song in enumerate(songs):
            if isinstance(song, str):
                name = os.path.splitext(os.path.basename(song))[0]
            else:
                name = song.name
            
            if len(name) > 18:
                name = name[:18] + "..."
            
            item = SongListItem(i, name, i == current_index)
            item.clicked.connect(self._on_item_clicked)
            self._list_layout.insertWidget(self._list_layout.count() - 1, item)
            self._song_items.append(item)
    
    def update_current(self, current_index: int):
        self._current_index = current_index
        for i, item in enumerate(self._song_items):
            item.set_current(i == current_index)
    
    def _on_item_clicked(self, index: int):
        self.song_selected.emit(index)
        self.hide()
    
    def update_theme(self, is_dark: bool):
        bg_color = "#2b2b2b" if is_dark else "#f9f9f9"
        border_color = "#404040" if is_dark else "#e0e0e0"
        title_color = "#e0e0e0" if is_dark else "#333"
        
        self.setStyleSheet(f"""
            SongListPopup {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)
        
        for item in self._song_items:
            item.update_theme(is_dark)
        
        for child in self.findChildren(QLabel):
            if child.text() == "歌曲列表":
                child.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {title_color}; padding: 4px;")
                break


class OnlineSearchPopup(QFrame):
    song_selected = pyqtSignal(object)
    search_requested = pyqtSignal(str, list)
    
    RESIZE_MARGIN = 8
    
    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setMinimumSize(320, 350)
        self.resize(360, 420)
        
        self._song_items = []
        self._is_dark = False
        self._drag_pos = None
        self._resize_dir = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        
        self.setMouseTracking(True)
        self._init_ui()
    
    def _get_resize_direction(self, pos):
        rect = self.rect()
        x, y = pos.x(), pos.y()
        margin = self.RESIZE_MARGIN
        
        on_left = x <= margin
        on_right = x >= rect.width() - margin
        on_top = y <= margin
        on_bottom = y >= rect.height() - margin
        
        if on_top and on_left:
            return 'topleft'
        elif on_top and on_right:
            return 'topright'
        elif on_bottom and on_left:
            return 'bottomleft'
        elif on_bottom and on_right:
            return 'bottomright'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'
        return None
    
    def _update_cursor(self, direction):
        cursors = {
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'topleft': Qt.SizeFDiagCursor,
            'bottomright': Qt.SizeFDiagCursor,
            'topright': Qt.SizeBDiagCursor,
            'bottomleft': Qt.SizeBDiagCursor,
        }
        if direction and direction in cursors:
            self.setCursor(cursors[direction])
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resize_dir = self._get_resize_direction(event.pos())
            if self._resize_dir:
                self._resize_start_pos = event.globalPos()
                self._resize_start_geom = self.geometry()
            else:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._resize_dir and self._resize_start_geom:
                self._handle_resize(event.globalPos())
            elif self._drag_pos is not None:
                self.move(event.globalPos() - self._drag_pos)
        else:
            direction = self._get_resize_direction(event.pos())
            self._update_cursor(direction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resize_dir = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)
    
    def _handle_resize(self, global_pos):
        delta = global_pos - self._resize_start_pos
        geom = QRect(self._resize_start_geom)
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        
        if 'right' in self._resize_dir:
            new_w = geom.width() + delta.x()
            if new_w >= min_w:
                geom.setWidth(new_w)
        if 'left' in self._resize_dir:
            new_w = geom.width() - delta.x()
            if new_w >= min_w:
                geom.setLeft(geom.left() + delta.x())
        if 'bottom' in self._resize_dir:
            new_h = geom.height() + delta.y()
            if new_h >= min_h:
                geom.setHeight(new_h)
        if 'top' in self._resize_dir:
            new_h = geom.height() - delta.y()
            if new_h >= min_h:
                geom.setTop(geom.top() + delta.y())
        
        self.setGeometry(geom)
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("🔍 在线搜索")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        
        self.close_btn = TransparentToolButton(FIF.CLOSE, self)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setIconSize(self.close_btn.size())
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title, 1)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(header_layout)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("全部平台", ["NeteaseMusicClient", "QQMusicClient", "KuwoMusicClient"])
        self.platform_combo.addItem("网易云", ["NeteaseMusicClient"])
        self.platform_combo.addItem("QQ音乐", ["QQMusicClient"])
        self.platform_combo.addItem("酷我音乐", ["KuwoMusicClient"])
        self.platform_combo.addItem("酷狗音乐", ["KugouMusicClient"])
        self.platform_combo.addItem("咪咕音乐", ["MiguMusicClient"])
        self.platform_combo.setFixedWidth(90)
        self.platform_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 12px;
                background: white;
            }
            QComboBox:hover {
                border: 1px solid #0078d4;
            }
            QComboBox::drop-down {
                border: 1px solid #0078d4;
            }
        """)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入歌曲名或歌手名...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.setFixedWidth(60)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.search_btn.clicked.connect(self._on_search)
        
        search_layout.addWidget(self.platform_combo)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        
        main_layout.addLayout(search_layout)
        
        self.status_label = QLabel("输入关键词搜索在线音乐")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-size: 12px; padding: 20px;")
        main_layout.addWidget(self.status_label)
        
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 3px;
                min-height: 20px;
            }
        """)
        
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        
        self._scroll_area.setWidget(self._list_container)
        self._scroll_area.hide()
        main_layout.addWidget(self._scroll_area, 1)
        
        self._apply_style()
    
    def _apply_style(self):
        bg_color = "#2b2b2b" if self._is_dark else "#f9f9f9"
        border_color = "#404040" if self._is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            OnlineSearchPopup {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
    
    def _on_search(self):
        keyword = self.search_input.text().strip()
        if keyword:
            platforms = self.platform_combo.currentData()
            self.status_label.setText("正在搜索...")
            self.status_label.show()
            self._scroll_area.hide()
            self.search_requested.emit(keyword, platforms)
    
    def set_results(self, songs: list):
        for item in self._song_items:
            item.deleteLater()
        self._song_items.clear()
        
        if not songs:
            self.status_label.setText("未找到相关歌曲")
            self.status_label.show()
            self._scroll_area.hide()
            return
        
        self.status_label.hide()
        self._scroll_area.show()
        
        for i, song in enumerate(songs):
            item = OnlineSongItem(song, i)
            item.play_clicked.connect(self._on_song_clicked)
            item.update_theme(self._is_dark)
            self._list_layout.insertWidget(self._list_layout.count() - 1, item)
            self._song_items.append(item)
    
    def _on_song_clicked(self, song_info):
        self.song_selected.emit(song_info)
        self.hide()
    
    def set_loading(self, is_loading: bool):
        if is_loading:
            self.status_label.setText("正在搜索...")
            self.search_btn.setEnabled(False)
            self.search_input.setEnabled(False)
        else:
            self.search_btn.setEnabled(True)
            self.search_input.setEnabled(True)
    
    def set_error(self, error_msg: str):
        self.status_label.setText(f"搜索失败: {error_msg}")
        self.status_label.show()
        self._scroll_area.hide()
    
    def update_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self._apply_style()
        
        title_color = "#e0e0e0" if is_dark else "#333"
        status_color = "#aaa" if is_dark else "#888"
        input_bg = "#3a3a3a" if is_dark else "#fff"
        input_border = "#505050" if is_dark else "#e0e0e0"
        combo_bg = "#3a3a3a" if is_dark else "#fff"
        combo_border = "#505050" if is_dark else "#e0e0e0"
        btn_bg = "#0078d4"
        btn_hover = "#106ebe"
        scroll_handle = "#666" if is_dark else "#ccc"
        
        for item in self._song_items:
            item.update_theme(is_dark)
        
        for child in self.findChildren(QLabel):
            if child.text() == "🔍 在线搜索":
                child.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {title_color};")
        
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 12px; padding: 20px;")
        
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 1px solid {input_border};
                border-radius: 6px;
                font-size: 13px;
                background: {input_bg};
                color: {title_color};
            }}
            QLineEdit:focus {{
                border: 1px solid #0078d4;
            }}
        """)
        
        self.platform_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 6px 10px;
                border: 1px solid {combo_border};
                border-radius: 6px;
                font-size: 12px;
                background: {combo_bg};
                color: {title_color};
            }}
            QComboBox:hover {{
                border: 1px solid #0078d4;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background: {combo_bg};
                border: 1px solid {combo_border};
                border-radius: 4px;
                outline: none;
                padding: 4px;
                alternate-background-color: {combo_bg};
            }}
            QComboBox QAbstractItemView::item {{
                height: 28px;
                padding: 4px 8px;
                border-radius: 4px;
                color: {title_color};
                background: transparent;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: rgba(0, 120, 212, 0.2);
                color: {title_color};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: rgba(0, 120, 212, 0.3);
                color: {title_color};
            }}
        """)
        
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #888;
            }}
        """)
    
    def showEvent(self, event):
        super().showEvent(event)
        self.search_input.setFocus()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class OnlineSongItem(QFrame):
    play_clicked = pyqtSignal(object)
    
    def __init__(self, song_info: SongInfo, index: int, parent=None):
        super().__init__(parent)
        self.song_info = song_info
        self._index = index
        self._is_hovered = False
        self._is_dark = False
        
        self.setFixedHeight(56)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        self.index_label = QLabel(f"{self._index + 1}")
        self.index_label.setFixedWidth(24)
        self.index_label.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(self.song_info.name)
        self.name_label.setStyleSheet("font-size: 13px; font-weight: bold; background: transparent;")
        
        singer_album = self.song_info.singer
        if self.song_info.album:
            singer_album += f" - {self.song_info.album}"
        
        self.singer_label = QLabel(singer_album)
        self.singer_label.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.singer_label)
        
        self.source_label = QLabel(self._get_source_name(self.song_info.source))
        self.source_label.setStyleSheet("""
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 3px;
            background: rgba(0, 120, 212, 0.1);
            color: #0078d4;
        """)
        
        self.play_btn = TransparentToolButton(FIF.PLAY, self)
        self.play_btn.setFixedSize(28, 28)
        self.play_btn.setIconSize(self.play_btn.size())
        self.play_btn.setToolTip("播放")
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.song_info))
        
        layout.addWidget(self.index_label)
        layout.addLayout(info_layout, 1)
        layout.addWidget(self.source_label)
        layout.addWidget(self.play_btn)
        
        self._update_style()
    
    def _get_source_name(self, source: str) -> str:
        source_names = {
            'NeteaseMusicClient': '网易云',
            'QQMusicClient': 'QQ音乐',
            'KugouMusicClient': '酷狗',
            'KuwoMusicClient': '酷我',
            'MiguMusicClient': '咪咕',
            'local': '本地'
        }
        return source_names.get(source, source[:4] if len(source) > 4 else source)
    
    def _update_style(self):
        self.setStyleSheet("""
            OnlineSongItem {
                background-color: transparent;
                border-radius: 6px;
                border: none;
            }
        """)
    
    def enterEvent(self, event):
        self._is_hovered = True
        hover_bg = "rgba(255,255,255, 0.08)" if self._is_dark else "rgba(0, 0, 0, 0.08)"
        self.setStyleSheet(f"""
            OnlineSongItem {{
                background-color: {hover_bg};
                border-radius: 6px;
                border: none;
            }}
        """)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_clicked.emit(self.song_info)
    
    def update_theme(self, is_dark: bool):
        self._is_dark = is_dark
        index_color = "#aaa" if is_dark else "#888"
        singer_color = "#aaa" if is_dark else "#888"
        name_color = "#e0e0e0" if is_dark else "#333"
        
        self.index_label.setStyleSheet(f"font-size: 12px; color: {index_color}; background: transparent;")
        self.name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {name_color}; background: transparent;")
        self.singer_label.setStyleSheet(f"font-size: 11px; color: {singer_color}; background: transparent;")
        
        if is_dark:
            self.source_label.setStyleSheet("""
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 3px;
                background: rgba(96, 165, 250, 0.2);
                color: #60a5fa;
            """)
        else:
            self.source_label.setStyleSheet("""
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 3px;
                background: rgba(0, 120, 212, 0.1);
                color: #0078d4;
            """)
        
        if self._is_hovered:
            hover_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.05)"
            self.setStyleSheet(f"""
                OnlineSongItem {{
                    background-color: {hover_bg};
                    border-radius: 6px;
                    border: none;
                }}
            """)


class ClickableSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.maximum() > 0:
                value = int((event.x() / self.width()) * self.maximum())
                self.setValue(value)
                self.sliderMoved.emit(value)
        super().mousePressEvent(event)


class MusicPlayerCard(CardWidget):
    playback_state_changed = pyqtSignal(bool)
    play_mode_changed = pyqtSignal(object)
    
    MUSIC_PATH = os.path.join("data", "resourse", "music")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_user_seeking = False
        self._is_online_mode = False
        self._current_online_song = None
        self._play_mode = PlayMode.LIST_LOOP
        self._played_indices = set()
        
        self._music_service = MusicService(self)
        self._init_player()
        self._init_ui()
        self._connect_service_signals()
        self._load_music_files()
    
    def _init_player(self):
        self.player = QMediaPlayer()
        self.player.setVolume(50)
        
        self._position_timer = QTimer(self)
        self._position_timer.setInterval(100)
        self._position_timer.timeout.connect(self._update_position)
        
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.stateChanged.connect(self._on_state_changed)
    
    def _connect_service_signals(self):
        self._music_service.search_completed.connect(self._on_search_completed)
        self._music_service.search_failed.connect(self._on_search_failed)
        self._music_service.play_url_obtained.connect(self._on_play_url_obtained)
        self._music_service.play_url_failed.connect(self._on_play_url_failed)
    
    def _init_ui(self):
        self.setMinimumHeight(120)
        self.setMaximumHeight(150)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self.music_icon = QLabel("🎵")
        self.music_icon.setStyleSheet("font-size: 18px; background: transparent;")
        
        self.title_label = QLabel("音乐播放")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)
        
        self.track_label = QLabel("未加载音乐")
        self.track_label.setStyleSheet("font-size: 12px; color: #888;")
        
        header_layout.addWidget(self.music_icon)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.track_label)
        
        main_layout.addLayout(header_layout)
        
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)
        
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("font-size: 11px; color: #888;")
        self.current_time_label.setFixedWidth(35)
        
        self.progress_slider = ClickableSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setFixedHeight(20)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        self._apply_slider_style(self.progress_slider, "#0078d4")
        
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("font-size: 11px; color: #888;")
        self.total_time_label.setFixedWidth(35)
        
        progress_layout.addWidget(self.current_time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time_label)
        
        main_layout.addLayout(progress_layout)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        self.prev_btn = TransparentToolButton(FIF.CARE_LEFT_SOLID, self)
        self.prev_btn.setFixedSize(16, 16)
        self.prev_btn.setIconSize(self.prev_btn.size())
        self.prev_btn.setToolTip("上一首")
        self.prev_btn.clicked.connect(self._play_previous)
        
        self.play_btn = TransparentToolButton(FIF.PLAY, self)
        self.play_btn.setFixedSize(16, 16)
        self.play_btn.setIconSize(self.play_btn.size())
        self.play_btn.setToolTip("播放")
        self.play_btn.clicked.connect(self._toggle_play)
        
        self.next_btn = TransparentToolButton(FIF.CARE_RIGHT_SOLID, self)
        self.next_btn.setFixedSize(16, 16)
        self.next_btn.setIconSize(self.next_btn.size())
        self.next_btn.setToolTip("下一首")
        self.next_btn.clicked.connect(self._play_next)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addStretch()
        
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(6)
        
        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("font-size: 14px;")
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setFixedHeight(20)
        self.volume_slider.setToolTip("音量")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self._apply_volume_slider_style(self.volume_slider)
        
        self.volume_value_label = QLabel("50%")
        self.volume_value_label.setStyleSheet("font-size: 11px; color: #888;")
        self.volume_value_label.setFixedWidth(30)
        
        volume_layout.addStretch()
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        
        self.song_list_btn = TransparentToolButton(FIF.MUSIC, self)
        self.song_list_btn.setFixedSize(16, 16)
        self.song_list_btn.setIconSize(self.song_list_btn.size())
        self.song_list_btn.setToolTip("本地歌曲列表")
        self.song_list_btn.clicked.connect(self._toggle_song_list)
        
        self.mode_btn = TransparentToolButton(FIF.SYNC, self)
        self.mode_btn.setFixedSize(16, 16)
        self.mode_btn.setIconSize(self.mode_btn.size())
        self.mode_btn.setToolTip("列表循环")
        self.mode_btn.clicked.connect(self._toggle_play_mode)
        
        volume_layout.addWidget(self.mode_btn)
        volume_layout.addWidget(self.song_list_btn)
        
        self.online_btn = TransparentToolButton(FIF.SEARCH, self)
        self.online_btn.setFixedSize(16, 16)
        self.online_btn.setIconSize(self.online_btn.size())
        self.online_btn.setToolTip("在线搜索")
        self.online_btn.clicked.connect(self._toggle_online_search)
        volume_layout.addWidget(self.online_btn)
        
        controls_layout.addLayout(volume_layout)
        
        main_layout.addLayout(controls_layout)
        
        self._song_popup = SongListPopup(self)
        self._song_popup.song_selected.connect(self._on_song_selected)
        
        self._online_popup = OnlineSearchPopup(self)
        self._online_popup.song_selected.connect(self._on_online_song_selected)
        self._online_popup.search_requested.connect(self._on_search_requested)
    
    def _apply_slider_style(self, slider, color):
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background: #e0e0e0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {color};
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #106ebe;
            }}
            QSlider::sub-page:horizontal {{
                background: {color};
                border-radius: 2px;
            }}
        """)
    
    def _apply_volume_slider_style(self, slider):
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #e0e0e0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #666;
                border: none;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #444;
            }
            QSlider::sub-page:horizontal {
                background: #888;
                border-radius: 2px;
            }
        """)
    
    def _load_music_files(self):
        self._music_files = []
        self._current_index = 0
        
        music_dir = self.MUSIC_PATH
        if not os.path.isabs(music_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            music_dir = os.path.join(base_dir, music_dir)
        
        if os.path.exists(music_dir):
            supported_formats = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma')
            try:
                files = os.listdir(music_dir)
                self._music_files = [
                    os.path.join(music_dir, f) for f in files 
                    if f.lower().endswith(supported_formats)
                ]
                self._music_files.sort()
            except Exception as e:
                print(f"Error loading music files: {e}")
        
        if self._music_files:
            self._load_track(0)
            self._update_song_popup()
    
    def _update_song_popup(self):
        if hasattr(self, '_song_popup'):
            self._song_popup.set_songs(self._music_files, self._current_index)
    
    def set_play_mode(self, mode: PlayMode):
        self._play_mode = mode
        if mode == PlayMode.SHUFFLE:
            self._played_indices.clear()
        self.play_mode_changed.emit(mode)
        self._update_mode_button()
    
    def get_play_mode(self) -> PlayMode:
        return self._play_mode
    
    def get_next_index(self) -> int:
        if not self._music_files:
            return -1
        
        total = len(self._music_files)
        
        if self._play_mode == PlayMode.SINGLE_LOOP:
            return self._current_index
        
        elif self._play_mode == PlayMode.SEQUENCE:
            next_idx = self._current_index + 1
            return next_idx if next_idx < total else -1
        
        elif self._play_mode == PlayMode.LIST_LOOP:
            return (self._current_index + 1) % total
        
        elif self._play_mode == PlayMode.SHUFFLE:
            return self._get_random_index()
        
        return -1
    
    def _get_random_index(self) -> int:
        total = len(self._music_files)
        
        if len(self._played_indices) >= total:
            self._played_indices.clear()
        
        available = [i for i in range(total) 
                     if i != self._current_index and i not in self._played_indices]
        
        if not available:
            return self._current_index
        
        next_idx = random.choice(available)
        self._played_indices.add(next_idx)
        return next_idx
    
    def _toggle_play_mode(self):
        modes = list(PlayMode)
        current_idx = modes.index(self._play_mode)
        next_mode = modes[(current_idx + 1) % len(modes)]
        self.set_play_mode(next_mode)
    
    def _update_mode_button(self):
        mode_config = {
            PlayMode.SEQUENCE: (FIF.RIGHT_ARROW, "顺序播放"),
            PlayMode.LIST_LOOP: (FIF.SYNC, "列表循环"),
            PlayMode.SINGLE_LOOP: (FIF.UPDATE, "单曲循环"),
            PlayMode.SHUFFLE: (FIF.TILES, "随机播放"),
        }
        icon, tooltip = mode_config[self._play_mode]
        self.mode_btn.setIcon(icon)
        self.mode_btn.setToolTip(tooltip)
    
    def _toggle_song_list(self):
        if self._online_popup.isVisible():
            self._online_popup.hide()
        
        if self._song_popup.isVisible():
            self._song_popup.hide()
        else:
            self._update_song_popup()
            btn_rect = self.song_list_btn.rect()
            popup_pos = self.song_list_btn.mapToGlobal(QPoint(btn_rect.width(), btn_rect.height() + 5))
            self._song_popup.move(popup_pos)
            self._song_popup.show()
    
    def _toggle_online_search(self):
        if self._song_popup.isVisible():
            self._song_popup.hide()
        
        if self._online_popup.isVisible():
            self._online_popup.hide()
        else:
            btn_rect = self.online_btn.rect()
            popup_pos = self.online_btn.mapToGlobal(QPoint(btn_rect.width() - self._online_popup.width() + 16, btn_rect.height() + 5))
            self._online_popup.move(popup_pos)
            self._online_popup.show()
    
    def _on_search_requested(self, keyword: str, platforms: list):
        self._online_popup.set_loading(True)
        self._music_service.search(keyword, platforms)
    
    def _on_search_completed(self, songs: list):
        self._online_popup.set_loading(False)
        self._online_popup.set_results(songs)
    
    def _on_search_failed(self, error_msg: str):
        self._online_popup.set_loading(False)
        self._online_popup.set_error(error_msg)
    
    def _on_online_song_selected(self, song_info: SongInfo):
        self._is_online_mode = True
        self._current_online_song = song_info
        
        track_name = f"{song_info.name} - {song_info.singer}"
        if len(track_name) > 20:
            track_name = track_name[:20] + "..."
        self.track_label.setText(track_name)
        
        self._online_popup.hide()
        
        if song_info.play_url:
            self._play_online_url(song_info.play_url)
        else:
            self.track_label.setText("获取播放链接...")
            self._music_service.get_play_url(song_info)
    
    def _on_play_url_obtained(self, song_id: str, url: str):
        if self._current_online_song and self._current_online_song.song_id == song_id:
            self._play_online_url(url)
    
    def _on_play_url_failed(self, song_id: str):
        if self._current_online_song and self._current_online_song.song_id == song_id:
            self.track_label.setText("获取链接失败")
    
    def _play_online_url(self, url: str):
        media_content = self._music_service.create_media_content(url)
        self.player.setMedia(media_content)
        self.player.play()
    
    def _on_song_selected(self, index: int):
        if 0 <= index < len(self._music_files):
            self._is_online_mode = False
            self._load_track(index)
            self.player.play()
            self._song_popup.update_current(index)
    
    def _load_track(self, index):
        if 0 <= index < len(self._music_files):
            self._current_index = index
            file_path = self._music_files[index]
            track_name = os.path.splitext(os.path.basename(file_path))[0]
            
            if len(track_name) > 15:
                track_name = track_name[:15] + "..."
            
            self.track_label.setText(track_name)
            
            url = QUrl.fromLocalFile(file_path)
            content = QMediaContent(url)
            self.player.setMedia(content)
            
            if hasattr(self, '_song_popup'):
                self._song_popup.update_current(index)
    
    def _toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def _play_previous(self):
        if self._is_online_mode:
            return
        if self._music_files:
            self._current_index = (self._current_index - 1) % len(self._music_files)
            self._load_track(self._current_index)
            self.player.play()
    
    def _play_next(self):
        if self._is_online_mode:
            return
        if self._music_files:
            next_index = self.get_next_index()
            if next_index >= 0:
                self._current_index = next_index
                self._load_track(self._current_index)
                self.player.play()
    
    def _on_slider_pressed(self):
        self._is_user_seeking = True
    
    def _on_slider_released(self):
        self._is_user_seeking = False
        position = self.progress_slider.value()
        self.player.setPosition(position)
    
    def _on_slider_moved(self, value):
        self.current_time_label.setText(self._format_time(value))
    
    def _on_volume_changed(self, value):
        self.player.setVolume(value)
        self.volume_value_label.setText(f"{value}%")
    
    def _on_duration_changed(self, duration):
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(self._format_time(duration))
    
    def _on_position_changed(self, position):
        if not self._is_user_seeking:
            self.progress_slider.setValue(position)
            self.current_time_label.setText(self._format_time(position))
    
    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(FIF.PAUSE)
            self.play_btn.setToolTip("暂停")
            self._position_timer.start()
            self.playback_state_changed.emit(True)
        else:
            self.play_btn.setIcon(FIF.PLAY)
            self.play_btn.setToolTip("播放")
            self._position_timer.stop()
            self.playback_state_changed.emit(False)
            
            if state == QMediaPlayer.StoppedState and not self._is_online_mode and self._music_files:
                if self.progress_slider.value() >= self.progress_slider.maximum() - 100:
                    self._handle_track_finished()
    
    def _handle_track_finished(self):
        if self._play_mode == PlayMode.SINGLE_LOOP:
            self.player.setPosition(0)
            self.player.play()
        else:
            next_index = self.get_next_index()
            if next_index >= 0:
                self._current_index = next_index
                self._load_track(self._current_index)
                self.player.play()
    
    def _update_position(self):
        pass
    
    def _format_time(self, ms):
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def auto_play(self):
        if self._music_files:
            self.player.play()
    
    def stop(self):
        self.player.stop()
    
    def pause(self):
        self.player.pause()
    
    def update_theme(self, is_dark: bool):
        title_color = "#e0e0e0" if is_dark else "#333"
        track_color = "#aaa" if is_dark else "#888"
        time_color = "#aaa" if is_dark else "#888"
        groove_bg = "#3a3a3a" if is_dark else "#e0e0e0"
        handle_bg = "#666" if is_dark else "#888"
        handle_hover = "#888" if is_dark else "#444"
        
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {title_color};
            }}
        """)
        self.track_label.setStyleSheet(f"font-size: 12px; color: {track_color};")
        self.current_time_label.setStyleSheet(f"font-size: 11px; color: {time_color};")
        self.total_time_label.setStyleSheet(f"font-size: 11px; color: {time_color};")
        self.volume_value_label.setStyleSheet(f"font-size: 11px; color: {time_color};")
        
        accent_color = "#60a5fa" if is_dark else "#0078d4"
        self._apply_slider_style(self.progress_slider, accent_color)
        
        self.volume_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background: {groove_bg};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {handle_bg};
                border: none;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {handle_hover};
            }}
            QSlider::sub-page:horizontal {{
                background: {handle_bg};
                border-radius: 2px;
            }}
        """)
        
        if hasattr(self, '_song_popup'):
            self._song_popup.update_theme(is_dark)
        
        if hasattr(self, '_online_popup'):
            self._online_popup.update_theme(is_dark)
    
    def closeEvent(self, event):
        self.player.stop()
        self._music_service.stop_workers()
        if hasattr(self, '_song_popup'):
            self._song_popup.hide()
        if hasattr(self, '_online_popup'):
            self._online_popup.hide()
        super().closeEvent(event)
