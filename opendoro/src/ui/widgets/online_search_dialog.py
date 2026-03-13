from typing import List, Optional
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, 
    QSizePolicy, QLineEdit, QPushButton
)
from PyQt5.QtGui import QColor

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, LineEdit, 
    TransparentToolButton, FluentIcon as FIF, BodyLabel, SubtitleLabel
)


class SearchResultItem(CardWidget):
    play_clicked = pyqtSignal(object)
    add_to_playlist = pyqtSignal(object)
    
    def __init__(self, song_info, index: int = 0, parent=None):
        super().__init__(parent)
        self.song_info = song_info
        self._index = index
        self._is_hovered = False
        
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
        
        singer_album = f"{self.song_info.singer}"
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
            SearchResultItem {
                background-color: transparent;
                border-radius: 6px;
                border: none;
            }
        """)
    
    def enterEvent(self, event):
        self._is_hovered = True
        self.setStyleSheet("""
            SearchResultItem {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 6px;
                border: none;
            }
        """)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play_clicked.emit(self.song_info)
    
    def update_theme(self, is_dark: bool):
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


class OnlineSearchDialog(CardWidget):
    song_selected = pyqtSignal(object)
    search_requested = pyqtSignal(str)
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setFixedSize(360, 420)
        
        self._song_items = []
        self._is_dark = False
        
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title = SubtitleLabel("🔍 在线搜索", self)
        title.setAlignment(Qt.AlignLeft)
        
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
        
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("输入歌曲名或歌手名...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self._on_search)
        
        self.search_btn = PrimaryPushButton("搜索", self)
        self.search_btn.setFixedWidth(60)
        self.search_btn.clicked.connect(self._on_search)
        
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        
        main_layout.addLayout(search_layout)
        
        self.status_label = BodyLabel("输入关键词搜索在线音乐", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
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
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        
        self._scroll_area.setWidget(self._list_container)
        main_layout.addWidget(self._scroll_area, 1)
        
        self._apply_style()
    
    def _apply_style(self):
        bg_color = "#2b2b2b" if self._is_dark else "#f9f9f9"
        border_color = "#404040" if self._is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            OnlineSearchDialog {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
    
    def _on_search(self):
        keyword = self.search_input.text().strip()
        if keyword:
            self.status_label.setText("正在搜索...")
            self.status_label.show()
            self.search_requested.emit(keyword)
    
    def set_results(self, songs: list):
        for item in self._song_items:
            item.deleteLater()
        self._song_items.clear()
        
        if not songs:
            self.status_label.setText("未找到相关歌曲")
            self.status_label.show()
            return
        
        self.status_label.hide()
        
        for i, song in enumerate(songs):
            item = SearchResultItem(song, i)
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
            self.status_label.show()
            self.search_btn.setEnabled(False)
            self.search_input.setEnabled(False)
        else:
            self.search_btn.setEnabled(True)
            self.search_input.setEnabled(True)
    
    def set_error(self, error_msg: str):
        self.status_label.setText(f"搜索失败: {error_msg}")
        self.status_label.show()
    
    def update_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self._apply_style()
        
        title_color = "#e0e0e0" if is_dark else "#333"
        status_color = "#aaa" if is_dark else "#888"
        
        for item in self._song_items:
            item.update_theme(is_dark)
        
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 12px;")
    
    def showEvent(self, event):
        super().showEvent(event)
        self.search_input.setFocus()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
