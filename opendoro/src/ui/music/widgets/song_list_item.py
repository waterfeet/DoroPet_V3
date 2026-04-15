from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics, QFont, QPixmap
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QMenu, 
                             QAction, QCheckBox)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import QUrl
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF

from src.services.extended_music_service import SongInfo, MUSIC_SOURCES
from ..network_manager import NetworkManager


class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class PlaylistItemWidget(QFrame):
    remove_clicked = pyqtSignal()
    play_clicked = pyqtSignal()
    add_to_queue_clicked = pyqtSignal()
    
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self._is_hovered = False
        self._init_ui()
    
    def _init_ui(self):
        self.setFixedHeight(60)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        self.icon_label = QLabel("🎵")
        self.icon_label.setFixedWidth(40)
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(self.playlist.name)
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.count_label = QLabel(f"{len(self.playlist.songs)} 首歌曲")
        self.count_label.setStyleSheet("font-size: 12px; color: #888;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.count_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)
        
        self.play_btn = TransparentToolButton(FIF.PLAY, self)
        self.play_btn.setFixedSize(28, 28)
        self.play_btn.setToolTip("播放全部")
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit())
        
        self.add_queue_btn = TransparentToolButton(FIF.ADD_TO, self)
        self.add_queue_btn.setFixedSize(28, 28)
        self.add_queue_btn.setToolTip("添加到播放列表")
        self.add_queue_btn.clicked.connect(lambda: self.add_to_queue_clicked.emit())
        
        self.remove_btn = TransparentToolButton(FIF.DELETE, self)
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setToolTip("删除歌单")
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit())
        
        actions_layout.addWidget(self.play_btn)
        actions_layout.addWidget(self.add_queue_btn)
        actions_layout.addWidget(self.remove_btn)
        
        layout.addWidget(self.icon_label)
        layout.addLayout(info_layout, 1)
        layout.addLayout(actions_layout)
    
    def _update_style(self):
        if self._is_hovered:
            bg = "rgba(0, 0, 0, 0.05)"
        else:
            bg = "transparent"
        self.setStyleSheet(f"background: {bg}; border-radius: 6px;")
    
    def enterEvent(self, event):
        self._is_hovered = True
        self._update_style()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
        super().leaveEvent(event)


class SongListItemWidget(QFrame):
    double_clicked = pyqtSignal(int)
    add_to_playlist_clicked = pyqtSignal(int)
    add_to_playqueue_clicked = pyqtSignal(int)
    remove_from_playlist_clicked = pyqtSignal(int)
    remove_from_playqueue_clicked = pyqtSignal(int)
    selection_changed = pyqtSignal(int, bool)
    download_clicked = pyqtSignal(int)
    
    def __init__(self, song_info: SongInfo, index: int, is_playing: bool = False, 
                 parent=None, show_remove: bool = False, show_playqueue_actions: bool = False, 
                 show_checkbox: bool = False, show_download: bool = True):
        super().__init__(parent)
        self.song_info = song_info
        self.index = index
        self.is_playing = is_playing
        self._is_hovered = False
        self._is_dark = False
        self.show_remove = show_remove
        self.show_playqueue_actions = show_playqueue_actions
        self.show_checkbox = show_checkbox
        self.show_download = show_download
        self._is_selected = False
        self._network_manager = NetworkManager.get_instance()
        
        self.setFixedHeight(50 if self.show_playqueue_actions else 60)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()
        self._load_cover()
    
    def _load_cover(self):
        if not self.song_info.img_url:
            return
        
        def on_cover_loaded(pixmap: QPixmap):
            if not pixmap.isNull():
                scaled = pixmap.scaled(44, 44, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.cover_label.setPixmap(scaled)
        
        self._network_manager.fetch_image(self.song_info.img_url, on_cover_loaded)
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        if self.show_checkbox:
            self.checkbox = QCheckBox()
            self.checkbox.setFixedSize(20, 20)
            self.checkbox.stateChanged.connect(self._on_checkbox_changed)
            layout.addWidget(self.checkbox)
        
        if not self.show_playqueue_actions:
            self.index_label = QLabel(f"{self.index + 1}")
            self.index_label.setFixedWidth(24)
            self.index_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.index_label)
        
        self.cover_label = QLabel()
        self.cover_label.setObjectName("musicCoverLabel")
        cover_size = 36 if self.show_playqueue_actions else 44
        self.cover_label.setFixedSize(cover_size, cover_size)
        
        if self.song_info.img_url:
            self.cover_label.setText("🎵")
            self.cover_label.setAlignment(Qt.AlignCenter)
        else:
            self.cover_label.setText("🎵")
            self.cover_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.cover_label)
        
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(2)
        
        self.name_label = QLabel(self._truncate_text(self.song_info.name, 100))
        self.name_label.setObjectName("musicSongNameLabel")
        self.name_label.setWordWrap(False)
        self.name_label.setToolTip(self.song_info.name)
        
        singer_text = self.song_info.singer
        if self.song_info.album and not self.show_playqueue_actions:
            singer_text += f" - {self.song_info.album}"
        
        self.singer_label = QLabel(singer_text)
        self.singer_label.setObjectName("musicArtistLabel")
        self.singer_label.setWordWrap(False)
        
        self.info_layout.addWidget(self.name_label)
        self.info_layout.addWidget(self.singer_label)
        
        layout.addLayout(self.info_layout, 1)
        
        self.duration_label = QLabel(self._format_duration(self.song_info.duration))
        self.duration_label.setObjectName("musicTimeLabel")
        self.duration_label.setFixedWidth(40)
        layout.addWidget(self.duration_label)
        
        if not self.show_playqueue_actions:
            self.source_label = QLabel(self._get_source_name())
            self.source_label.setObjectName("musicSourceLabel")
            self.source_label.setFixedWidth(50)
            layout.addWidget(self.source_label)
        
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(2)
        
        self.play_btn = TransparentToolButton(FIF.PLAY, self)
        self.play_btn.setFixedSize(24, 24)
        self.play_btn.setToolTip("播放")
        self.play_btn.clicked.connect(lambda: self.double_clicked.emit(self.index))
        
        if self.show_playqueue_actions:
            self.remove_queue_btn = TransparentToolButton(FIF.DELETE, self)
            self.remove_queue_btn.setFixedSize(24, 24)
            self.remove_queue_btn.setToolTip("从播放列表移除")
            self.remove_queue_btn.clicked.connect(lambda: self.remove_from_playqueue_clicked.emit(self.index))
            self.actions_layout.addWidget(self.remove_queue_btn)
        else:
            self.add_queue_btn = TransparentToolButton(FIF.ADD, self)
            self.add_queue_btn.setFixedSize(24, 24)
            self.add_queue_btn.setToolTip("添加到播放列表")
            self.add_queue_btn.clicked.connect(lambda: self.add_to_playqueue_clicked.emit(self.index))
            self.actions_layout.addWidget(self.add_queue_btn)
        
        if self.show_remove:
            self.remove_btn = TransparentToolButton(FIF.DELETE, self)
            self.remove_btn.setFixedSize(24, 24)
            self.remove_btn.setToolTip("移除")
            self.remove_btn.clicked.connect(lambda: self.remove_from_playlist_clicked.emit(self.index))
            self.actions_layout.addWidget(self.remove_btn)
        elif not self.show_playqueue_actions:
            self.add_btn = TransparentToolButton(FIF.FOLDER_ADD, self)
            self.add_btn.setFixedSize(24, 24)
            self.add_btn.setToolTip("添加到歌单")
            self.add_btn.clicked.connect(lambda: self.add_to_playlist_clicked.emit(self.index))
            self.actions_layout.addWidget(self.add_btn)
        
        if self.show_download and self.song_info.source != "local":
            self.download_btn = TransparentToolButton(FIF.DOWNLOAD, self)
            self.download_btn.setFixedSize(24, 24)
            self.download_btn.setToolTip("下载到本地")
            self.download_btn.clicked.connect(lambda: self.download_clicked.emit(self.index))
            self.actions_layout.addWidget(self.download_btn)
        
        self.actions_layout.addWidget(self.play_btn)
        
        layout.addLayout(self.actions_layout)
        
        self._update_style()
    
    def _truncate_text(self, text: str, max_width: int, font=None) -> str:
        if font is None:
            font = self.font()
        font_metrics = QFontMetrics(font)
        if font_metrics.width(text) <= max_width:
            return text
        truncated = text
        while font_metrics.width(truncated + "...") > max_width and len(truncated) > 1:
            truncated = truncated[:-1]
        return truncated + "..." if truncated else text
    
    def _format_duration(self, seconds: int) -> str:
        try:
            seconds = int(seconds)
        except (ValueError, TypeError):
            seconds = 0
        if seconds <= 0:
            return "0:00"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    def _get_source_name(self) -> str:
        for key, value in MUSIC_SOURCES.items():
            if value['client'] == self.song_info.source:
                return value['name']
        return self.song_info.source[:4] if len(self.song_info.source) > 4 else self.song_info.source
    
    def _update_style(self):
        if self.is_playing:
            bg_color = "rgba(0, 120, 212, 0.1)"
            name_color = "#0078d4"
        else:
            bg_color = "transparent"
            name_color = "#333" if not self._is_dark else "#e0e0e0"
        
        self.setStyleSheet(f"""
            SongListItemWidget {{
                background-color: {bg_color};
                border-radius: 6px;
                border: none;
            }}
        """)
        self.name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {name_color};")
    
    def set_playing(self, is_playing: bool):
        self.is_playing = is_playing
        self._update_style()
    
    def enterEvent(self, event):
        self._is_hovered = True
        if not self.is_playing:
            hover_bg = "rgba(0, 0, 0, 0.05)" if not self._is_dark else "rgba(255, 255, 255, 0.05)"
            self.setStyleSheet(f"""
                SongListItemWidget {{
                    background-color: {hover_bg};
                    border-radius: 6px;
                    border: none;
                }}
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_style()
        super().leaveEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.index)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        play_action = QAction("播放", self)
        play_action.triggered.connect(lambda: self.double_clicked.emit(self.index))
        menu.addAction(play_action)
        
        add_queue_action = QAction("添加到播放列表", self)
        add_queue_action.triggered.connect(lambda: self.add_to_playqueue_clicked.emit(self.index))
        menu.addAction(add_queue_action)
        
        add_playlist_action = QAction("添加到歌单", self)
        add_playlist_action.triggered.connect(lambda: self.add_to_playlist_clicked.emit(self.index))
        menu.addAction(add_playlist_action)
        
        if self.show_playqueue_actions:
            menu.addSeparator()
            remove_queue_action = QAction("从播放列表移除", self)
            remove_queue_action.triggered.connect(lambda: self.remove_from_playqueue_clicked.emit(self.index))
            menu.addAction(remove_queue_action)
        
        menu.exec_(event.globalPos())
    
    def update_theme(self, is_dark: bool):
        self._is_dark = is_dark
        index_color = "#aaa" if is_dark else "#888"
        singer_color = "#aaa" if is_dark else "#888"
        name_color = "#0078d4" if self.is_playing else ("#e0e0e0" if is_dark else "#333")
        bg_color = "#2b2b2b" if is_dark else "#f9f9f9"
        
        if hasattr(self, 'index_label'):
            self.index_label.setStyleSheet(f"font-size: 12px; color: {index_color};")
        self.singer_label.setStyleSheet(f"font-size: 11px; color: {singer_color};")
        self.name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {name_color};")
        self.setStyleSheet(f"""
            SongListItemWidget {{
                background-color: {bg_color};
                border-radius: 6px;
                border: none;
            }}
        """)
    
    def _on_checkbox_changed(self, state):
        self._is_selected = (state == 2)
        self.selection_changed.emit(self.index, self._is_selected)
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        if self.show_checkbox:
            self.checkbox.blockSignals(True)
            self.checkbox.setChecked(selected)
            self.checkbox.blockSignals(False)
    
    def is_selected(self) -> bool:
        return self._is_selected
