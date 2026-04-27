import os
import random
from typing import List
from PyQt5.QtCore import (Qt, QTimer, QUrl, pyqtSignal, QSize, QEvent, 
                          QPropertyAnimation, QEasingCurve, QRectF)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QFrame, QScrollArea, QLineEdit, QPushButton, QComboBox, QSpinBox,
                             QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QAction,
                             QInputDialog, QMessageBox, QStackedWidget, QShortcut)
from PyQt5.QtGui import (QFont, QColor, QFontMetrics, QPalette, QLinearGradient, QRadialGradient, 
                         QPainter, QPainterPath, QBrush, QPen, QPixmap, QImage)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from qfluentwidgets import (CardWidget, PushButton, TransparentToolButton, ScrollArea,
                           LineEdit, ComboBox, SearchLineEdit, PrimaryPushButton,
                           IconWidget, BodyLabel, StrongBodyLabel, isDarkTheme, TabBar, ListWidget, SpinBox,
                           SubtitleLabel, Dialog, CheckBox)
from qfluentwidgets import FluentIcon as FIF

from src.services.extended_music_service import ExtendedMusicService, SongInfo, Playlist, get_music_data_dir
from src.services.global_music_player import GlobalMusicPlayer
from src.services.audio_spectrum_analyzer import AudioSpectrumAnalyzer
from src.core.logger import logger
from src.utils.lyric_parser import LyricParser, LyricLine

from .constants import PlayMode, PlayerConstants, ColorConstants, PLAY_MODE_CONFIG, PLATFORM_MAP
from .network_manager import NetworkManager
from .widgets import (
    VinylRecordWidget, LyricsCardWidget, SongListItemWidget, PlaylistItemWidget,
    ClickableLabel, DockablePlaylistWidget, SlidingPlayerPanel, ClickableSlider,
    StyledProgressBar, StyledVolumeSlider, SpectrumWidget, MiniSpectrumWidget
)


class MusicInterface(ScrollArea):
    switch_to_player = pyqtSignal(object)
    playqueue_changed = pyqtSignal()
    playlist_import_progress = pyqtSignal(str, int)
    playlist_imported = pyqtSignal(list)
    playlist_import_failed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MusicInterface")
        self.setWidgetResizable(True)
        self.setMinimumSize(900, 650)
        
        self._music_service = ExtendedMusicService(self)
        self.global_player = GlobalMusicPlayer.get_instance(self)
        self._network_manager = NetworkManager.get_instance()
        self._playlists: list = []
        self._play_queue: list = []
        self._current_index: int = -1
        self._play_mode = PlayMode.LIST_LOOP
        self._played_indices = set()
        self._is_user_seeking = False
        self._retry_count = 0
        self._local_playlist = []
        self._search_results = []
        self._playlist_songs = []
        self._original_cover_pixmap: QPixmap = None
        self._dominant_color: QColor = None
        
        self._selected_indices = {"search": set(), "local": set(), "playlist": set()}
        
        self._vinyl_record = None
        self._dockable_playlist = None
        
        self._init_ui()
        self._connect_signals()
        self._load_playlists()
        self._connect_global_player()
        self._init_default_playlist()
        self._init_local_music()
        self._connect_import_signals()
    
    def _connect_import_signals(self):
        self.playlist_import_progress.connect(self._update_import_progress)
        self.playlist_imported.connect(self._on_playlist_imported)
        self.playlist_import_failed.connect(self._on_playlist_import_failed)
    
    def _init_default_playlist(self):
        if not self._playlists:
            self._music_service.create_playlist("我喜欢的", "默认歌单")
            self._load_playlists()
    
    def _init_local_music(self):
        music_dir = get_music_data_dir()
        local_songs = self._music_service.get_local_songs(music_dir)
        if local_songs:
            self._local_playlist = local_songs
            self._update_local_music_view()
            logger.info(f"[MusicUI] 加载本地音乐: {len(local_songs)} 首")
    
    def _connect_global_player(self):
        self.global_player.set_music_service(self._music_service)
        self.global_player.playback_state_changed.connect(self._on_global_playback_state_changed)
        self.global_player.playback_finished.connect(self._handle_track_finished)
        self.global_player.current_song_changed.connect(self._on_global_song_changed)
        self.global_player.position_changed.connect(self._on_global_position_changed)
        self.global_player.duration_changed.connect(self._on_global_duration_changed)
        self.global_player.play_url_refreshed.connect(self._on_play_url_refreshed)

    def _handle_track_finished(self):
        self._play_next()
    
    def _init_ui(self):
        self._container = QWidget()
        self._container.setObjectName("musicContainer")
        self.setWidget(self._container)
        
        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(20, 20, 20, 20)
        self._content_layout.setSpacing(20)
        
        self._init_content_area()
        
        main_layout.addWidget(self._content_widget)
        
        self._sliding_panel = SlidingPlayerPanel(self._container)
        self._init_home_view()
        self._sliding_panel.set_content(self.home_widget)
        self._sliding_panel.setup_ui()
        self._sliding_panel.expanded.connect(self._on_panel_expanded)
        self._sliding_panel.collapsed.connect(self._on_panel_collapsed)
        
        self._init_bottom_player()
        main_layout.addWidget(self.bottom_player)
        
        self._dockable_playlist = DockablePlaylistWidget(self._container)
        self._dockable_playlist.song_double_clicked.connect(self._on_playqueue_song_double_clicked)
        self._dockable_playlist.song_remove_clicked.connect(self._remove_from_playqueue)
        self._dockable_playlist.song_download_clicked.connect(self._on_download_from_playqueue)
        self._dockable_playlist.clear_all_clicked.connect(self._clear_play_queue)
        self._dockable_playlist.hide()

        self._init_shortcuts()

    def _init_shortcuts(self):
        QShortcut(Qt.CTRL + Qt.Key_Up, self._container, self._toggle_home_view)
        QShortcut(Qt.CTRL + Qt.Key_Down, self._container, self._toggle_home_view)
    def _init_content_area(self):
        from qfluentwidgets import SegmentedWidget
        
        self._nav_container = QWidget(self._content_widget)
        self._nav_container.setObjectName("navContainer")
        nav_layout = QHBoxLayout(self._nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 16)
        nav_layout.setSpacing(0)
        
        self.content_pivot = SegmentedWidget(self._nav_container)
        self.content_pivot.setObjectName("musicSegmentedWidget")
        self.content_pivot.lightIndicatorColor = QColor("#0078d4")

        self.content_stack = QStackedWidget(self._content_widget)
        
        self._init_search_view()
        self._init_local_music_view()
        self._init_playlist_songs_view()
        
        self.content_stack.addWidget(self.search_widget)
        self.content_stack.addWidget(self.local_music_widget)
        self.content_stack.addWidget(self.playlist_songs_widget)
        
        self.content_pivot.addItem(routeKey="search", text="搜索", icon=FIF.SEARCH,
                                   onClick=lambda: self._switch_to_search())
        self.content_pivot.addItem(routeKey="local", text="本地", icon=FIF.FOLDER,
                                   onClick=lambda: self._switch_to_local())
        self.content_pivot.addItem(routeKey="playlist", text="歌单", icon=FIF.ALBUM,
                                   onClick=lambda: self._switch_to_playlist())
        
        self.content_pivot.setCurrentItem("search")
        
        self._is_home_visible = False
        self._previous_widget = self.search_widget
        
        nav_layout.addWidget(self.content_pivot)
        nav_layout.addStretch()
        
        self._content_layout.addWidget(self._nav_container)
        self._content_layout.addWidget(self.content_stack, 1)
        
        self.content_stack.setCurrentWidget(self.search_widget)
        
        QTimer.singleShot(100, self._update_nav_style)
    
    def _toggle_home_view(self):
        if self._sliding_panel.is_expanded():
            self._sliding_panel.collapse()
        else:
            self._sliding_panel.expand()
    
    def _on_panel_expanded(self):
        self._previous_widget = self.content_stack.currentWidget()
        self._is_home_visible = True
        self._apply_theme_to_container()
        self.progress_bar_widget.raise_()
        self.bottom_player.raise_()
        if hasattr(self, 'expand_btn'):
            self.expand_btn.setIcon(FIF.CHEVRON_DOWN_MED)
            self.expand_btn.setToolTip("收起播放面板")
    
    def _on_panel_collapsed(self):
        self._is_home_visible = False
        self._update_nav_style_for_widget(self._previous_widget)
        if hasattr(self, 'expand_btn'):
            self.expand_btn.setIcon(FIF.CARE_UP_SOLID)
            self.expand_btn.setToolTip("展开播放面板")
    
    def _update_nav_style_for_widget(self, widget):
        if widget == self.search_widget:
            self._reset_container_style()
            self.content_pivot.setCurrentItem("search")
        elif widget == self.local_music_widget:
            self._reset_container_style()
            self.content_pivot.setCurrentItem("local")
        elif widget == self.playlist_songs_widget:
            self._reset_container_style()
            self.content_pivot.setCurrentItem("playlist")
        self._update_nav_style()
    
    def _switch_to_search(self):
        self._is_home_visible = False
        self._nav_container.show()
        self.content_stack.setCurrentWidget(self.search_widget)
        self._reset_container_style()
        self._update_nav_style()
    
    def _switch_to_local(self):
        self._is_home_visible = False
        self._nav_container.show()
        self._update_local_music_view()
        self.content_stack.setCurrentWidget(self.local_music_widget)
        self._reset_container_style()
        self._update_nav_style()
    
    def _switch_to_playlist(self):
        self._is_home_visible = False
        self._nav_container.show()
        if self._playlists:
            index = self.playlist_combo.currentIndex()
            if 0 <= index < len(self._playlists):
                playlist = self._playlists[index]
                self._update_playlist_view(playlist)
        self.content_stack.setCurrentWidget(self.playlist_songs_widget)
        self._reset_container_style()
        self._update_nav_style()
    
    def eventFilter(self, obj, event):
        if hasattr(self, 'bottom_player') and obj == self.bottom_player:
            if event.type() == QEvent.MouseButtonPress:
                self._bottom_player_drag_start_y = event.globalY()
                self._bottom_player_is_dragging = True
            elif event.type() == QEvent.MouseMove and self._bottom_player_is_dragging:
                delta = event.globalY() - self._bottom_player_drag_start_y
                if delta < -50:
                    self._sliding_panel.expand()
                    self._bottom_player_is_dragging = False
            elif event.type() == QEvent.MouseButtonRelease:
                self._bottom_player_is_dragging = False
        if obj == self and event.type() == QEvent.Resize:
            if hasattr(self, '_resize_bottom_player'):
                self._resize_bottom_player()
        return super().eventFilter(obj, event)
    
    def _init_home_view(self):
        self.home_widget = QWidget()
        home_layout = QHBoxLayout(self.home_widget)
        home_layout.setContentsMargins(30, 30, 30, 124)
        home_layout.setSpacing(30)
        
        left_widget = QWidget()
        left_widget.setStyleSheet("QWidget { background: transparent; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        vinyl_container = QWidget()
        vinyl_container.setStyleSheet("QWidget { background: transparent; }")
        vinyl_layout = QVBoxLayout(vinyl_container)
        vinyl_layout.setContentsMargins(0, 0, 0, 0)
        vinyl_layout.setSpacing(15)
        
        self._vinyl_record = VinylRecordWidget()
        self._vinyl_record.clicked.connect(self._toggle_play)
        vinyl_layout.addWidget(self._vinyl_record, 0, Qt.AlignCenter)
        
        self._spectrum_widget = SpectrumWidget()
        self._spectrum_widget.setFixedWidth(320)
        vinyl_layout.addWidget(self._spectrum_widget, 0, Qt.AlignCenter)
        
        self._spectrum_analyzer = AudioSpectrumAnalyzer.get_instance(self)
        self._spectrum_analyzer.set_num_bars(32)
        self._spectrum_analyzer.spectrum_data_ready.connect(self._on_spectrum_data_ready)
        
        song_info_widget = QWidget()
        song_info_widget.setStyleSheet("QWidget { background: transparent; }")
        song_info_layout = QVBoxLayout(song_info_widget)
        song_info_layout.setContentsMargins(0, 0, 0, 0)
        song_info_layout.setSpacing(8)
        
        self.home_song_name = QLabel("未播放歌曲")
        self.home_song_name.setAlignment(Qt.AlignCenter)
        self.home_song_name.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
                background: transparent;
                padding: 6px 16px;
            }
        """)
        
        self.home_song_artist = QLabel("")
        self.home_song_artist.setAlignment(Qt.AlignCenter)
        self.home_song_artist.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: rgba(255, 255, 255, 200);
                background: transparent;
                padding: 3px 10px;
            }
        """)
        
        song_info_layout.addWidget(self.home_song_name)
        song_info_layout.addWidget(self.home_song_artist)
        
        vinyl_layout.addWidget(song_info_widget)
        
        left_layout.addWidget(vinyl_container)
        
        home_layout.addWidget(left_widget, 5)
        
        self.lyrics_card = LyricsCardWidget()
        self.lyrics_card.textColorChanged.connect(self._update_lyrics_text_color)
        lyrics_card_layout = QVBoxLayout(self.lyrics_card)
        lyrics_card_layout.setContentsMargins(24, 24, 24, 24)
        
        self.home_lyrics_list = QListWidget()
        self.home_lyrics_list.setObjectName("musicLyricsList")
        self.home_lyrics_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.home_lyrics_list.setSpacing(10)
        self.home_lyrics_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.home_lyrics_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._lyrics_normal_color = "rgba(255, 255, 255, 0.6)"
        self._lyrics_hover_color = "rgba(255, 255, 255, 0.9)"
        self._lyrics_selected_color = "white"
        lyrics_card_layout.addWidget(self.home_lyrics_list)
        
        home_layout.addWidget(self.lyrics_card, 5)
        
        self._lyric_lines: List[LyricLine] = []
        self._current_lyric_index = -1
    
    def _init_search_view(self):
        self.search_widget = QWidget()
        search_layout = QVBoxLayout(self.search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)
        
        search_card = CardWidget()
        search_card_layout = QHBoxLayout(search_card)
        search_card_layout.setContentsMargins(16, 12, 16, 12)
        search_card_layout.setSpacing(12)
        
        self.platform_combo = ComboBox()
        for text in PLATFORM_MAP.keys():
            self.platform_combo.addItem(text)
        self.platform_combo.setCurrentText("全部平台")
        self.platform_combo.setFixedWidth(140)
        
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("搜索歌曲、歌手...")
        self.search_input.setFixedWidth(300)
        self.search_input.returnPressed.connect(self._on_search)
        
        self.search_btn = PrimaryPushButton("搜索")
        self.search_btn.setIcon(FIF.SEARCH)
        self.search_btn.clicked.connect(self._on_search_toggle)
        self._is_searching = False
        
        self.search_count_box = SpinBox()
        self.search_count_box.setRange(5, 100)
        self.search_count_box.setValue(20)
        self.search_count_box.setFixedWidth(120)
        self.search_count_box.setToolTip("搜索结果数量")
        
        search_card_layout.addWidget(self.platform_combo)
        search_card_layout.addWidget(self.search_input)
        search_card_layout.addWidget(self.search_btn)
        search_card_layout.addWidget(QLabel("数量:"))
        search_card_layout.addWidget(self.search_count_box)
        search_card_layout.addStretch()
        
        self.import_playlist_btn = TransparentToolButton(FIF.DOWNLOAD, self)
        self.import_playlist_btn.setFixedSize(28, 28)
        self.import_playlist_btn.setToolTip("导入歌单")
        self.import_playlist_btn.clicked.connect(self._on_import_playlist)
        search_card_layout.addWidget(self.import_playlist_btn)
        
        search_layout.addWidget(search_card)
        
        self.batch_toolbar = QWidget()
        batch_layout = QHBoxLayout(self.batch_toolbar)
        batch_layout.setContentsMargins(16, 8, 16, 8)
        batch_layout.setSpacing(8)
        
        self.select_all_cb = CheckBox()
        self.select_all_cb.setText("全选")
        self.select_all_cb.stateChanged.connect(self._on_select_all_search)
        batch_layout.addWidget(self.select_all_cb)
        
        self.batch_add_queue_btn = PushButton("添加到播放列表")
        self.batch_add_queue_btn.setIcon(FIF.ADD)
        self.batch_add_queue_btn.clicked.connect(self._batch_add_to_playqueue)
        batch_layout.addWidget(self.batch_add_queue_btn)
        
        self.batch_add_playlist_btn = PushButton("添加到歌单")
        self.batch_add_playlist_btn.setIcon(FIF.FOLDER_ADD)
        self.batch_add_playlist_btn.clicked.connect(self._batch_add_to_playlist)
        batch_layout.addWidget(self.batch_add_playlist_btn)
        
        self.batch_download_btn = PushButton("下载选中")
        self.batch_download_btn.setIcon(FIF.DOWNLOAD)
        self.batch_download_btn.clicked.connect(self._batch_download_songs)
        batch_layout.addWidget(self.batch_download_btn)
        
        self.selected_count_label = QLabel("已选 0 首")
        batch_layout.addWidget(self.selected_count_label)
        
        batch_layout.addStretch()
        
        search_layout.addWidget(self.batch_toolbar)
        self.batch_toolbar.setVisible(False)
        
        self.results_list = ListWidget()
        self.results_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.results_list.setSpacing(2)
        self.results_list.itemDoubleClicked.connect(lambda item: self._on_result_double_clicked(self.results_list.row(item)))
        search_layout.addWidget(self.results_list)
    
    def _init_local_music_view(self):
        self.local_music_widget = QWidget()
        local_layout = QVBoxLayout(self.local_music_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(12)
        
        local_header = QHBoxLayout()
        
        local_title = StrongBodyLabel("本地音乐")
        local_header.addWidget(local_title)
        
        local_header.addStretch()
        
        self.local_count = BodyLabel("0 首歌曲")
        local_header.addWidget(self.local_count)
        
        self.refresh_local_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_local_btn.setFixedSize(28, 28)
        self.refresh_local_btn.setToolTip("刷新")
        self.refresh_local_btn.clicked.connect(self._refresh_local_music)
        local_header.addWidget(self.refresh_local_btn)
        
        self.open_music_dir_btn = TransparentToolButton(FIF.FOLDER, self)
        self.open_music_dir_btn.setFixedSize(28, 28)
        self.open_music_dir_btn.setToolTip("打开音乐目录")
        self.open_music_dir_btn.clicked.connect(self._open_music_directory)
        local_header.addWidget(self.open_music_dir_btn)
        
        local_layout.addLayout(local_header)

        self.local_batch_toolbar = QWidget()
        local_batch_layout = QHBoxLayout(self.local_batch_toolbar)
        local_batch_layout.setContentsMargins(16, 8, 16, 8)
        local_batch_layout.setSpacing(8)

        self.local_select_all_cb = CheckBox()
        self.local_select_all_cb.setText("全选")
        self.local_select_all_cb.stateChanged.connect(self._on_select_all_local)
        local_batch_layout.addWidget(self.local_select_all_cb)

        self.local_batch_add_queue_btn = PushButton("添加到播放列表")
        self.local_batch_add_queue_btn.setIcon(FIF.ADD)
        self.local_batch_add_queue_btn.clicked.connect(self._local_batch_add_to_playqueue)
        local_batch_layout.addWidget(self.local_batch_add_queue_btn)

        self.local_batch_add_playlist_btn = PushButton("添加到歌单")
        self.local_batch_add_playlist_btn.setIcon(FIF.FOLDER_ADD)
        self.local_batch_add_playlist_btn.clicked.connect(self._local_batch_add_to_playlist)
        local_batch_layout.addWidget(self.local_batch_add_playlist_btn)

        self.local_selected_count_label = QLabel("已选 0 首")
        local_batch_layout.addWidget(self.local_selected_count_label)

        local_batch_layout.addStretch()

        local_layout.addWidget(self.local_batch_toolbar)
        self.local_batch_toolbar.setVisible(False)
        
        self.local_music_list = ListWidget()
        self.local_music_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.local_music_list.setSpacing(2)
        self.local_music_list.itemDoubleClicked.connect(lambda item: self._on_local_music_double_clicked(self.local_music_list.row(item)))
        local_layout.addWidget(self.local_music_list)
    
    def _init_playlist_songs_view(self):
        self.playlist_songs_widget = QWidget()
        playlist_songs_layout = QVBoxLayout(self.playlist_songs_widget)
        playlist_songs_layout.setContentsMargins(0, 0, 0, 0)
        
        playlist_songs_header = QHBoxLayout()
        
        playlist_songs_header.addWidget(QLabel("歌单:"))
        
        self.playlist_combo = ComboBox()
        self.playlist_combo.setFixedWidth(200)
        self.playlist_combo.currentIndexChanged.connect(self._on_playlist_combo_changed)
        playlist_songs_header.addWidget(self.playlist_combo)
        
        playlist_songs_header.addStretch()
        
        self.playlist_songs_count = BodyLabel("0 首歌曲")
        playlist_songs_header.addWidget(self.playlist_songs_count)
        
        self.new_playlist_btn = TransparentToolButton(FIF.ADD, self)
        self.new_playlist_btn.setFixedSize(28, 28)
        self.new_playlist_btn.setToolTip("新建歌单")
        self.new_playlist_btn.clicked.connect(self._create_playlist)
        playlist_songs_header.addWidget(self.new_playlist_btn)
        
        self.delete_playlist_btn = TransparentToolButton(FIF.DELETE, self)
        self.delete_playlist_btn.setFixedSize(28, 28)
        self.delete_playlist_btn.setToolTip("删除当前歌单")
        self.delete_playlist_btn.clicked.connect(self._delete_current_playlist)
        playlist_songs_header.addWidget(self.delete_playlist_btn)
        
        self.add_playlist_to_queue_btn = TransparentToolButton(FIF.ADD_TO, self)
        self.add_playlist_to_queue_btn.setFixedSize(28, 28)
        self.add_playlist_to_queue_btn.setToolTip("添加歌单到播放列表")
        self.add_playlist_to_queue_btn.clicked.connect(self._add_current_playlist_to_queue)
        playlist_songs_header.addWidget(self.add_playlist_to_queue_btn)
        
        playlist_songs_layout.addLayout(playlist_songs_header)
        
        self.playlist_songs_list = ListWidget()
        self.playlist_songs_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.playlist_songs_list.setSpacing(2)
        self.playlist_songs_list.itemDoubleClicked.connect(lambda item: self._on_playlist_song_double_clicked(self.playlist_songs_list.row(item)))
        playlist_songs_layout.addWidget(self.playlist_songs_list)
    
    def _on_playlist_combo_changed(self, index):
        if index >= 0 and index < len(self._playlists):
            playlist = self._playlists[index]
            self._open_playlist(playlist)
    
    def _add_current_playlist_to_queue(self):
        index = self.playlist_combo.currentIndex()
        if 0 <= index < len(self._playlists):
            playlist = self._playlists[index]
            if playlist.songs:
                for song in playlist.songs:
                    self._add_to_play_queue(song)
                logger.info(f"[Music] 已添加歌单 '{playlist.name}' ({len(playlist.songs)} 首) 到播放列表")
    
    def _init_bottom_player(self):
        self.progress_bar_widget = QWidget(self)
        self.progress_bar_widget.setFixedHeight(PlayerConstants.PROGRESS_BAR_HEIGHT)
        self.progress_bar_widget.setStyleSheet("background: transparent;")
        
        progress_layout = QHBoxLayout(self.progress_bar_widget)
        progress_layout.setContentsMargins(20, 0, 20, 0)
        progress_layout.setSpacing(8)
        
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setObjectName("musicTimeLabel")
        self.current_time_label.setFixedWidth(40)
        
        self.progress_slider = StyledProgressBar(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setObjectName("musicTimeLabel")
        self.total_time_label.setFixedWidth(40)
        
        progress_layout.addWidget(self.current_time_label)
        progress_layout.addWidget(self.progress_slider, 1)
        progress_layout.addWidget(self.total_time_label)
        
        self.bottom_player = CardWidget()
        self.bottom_player.setObjectName("musicBottomPlayer")
        self.bottom_player.setFixedHeight(PlayerConstants.BOTTOM_PLAYER_HEIGHT)
        
        self.bottom_player.setStyleSheet("""
            #musicBottomPlayer {
                background: transparent;
                border: none;
            }
        """)
        
        player_layout = QHBoxLayout(self.bottom_player)
        player_layout.setContentsMargins(20, 10, 20, 10)
        player_layout.setSpacing(20)
        
        self.cover_label = ClickableLabel()
        self.cover_label.setObjectName("musicCoverLabel")
        self.cover_label.setFixedSize(50, 50)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setText("🎵")
        self.cover_label.clicked.connect(self._toggle_home_view)
        
        song_info_container = QWidget()
        song_info_container.setCursor(Qt.PointingHandCursor)
        song_info_layout = QHBoxLayout(song_info_container)
        song_info_layout.setContentsMargins(0, 0, 0, 0)
        song_info_layout.setSpacing(8)
        
        song_text_layout = QVBoxLayout()
        song_text_layout.setSpacing(2)
        
        self.now_playing_label = QLabel("未选择歌曲")
        self.now_playing_label.setObjectName("musicSongNameLabel")
        
        self.now_artist_label = QLabel("")
        self.now_artist_label.setObjectName("musicArtistLabel")
        
        song_text_layout.addWidget(self.now_playing_label)
        song_text_layout.addWidget(self.now_artist_label)
        
        song_info_layout.addLayout(song_text_layout, 1)
        
        song_info_container.mousePressEvent = lambda e: self._toggle_home_view() if e.button() == Qt.LeftButton else None
        
        player_layout.addWidget(self.cover_label, 0, Qt.AlignLeft)
        player_layout.addWidget(song_info_container, 2)

        self._mini_spectrum = MiniSpectrumWidget()
        self._mini_spectrum.setFixedSize(80, 20)
        player_layout.addWidget(self._mini_spectrum, 0, Qt.AlignVCenter)

        self._bottom_player_drag_start_y = 0
        self._bottom_player_is_dragging = False
        self.bottom_player.installEventFilter(self)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        
        self.prev_btn = TransparentToolButton(FIF.CARE_LEFT_SOLID, self)
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setToolTip("上一首")
        self.prev_btn.clicked.connect(self._play_previous)
        
        self.play_btn = TransparentToolButton(FIF.PLAY, self)
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setIconSize(QSize(24, 24))
        self.play_btn.setToolTip("播放")
        self.play_btn.clicked.connect(self._toggle_play)
        
        self.next_btn = TransparentToolButton(FIF.CARE_RIGHT_SOLID, self)
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setToolTip("下一首")
        self.next_btn.clicked.connect(self._play_next)
        
        self.mode_btn = TransparentToolButton(FIF.SYNC, self)
        self.mode_btn.setFixedSize(28, 28)
        self.mode_btn.setToolTip("播放模式")
        self.mode_btn.clicked.connect(self._toggle_play_mode)
        
        self.mode_label = QLabel("列表循环")
        self.mode_label.setObjectName("musicModeLabel")
        
        controls_layout.addWidget(self.mode_btn)
        controls_layout.addWidget(self.mode_label)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.next_btn)

        self.expand_btn = TransparentToolButton(FIF.CARE_UP_SOLID, self)
        self.expand_btn.setFixedSize(28, 28)
        self.expand_btn.setToolTip("展开播放面板")
        self.expand_btn.clicked.connect(self._toggle_home_view)

        controls_layout.addWidget(self.expand_btn)

        player_layout.addLayout(controls_layout)
        
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)
        
        self.playlist_toggle_btn = TransparentToolButton(FIF.MENU, self)
        self.playlist_toggle_btn.setFixedSize(28, 28)
        self.playlist_toggle_btn.setToolTip("播放列表")
        self.playlist_toggle_btn.clicked.connect(self._toggle_playlist_dock)
        
        self.volume_icon = TransparentToolButton(FIF.VOLUME, self)
        self.volume_icon.setFixedSize(28, 28)
        self.volume_icon.setToolTip("音量")
        
        self.volume_slider = StyledVolumeSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        
        self.volume_label = QLabel("100%")
        self.volume_label.setObjectName("musicVolumeLabel")
        self.volume_label.setFixedWidth(35)
        
        volume_layout.addWidget(self.playlist_toggle_btn)
        volume_layout.addWidget(self.volume_icon)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        
        player_layout.addLayout(volume_layout)
        
        self._resize_bottom_player()
        self.installEventFilter(self)
    
    def _resize_bottom_player(self):
        self.progress_bar_widget.setFixedWidth(self.width())
        self.progress_bar_widget.move(0, self.height() - PlayerConstants.BOTTOM_PLAYER_HEIGHT - PlayerConstants.PROGRESS_BAR_HEIGHT)
        self.bottom_player.setFixedWidth(self.width())
        self.bottom_player.move(0, self.height() - PlayerConstants.BOTTOM_PLAYER_HEIGHT)
        if hasattr(self, '_sliding_panel') and self._sliding_panel:
            self._sliding_panel.setGeometry(0, 0, self.width(), self.height())
    
    def _connect_signals(self):
        self._music_service.search_completed.connect(self._on_search_completed)
        self._music_service.search_failed.connect(self._on_search_failed)
        self._music_service.search_progress.connect(self._on_search_progress)
        self._music_service.play_url_obtained.connect(self._on_play_url_obtained)
        self._music_service.play_url_failed.connect(self._on_play_url_failed)
        self._music_service.playlists_loaded.connect(self._on_playlists_loaded)
        self._music_service.lyric_completed.connect(self._on_lyric_completed)
        self._music_service.download_completed.connect(self._on_download_completed)
        self._music_service.download_failed.connect(self._on_download_failed)
        self._music_service.download_progress.connect(self._on_download_progress)
        self._music_service.all_downloads_completed.connect(self._on_all_downloads_completed)
    
    def _on_lyric_completed(self, song_id: str, lyric: str):
        logger.info(f"[Lyric] 歌词获取成功：{song_id[:20]}... 长度：{len(lyric)}")
        current_song = self.global_player.get_current_song()
        if current_song and current_song.song_id == song_id:
            current_song.lyric = lyric
            self._update_lyric(current_song)
            logger.info(f"[Lyric] 歌词已更新到界面")
    
    def _load_playlists(self):
        self._playlists = self._music_service.get_playlists()
        self._update_playlist_combo()
        
        if self._playlists:
            self._open_playlist(self._playlists[0])
    
    def _update_playlist_combo(self):
        self.playlist_combo.blockSignals(True)
        self.playlist_combo.clear()
        for playlist in self._playlists:
            self.playlist_combo.addItem(playlist.name, playlist.id)
        self.playlist_combo.blockSignals(False)
    
    def _delete_current_playlist(self):
        current_index = self.playlist_combo.currentIndex()
        if current_index >= 0 and current_index < len(self._playlists):
            playlist = self._playlists[current_index]
            self._remove_playlist(playlist)
    
    def _remove_playlist(self, playlist: Playlist):
        reply = QMessageBox.question(self, "删除歌单", f"确定要删除歌单 '{playlist.name}' 吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._music_service.delete_playlist(playlist.id)
            self._load_playlists()
    
    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "新建歌单", "请输入歌单名称:")
        if ok and name.strip():
            description, _ = QInputDialog.getText(self, "新建歌单", "请输入歌单描述(可选):")
            self._music_service.create_playlist(name.strip(), description or "")
            self._load_playlists()
    
    def _open_playlist(self, playlist: Playlist):
        for i, p in enumerate(self._playlists):
            if p.id == playlist.id:
                self.playlist_combo.blockSignals(True)
                self.playlist_combo.setCurrentIndex(i)
                self.playlist_combo.blockSignals(False)
                break
        
        self._update_playlist_view(playlist)
    
    def _update_playlist_view(self, playlist: Playlist):
        self._playlist_songs = playlist.songs
        self.playlist_songs_list.clear()
        self.playlist_songs_count.setText(f"{len(playlist.songs)} 首歌曲")
        
        for i, song in enumerate(playlist.songs):
            item = QListWidgetItem()
            widget = SongListItemWidget(song, i, i == self._current_index, show_remove=True)
            widget.double_clicked.connect(self._on_playlist_song_double_clicked)
            widget.add_to_playqueue_clicked.connect(self._on_add_to_playqueue_from_playlist)
            widget.remove_from_playlist_clicked.connect(lambda idx: self._remove_from_playlist(idx, playlist))
            widget.download_clicked.connect(self._on_download_from_playlist)
            widget.update_theme(isDarkTheme())
            item.setSizeHint(widget.sizeHint())
            self.playlist_songs_list.addItem(item)
            self.playlist_songs_list.setItemWidget(item, widget)
    
    def _remove_from_playlist(self, index: int, playlist: Playlist):
        if 0 <= index < len(playlist.songs):
            song = playlist.songs[index]
            self._music_service.remove_from_playlist(playlist.id, song.song_id)
            self._open_playlist(playlist)
    
    def _update_playqueue_view(self):
        self._update_dockable_playlist()
    
    def _on_playqueue_song_double_clicked(self, index: int):
        if 0 <= index < len(self._play_queue):
            self._current_index = index
            self._play_song_from_queue(index)
    
    def _play_song_from_queue(self, index: int):
        if index < 0 or index >= len(self._play_queue):
            return
        
        song = self._play_queue[index]
        self._current_index = index
        self._retry_count = 0
        
        self._update_now_playing(song)
        
        logger.info(f"[Music] 播放歌曲：{song.name}, 歌词：{'有' if song.lyric else '无'}")
        if not song.lyric:
            logger.info(f"[Music] 开始获取歌词...")
            self._music_service.get_lyric(song)
        
        if song.play_url:
            self.global_player.play(song, self._play_queue, index)
            self.play_btn.setIcon(FIF.PAUSE)
            self.play_btn.setToolTip("暂停")
            if self._vinyl_record:
                self._vinyl_record.set_playing(True)
        else:
            self._music_service.get_play_url(song)
        
        self._update_playqueue_view()
    
    def _add_to_play_queue(self, song: SongInfo, play_next: bool = False):
        if not any(s.song_id == song.song_id for s in self._play_queue):
            if play_next and self._current_index >= 0:
                self._play_queue.insert(self._current_index + 1, song)
            else:
                self._play_queue.append(song)
            self._update_playqueue_view()
            self.playqueue_changed.emit()
            logger.info(f"[Music] 添加到播放列表: {song.name}")
    
    def _play_song_or_add_to_queue(self, song: SongInfo):
        for i, s in enumerate(self._play_queue):
            if s.song_id == song.song_id:
                self._current_index = i
                self._play_song_from_queue(i)
                return
        self._play_queue.append(song)
        self._current_index = len(self._play_queue) - 1
        self._update_playqueue_view()
        self.playqueue_changed.emit()
        self._play_song_from_queue(self._current_index)
        logger.info(f"[Music] 添加到播放列表: {song.name}")
    
    def _clear_play_queue(self):
        self._play_queue.clear()
        self._current_index = -1
        self._update_playqueue_view()
        self.playqueue_changed.emit()
    
    def _remove_from_playqueue(self, index: int):
        if 0 <= index < len(self._play_queue):
            del self._play_queue[index]
            if self._current_index >= len(self._play_queue):
                self._current_index = len(self._play_queue) - 1
            elif self._current_index >= index and self._current_index > 0:
                self._current_index -= 1
            self._update_playqueue_view()
            self.playqueue_changed.emit()
    
    def _on_add_to_playqueue_from_playlist(self, index: int):
        if 0 <= index < len(self._playlist_songs):
            self._add_to_play_queue(self._playlist_songs[index])
    
    def _on_add_to_playqueue_from_search(self, index: int):
        if 0 <= index < len(self._search_results):
            self._add_to_play_queue(self._search_results[index])
    
    def _on_add_to_playqueue_from_local(self, index: int):
        if 0 <= index < len(self._local_playlist):
            self._add_to_play_queue(self._local_playlist[index])
    
    def _on_download_from_playlist(self, index: int):
        if 0 <= index < len(self._playlist_songs):
            song = self._playlist_songs[index]
            if song.source != "local":
                self._music_service.download_song(song)
                logger.info(f"[Music] 开始下载: {song.name}")
    
    def _on_download_from_playqueue(self, index: int):
        if 0 <= index < len(self._play_queue):
            song = self._play_queue[index]
            if song.source != "local":
                self._music_service.download_song(song)
                logger.info(f"[Music] 开始下载: {song.name}")
    
    def _refresh_local_music(self):
        self._load_local_music()
        logger.info("[Music] 本地音乐已刷新")
    
    def _open_music_directory(self):
        music_dir = get_music_data_dir()
        if os.path.exists(music_dir):
            import subprocess
            import platform
            if platform.system() == 'Windows':
                os.startfile(music_dir)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', music_dir])
            else:
                subprocess.run(['xdg-open', music_dir])
            logger.info(f"[Music] 已打开音乐目录: {music_dir}")
    
    def _load_local_music(self):
        self._local_playlist = self._music_service.get_local_songs()
        self._update_local_music_view()
        self.content_pivot.setCurrentItem("local")
        self.content_stack.setCurrentWidget(self.local_music_widget)
    
    def _on_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return
        
        platforms_str = PLATFORM_MAP.get(self.platform_combo.text(), "")
        if platforms_str:
            platforms = [p.strip() for p in platforms_str.split(",")]
        else:
            platforms = None
        count = self.search_count_box.value()
        
        self._music_service.search(keyword, platforms, count)
    
    def _on_search_toggle(self):
        if self._is_searching:
            self._music_service.cancel_search()
            self._is_searching = False
            self.search_btn.setEnabled(True)
            self.search_btn.setText("搜索")
            self.search_btn.setIcon(FIF.SEARCH)
            self.search_input.setEnabled(True)
            self.platform_combo.setEnabled(True)
            self.search_count_box.setEnabled(True)
        else:
            self._on_search()
    
    def _on_search_completed(self, results: list):
        self._is_searching = False
        self.search_btn.setEnabled(True)
        self.search_btn.setText("搜索")
        self.search_btn.setIcon(FIF.SEARCH)
        self.search_input.setEnabled(True)
        self.platform_combo.setEnabled(True)
        self.search_count_box.setEnabled(True)
        
        self._search_results = results
        self._update_search_results_view(results)
    
    def _on_search_failed(self, error_msg: str):
        self._is_searching = False
        self.search_btn.setEnabled(True)
        self.search_btn.setText("搜索")
        self.search_btn.setIcon(FIF.SEARCH)
        self.search_input.setEnabled(True)
        self.platform_combo.setEnabled(True)
        self.search_count_box.setEnabled(True)
        QMessageBox.warning(self, "搜索失败", error_msg)
    
    def _on_search_progress(self, message: str):
        self.search_btn.setText(message)
    
    def _on_import_playlist(self):
        url, ok = QInputDialog.getText(self, "导入歌单", "请输入歌单分享链接:\n支持奈缇斯、咕嘎、酷汪、酷me、咪咕等平台的歌单链接")
        if ok and url.strip():
            self._import_playlist_url(url.strip())
    
    def _import_playlist_url(self, url: str):
        from PyQt5.QtWidgets import QProgressDialog
        
        self.progress_dialog = QProgressDialog("正在解析歌单，请稍候...\n这可能需要一些时间，请耐心等待", "取消", 0, 0, self)
        self.progress_dialog.setWindowTitle("导入歌单")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setRange(0, 0)
        self.progress_dialog.canceled.connect(self._on_import_cancelled)
        self.progress_dialog.show()
        
        self.import_playlist_btn.setEnabled(False)
        
        import threading
        def parse_thread():
            try:
                from musicdl import musicdl
                self.playlist_import_progress.emit("正在连接音乐平台...", 0)
                
                music_client = musicdl.MusicClient()
                
                self.playlist_import_progress.emit("正在解析歌单信息...", 0)
                
                song_infos = music_client.parseplaylist(url)
                
                if song_infos:
                    self.playlist_import_progress.emit(f"正在处理 {len(song_infos)} 首歌曲...", 0)
                    
                    songs = []
                    for idx, song_info in enumerate(song_infos):
                        try:
                            song = SongInfo(
                                song_id=str(song_info.get('identifier', '')),
                                name=song_info.get('song_name', '未知'),
                                singer=song_info.get('singers', '未知'),
                                album=song_info.get('album', ''),
                                duration=song_info.get('duration', ''),
                                img_url=song_info.get('cover_url', ''),
                                source=song_info.get('source', ''),
                                play_url=song_info.get('download_url', ''),
                                lyric=song_info.get('lyric', '')
                            )
                            songs.append(song)
                        except Exception as e:
                            logger.warning(f"Failed to parse song: {e}")
                    
                    self.playlist_imported.emit(songs)
                else:
                    self.playlist_import_failed.emit("无法解析该歌单链接")
            except Exception as e:
                self.playlist_import_failed.emit(f"解析失败：{str(e)}")
        
        thread = threading.Thread(target=parse_thread)
        thread.daemon = True
        thread.start()
    
    def _update_import_progress(self, message: str, value: int):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            self.progress_dialog.setValue(value)
    
    def _on_import_cancelled(self):
        self.import_playlist_btn.setEnabled(True)
        self.search_btn.setText("搜索")
    
    def _on_playlist_imported(self, songs: list):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        self.import_playlist_btn.setEnabled(True)
        self.search_btn.setText("搜索")
        
        if songs:
            self._search_results = songs
            self._update_search_results_view(songs)
            self.content_pivot.setCurrentItem("search")
            self.content_stack.setCurrentWidget(self.search_widget)
            QMessageBox.information(self, "导入成功", f"成功导入 {len(songs)} 首歌曲")
        else:
            QMessageBox.warning(self, "导入失败", "未能解析到任何歌曲")
    
    def _on_playlist_import_failed(self, error_msg: str):
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        self.import_playlist_btn.setEnabled(True)
        self.search_btn.setText("搜索")
        QMessageBox.warning(self, "导入失败", error_msg)
    
    def _update_search_results_view(self, songs: list):
        self.results_list.clear()
        self._selected_indices["search"].clear()
        
        for i, song in enumerate(songs):
            item = QListWidgetItem()
            widget = SongListItemWidget(song, i, i == self._current_index, show_checkbox=True)
            widget.double_clicked.connect(self._on_result_double_clicked)
            widget.add_to_playlist_clicked.connect(self._on_add_to_playlist_from_search)
            widget.add_to_playqueue_clicked.connect(self._on_add_to_playqueue_from_search)
            widget.selection_changed.connect(self._on_search_selection_changed)
            widget.download_clicked.connect(self._on_download_from_search)
            widget.update_theme(isDarkTheme())
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
        
        self.batch_toolbar.setVisible(len(songs) > 0)
        self._update_selected_count("search")
    
    def _on_search_selection_changed(self, index: int, selected: bool):
        if selected:
            self._selected_indices["search"].add(index)
        else:
            self._selected_indices["search"].discard(index)
        self._update_selected_count("search")
    
    def _on_select_all_search(self, state):
        checked = state == Qt.Checked
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            widget = self.results_list.itemWidget(item)
            if widget:
                widget.set_selected(checked)
        
        if checked:
            self._selected_indices["search"] = set(range(self.results_list.count()))
        else:
            self._selected_indices["search"].clear()
        self._update_selected_count("search")
    
    def _update_selected_count(self, list_type: str):
        count = len(self._selected_indices.get(list_type, set()))
        self.selected_count_label.setText(f"已选 {count} 首")
    
    def _batch_add_to_playqueue(self):
        selected = self._selected_indices.get("search", set()).copy()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择歌曲")
            return
        
        count = len(selected)
        for index in sorted(selected):
            if 0 <= index < len(self._search_results):
                self._add_to_play_queue(self._search_results[index])
        
        self._clear_selection("search")
        QMessageBox.information(self, "成功", f"已添加 {count} 首歌曲到播放列表")
    
    def _batch_add_to_playlist(self):
        selected = self._selected_indices.get("search", set()).copy()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择歌曲")
            return
        
        if not self._playlists:
            QMessageBox.information(self, "提示", "请先创建歌单")
            return
        
        playlist_names = [p.name for p in self._playlists]
        selected_playlist, ok = QInputDialog.getItem(self, "添加到歌单", "选择歌单:", playlist_names, 0, False)
        if ok and selected_playlist:
            playlist = next((p for p in self._playlists if p.name == selected_playlist), None)
            if playlist:
                count = 0
                for index in sorted(selected):
                    if 0 <= index < len(self._search_results):
                        self._music_service.add_to_playlist(playlist.id, self._search_results[index])
                        count += 1
                self._load_playlists()
                self._clear_selection("search")
                QMessageBox.information(self, "成功", f"已添加 {count} 首歌曲到歌单 '{playlist.name}'")
    
    def _clear_selection(self, list_type: str):
        self._selected_indices[list_type].clear()
        self.select_all_cb.setChecked(False)
        self._update_selected_count(list_type)
    
    def _update_local_music_view(self):
        self.local_music_list.clear()
        self._selected_indices["local"].clear()
        self.local_count.setText(f"{len(self._local_playlist)} 首歌曲")

        for i, song in enumerate(self._local_playlist):
            item = QListWidgetItem()
            widget = SongListItemWidget(song, i, i == self._current_index, show_download=False, show_checkbox=True)
            widget.double_clicked.connect(self._on_local_music_double_clicked)
            widget.add_to_playlist_clicked.connect(self._on_add_to_playlist_from_local)
            widget.add_to_playqueue_clicked.connect(self._on_add_to_playqueue_from_local)
            widget.selection_changed.connect(self._on_local_selection_changed)
            widget.update_theme(isDarkTheme())
            item.setSizeHint(widget.sizeHint())
            self.local_music_list.addItem(item)
            self.local_music_list.setItemWidget(item, widget)

        self.local_batch_toolbar.setVisible(len(self._local_playlist) > 0)
        self._update_local_selected_count()
    
    def _on_local_music_double_clicked(self, index: int):
        if 0 <= index < len(self._local_playlist):
            song = self._local_playlist[index]
            self._add_to_play_queue(song)
            self._current_index = len(self._play_queue) - 1
            self._play_song_from_queue(self._current_index)
    
    def _on_add_to_playlist_from_search(self, index: int):
        if 0 <= index < len(self._search_results):
            self._show_add_to_playlist_dialog(self._search_results[index])
    
    def _on_add_to_playlist_from_local(self, index: int):
        if 0 <= index < len(self._local_playlist):
            self._show_add_to_playlist_dialog(self._local_playlist[index])

    def _on_local_selection_changed(self, index: int, selected: bool):
        if selected:
            self._selected_indices["local"].add(index)
        else:
            self._selected_indices["local"].discard(index)
        self._update_local_selected_count()

    def _on_select_all_local(self, state):
        checked = state == Qt.Checked
        for i in range(self.local_music_list.count()):
            item = self.local_music_list.item(i)
            widget = self.local_music_list.itemWidget(item)
            if widget:
                widget.set_selected(checked)

        if checked:
            self._selected_indices["local"] = set(range(self.local_music_list.count()))
        else:
            self._selected_indices["local"].clear()
        self._update_local_selected_count()

    def _update_local_selected_count(self):
        count = len(self._selected_indices.get("local", set()))
        self.local_selected_count_label.setText(f"已选 {count} 首")

    def _local_clear_selection(self):
        self._selected_indices["local"].clear()
        self.local_select_all_cb.setChecked(False)
        self._update_local_selected_count()

    def _local_batch_add_to_playqueue(self):
        selected = self._selected_indices.get("local", set()).copy()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择歌曲")
            return

        count = len(selected)
        for index in sorted(selected):
            if 0 <= index < len(self._local_playlist):
                self._add_to_play_queue(self._local_playlist[index])

        self._local_clear_selection()
        QMessageBox.information(self, "成功", f"已添加 {count} 首歌曲到播放列表")

    def _local_batch_add_to_playlist(self):
        selected = self._selected_indices.get("local", set()).copy()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择歌曲")
            return

        if not self._playlists:
            QMessageBox.information(self, "提示", "请先创建歌单")
            return

        playlist_names = [p.name for p in self._playlists]
        selected_playlist, ok = QInputDialog.getItem(self, "添加到歌单", "选择歌单:", playlist_names, 0, False)
        if ok and selected_playlist:
            playlist = next((p for p in self._playlists if p.name == selected_playlist), None)
            if playlist:
                count = 0
                for index in sorted(selected):
                    if 0 <= index < len(self._local_playlist):
                        self._music_service.add_to_playlist(playlist.id, self._local_playlist[index])
                        count += 1
                self._load_playlists()
                self._local_clear_selection()
                QMessageBox.information(self, "成功", f"已添加 {count} 首歌曲到歌单 '{playlist.name}'")
    
    def _on_add_to_playlist_from_playlist(self, index: int):
        if 0 <= index < len(self._playlist_songs):
            self._show_add_to_playlist_dialog(self._playlist_songs[index])
    
    def _show_add_to_playlist_dialog(self, song: SongInfo):
        if not self._playlists:
            QMessageBox.information(self, "提示", "请先创建歌单")
            return
        
        playlist_names = [p.name for p in self._playlists]
        selected, ok = QInputDialog.getItem(self, "添加到歌单", "选择歌单:", playlist_names, 0, False)
        if ok and selected:
            playlist = next((p for p in self._playlists if p.name == selected), None)
            if playlist:
                self._music_service.add_to_playlist(playlist.id, song)
                self._load_playlists()
                QMessageBox.information(self, "成功", f"已添加到歌单 '{playlist.name}'")
    
    def _on_playlist_double_clicked(self, index: int):
        if 0 <= index < len(self._playlist_songs):
            song = self._playlist_songs[index]
            self._play_song_or_add_to_queue(song)
    
    def _on_result_double_clicked(self, index: int):
        if 0 <= index < len(self._search_results):
            song = self._search_results[index]
            self._play_song_or_add_to_queue(song)
    
    def _on_playlist_song_double_clicked(self, index: int):
        if 0 <= index < len(self._playlist_songs):
            song = self._playlist_songs[index]
            self._play_song_or_add_to_queue(song)
    
    def _on_global_playback_state_changed(self, is_playing: bool):
        logger.info(f"[MusicUI] _on_global_playback_state_changed: is_playing={is_playing}")
        if is_playing:
            self.play_btn.setIcon(FIF.PAUSE)
            self.play_btn.setToolTip("暂停")
            if self._vinyl_record:
                self._vinyl_record.set_playing(True)
            if hasattr(self, '_spectrum_widget'):
                self._spectrum_widget.set_playing(True)
            if hasattr(self, '_mini_spectrum'):
                self._mini_spectrum.set_playing(True)
            if hasattr(self, '_spectrum_analyzer'):
                self._spectrum_analyzer.start()
        else:
            self.play_btn.setIcon(FIF.PLAY)
            self.play_btn.setToolTip("播放")
            if self._vinyl_record:
                self._vinyl_record.set_playing(False)
            if hasattr(self, '_spectrum_widget'):
                self._spectrum_widget.set_playing(False)
            if hasattr(self, '_mini_spectrum'):
                self._mini_spectrum.set_playing(False)
            if hasattr(self, '_spectrum_analyzer'):
                self._spectrum_analyzer.stop()
    
    def _on_spectrum_data_ready(self, data: list):
        if hasattr(self, '_spectrum_widget'):
            self._spectrum_widget.set_spectrum_data(data)
        if hasattr(self, '_mini_spectrum'):
            self._mini_spectrum.set_spectrum_data(data)
    
    def _on_global_song_changed(self, song: SongInfo):
        self._update_now_playing(song)
    
    def _on_global_position_changed(self, position: int):
        if not self._is_user_seeking:
            self.progress_slider.setValue(position)
            self.current_time_label.setText(self._format_time(position))
            self._update_lyric_highlight(position)
    
    def _on_global_duration_changed(self, duration: int):
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(self._format_time(duration))
    
    def _on_play_url_refreshed(self, song: SongInfo, url: str):
        if self._current_index >= 0 and self._play_queue:
            current_song = self._play_queue[self._current_index]
            if current_song.song_id == song.song_id:
                current_song.play_url = url
    
    def _on_play_url_obtained(self, song_id: str, url: str):
        if self._current_index >= 0 and self._play_queue:
            current_song = self._play_queue[self._current_index]
            if current_song.song_id == song_id:
                current_song.play_url = url
                self.global_player.play(current_song, self._play_queue, self._current_index)
    
    def _on_play_url_failed(self, song_id: str):
        if self._current_index >= 0 and self._play_queue:
            current_song = self._play_queue[self._current_index]
            if current_song.song_id == song_id:
                self.now_playing_label.setText("获取播放链接失败")
    
    def _update_now_playing(self, song: SongInfo):
        name = song.name
        if len(name) > 30:
            name = name[:30] + "..."
        self.now_playing_label.setText(name)
        
        singer = song.singer
        if song.album:
            singer += f" - {song.album}"
        self.now_artist_label.setText(singer)
        
        self._update_cover(song.img_url)
        self._update_lyric(song)
    
    def _update_cover(self, img_url: str):
        if not img_url:
            self.cover_label.setText("🎵")
            return
        
        self.cover_label.setText("⏳")
        
        def on_cover_loaded(pixmap: QPixmap):
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cover_label.setPixmap(scaled_pixmap)
            else:
                self.cover_label.setText("🎵")
        
        def on_error():
            self.cover_label.setText("🎵")
        
        self._network_manager.fetch_image(img_url, on_cover_loaded, on_error)
    
    def _update_lyric(self, song: SongInfo):
        if song.lyric:
            self._lyric_lines = LyricParser.parse(song.lyric)
            self._display_lyrics()
            self._update_lyric_info(song)
        else:
            self._lyric_lines = []
            self.home_lyrics_list.clear()
            self.home_lyrics_list.addItem("暂无歌词")
            self._update_lyric_info(song)
    
    def _update_lyric_info(self, song: SongInfo):
        self.home_song_name.setText(song.name if song.name else "未知歌曲")
        artist = song.singer if song.singer else ""
        if song.album:
            artist += f" - {song.album}" if artist else song.album
        self.home_song_artist.setText(artist)
        
        if song.img_url:
            self._load_lyric_cover(song.img_url)
        else:
            self._reset_lyrics_card_style()
    
    def _reset_lyrics_card_style(self):
        self._original_cover_pixmap = None
        self._dominant_color = None
        self.lyrics_card.set_dominant_color(None)
        if self._vinyl_record:
            self._vinyl_record.set_cover(QPixmap())
        self._update_lyrics_text_color(
            "rgba(255, 255, 255, 0.6)",
            "rgba(255, 255, 255, 0.9)",
            "white"
        )
        self._apply_theme_color_to_window(None)
    
    def _load_lyric_cover(self, img_url: str):
        if not img_url:
            return
        
        def on_cover_loaded(pixmap: QPixmap):
            if not pixmap.isNull():
                self._set_lyrics_card_background(pixmap)
        
        self._network_manager.fetch_image(img_url, on_cover_loaded)
    
    def _set_lyrics_card_background(self, pixmap: QPixmap):
        if pixmap.isNull():
            self._original_cover_pixmap = None
            self._dominant_color = None
            self.lyrics_card.set_dominant_color(None)
            if self._vinyl_record:
                self._vinyl_record.set_cover(QPixmap())
            self._apply_theme_color_to_window(None)
            return
        
        self._original_cover_pixmap = pixmap
        self.lyrics_card.set_background_from_pixmap(pixmap)
        
        if self._vinyl_record:
            self._vinyl_record.set_cover(pixmap)
        
        self._apply_theme_color_to_window(pixmap)
    
    def _apply_theme_color_to_window(self, pixmap: QPixmap):
        if pixmap.isNull():
            self._dominant_color = None
            self._sliding_panel.set_background_style("""
                QWidget {
                    background: qradialgradient(
                        cx: 0.5, cy: 0.5, radius: 0.8,
                        fx: 0.5, fy: 0.5,
                        stop: 0 rgb(60, 60, 80),
                        stop: 1 rgb(30, 30, 50)
                    );
                }
            """)
            return
        
        dominant_color = self.lyrics_card._extract_dominant_color(pixmap)
        self._dominant_color = dominant_color
        
        h = dominant_color.hue()
        s = dominant_color.saturation()
        v = dominant_color.value()
        
        is_dark = isDarkTheme()
        
        if is_dark:
            center_color = QColor.fromHsv(h, min(s + 10, 255), max(v - 30, 20))
            edge_color = QColor.fromHsv(h, min(s + 10, 255), max(v - 80, 10))
        else:
            center_color = QColor.fromHsv(h, min(s + 30, 255), max(v - 10, 40))
            edge_color = QColor.fromHsv(h, min(s + 30, 255), max(v - 60, 20))
        
        center_css = f"rgb({center_color.red()}, {center_color.green()}, {center_color.blue()})"
        edge_css = f"rgb({edge_color.red()}, {edge_color.green()}, {edge_color.blue()})"
        
        self._sliding_panel.set_background_style(f"""
            QWidget {{
                background: qradialgradient(
                    cx: 0.5, cy: 0.5, radius: 0.8,
                    fx: 0.5, fy: 0.5,
                    stop: 0 {center_css},
                    stop: 1 {edge_css}
                );
            }}
        """)
    
    def _display_lyrics(self):
        self.home_lyrics_list.clear()
        
        for line in self._lyric_lines:
            item = QListWidgetItem(line.text)
            item.setTextAlignment(Qt.AlignCenter)
            font = QFont()
            font.setPointSize(12)
            item.setFont(font)
            item.setSizeHint(QSize(0, 50))
            self.home_lyrics_list.addItem(item)
    
    def _update_lyric_highlight(self, current_time_ms: int):
        if not self._lyric_lines:
            return
        
        current_index = LyricParser.find_current_line(self._lyric_lines, current_time_ms)
        
        if current_index == self._current_lyric_index:
            return
        
        self._current_lyric_index = current_index
        
        for i in range(self.home_lyrics_list.count()):
            item = self.home_lyrics_list.item(i)
            if item:
                item.setSelected(i == current_index)
                font = QFont()
                if i == current_index:
                    font.setPointSize(16)
                    font.setBold(True)
                else:
                    font.setPointSize(12)
                    font.setBold(False)
                item.setFont(font)
        
        if current_index >= 0 and current_index < self.home_lyrics_list.count():
            self.home_lyrics_list.scrollToItem(
                self.home_lyrics_list.item(current_index),
                QAbstractItemView.PositionAtCenter
            )
    
    def _toggle_play(self):
        self.global_player.toggle_play()
    
    def _play_previous(self):
        if not self._play_queue:
            return
        
        if self._play_mode == PlayMode.SHUFFLE:
            self._current_index = self._get_random_index()
        else:
            self._current_index = (self._current_index - 1) % len(self._play_queue)
        
        self._play_song_from_queue(self._current_index)
    
    def _play_next(self):
        if not self._play_queue:
            return
        
        if self._play_mode == PlayMode.SINGLE_LOOP:
            self.global_player.play(self._play_queue[self._current_index], self._play_queue, self._current_index)
        elif self._play_mode == PlayMode.SHUFFLE:
            self._current_index = self._get_random_index()
            self._play_song_from_queue(self._current_index)
        else:
            self._current_index = (self._current_index + 1) % len(self._play_queue)
            self._play_song_from_queue(self._current_index)
    
    def _get_random_index(self) -> int:
        total = len(self._play_queue)
        
        if len(self._played_indices) >= total:
            self._played_indices.clear()
        
        available = [i for i in range(total) if i != self._current_index and i not in self._played_indices]
        
        if not available:
            return self._current_index
        
        next_idx = random.choice(available)
        self._played_indices.add(next_idx)
        return next_idx
    
    def _toggle_play_mode(self):
        modes = list(PlayMode)
        current_idx = modes.index(self._play_mode)
        next_mode = modes[(current_idx + 1) % len(modes)]
        self._play_mode = next_mode
        
        if next_mode == PlayMode.SHUFFLE:
            self._played_indices.clear()
        
        self._update_mode_button()
    
    def _update_mode_button(self):
        icon_name, tooltip = PLAY_MODE_CONFIG[self._play_mode]
        icon = getattr(FIF, icon_name.upper(), FIF.SYNC)
        self.mode_btn.setIcon(icon)
        self.mode_btn.setToolTip(tooltip)
        self.mode_label.setText(tooltip)
    
    def _on_slider_pressed(self):
        self._is_user_seeking = True
    
    def _on_slider_released(self):
        self._is_user_seeking = False
        position = self.progress_slider.value()
        self.global_player.set_position(position)
    
    def _on_slider_moved(self, value: int):
        self.current_time_label.setText(self._format_time(value))
    
    def _on_volume_changed(self, value: int):
        self.global_player.set_volume(value)
        self.volume_label.setText(f"{value}%")
    
    def _format_time(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _on_playlists_loaded(self, playlists: list):
        self._playlists = playlists
        self._update_playlists_view()
    
    def update_theme(self, is_dark: bool):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            widget = self.results_list.itemWidget(item)
            if widget and hasattr(widget, 'update_theme'):
                widget.update_theme(is_dark)
        
        for i in range(self.playlist_songs_list.count()):
            item = self.playlist_songs_list.item(i)
            widget = self.playlist_songs_list.itemWidget(item)
            if widget and hasattr(widget, 'update_theme'):
                widget.update_theme(is_dark)
        
        for i in range(self.local_music_list.count()):
            item = self.local_music_list.item(i)
            widget = self.local_music_list.itemWidget(item)
            if widget and hasattr(widget, 'update_theme'):
                widget.update_theme(is_dark)
        
        self._update_lyrics_theme(is_dark)
        self._update_nav_style()
        
        if hasattr(self, '_spectrum_widget'):
            accent = QColor(96, 165, 250) if is_dark else QColor(0, 120, 212)
            self._spectrum_widget.set_accent_color(accent)
    
    def _update_lyrics_text_color(self, normal_color: str, hover_color: str, selected_color: str):
        self._lyrics_normal_color = normal_color
        self._lyrics_hover_color = hover_color
        self._lyrics_selected_color = selected_color
        
        self.home_lyrics_list.setStyleSheet(f"""
            QListWidget{{
                border: none;
                background: transparent;
                outline: none;
            }}
            QListWidget::item{{
                padding: 12px 20px;
                border-radius: 10px;
                color: {normal_color};
                margin: 3px 0px;
            }}
            QListWidget::item:hover{{
                background: rgba(128, 128, 128, 0.25);
                color: {hover_color};
            }}
            QListWidget::item:selected{{
                background: rgba(128, 128, 128, 0.35);
                color: {selected_color};
            }}
        """)
    
    def _update_lyrics_theme(self, is_dark: bool):
        for i in range(self.home_lyrics_list.count()):
            item = self.home_lyrics_list.item(i)
            if item:
                item.setSelected(i == self._current_lyric_index)
                font = QFont()
                if i == self._current_lyric_index:
                    font.setPointSize(16)
                    font.setBold(True)
                else:
                    font.setPointSize(12)
                    font.setBold(False)
                item.setFont(font)
    
    def _update_nav_style(self):
        current_widget = self.content_stack.currentWidget()
        is_home = (current_widget is None) or (current_widget == self.home_widget)
        is_dark = isDarkTheme()
        
        if is_home:
            text_color = "rgba(255, 255, 255, 0.85) !important"
            text_color_hover = "rgba(255, 255, 255, 0.95) !important"
            text_color_selected = "white !important"
        else:
            if is_dark:
                text_color = "rgba(255, 255, 255, 0.85) !important"
                text_color_hover = "rgba(255, 255, 255, 0.95) !important"
                text_color_selected = "white !important"
            else:
                text_color = "rgba(0, 0, 0, 0.75) !important"
                text_color_hover = "rgba(0, 0, 0, 0.95) !important"
                text_color_selected = "black !important"
        
        style_sheet = f"""
            SegmentedWidget,
            SegmentedWidget * {{
                background: transparent;
            }}
            
            SegmentedWidget QPushButton,
            SegmentedWidget QPushButton * {{
                color: {text_color};
                background: transparent;
                border: none;
            }}
            
            SegmentedWidget QPushButton:hover,
            SegmentedWidget QPushButton:hover * {{
                color: {text_color_hover};
                background: rgba(128, 128, 128, 0.15);
            }}
            
            SegmentedWidget QPushButton:checked,
            SegmentedWidget QPushButton:checked * {{
                color: {text_color_selected};
                background: transparent;
            }}
            
            SegmentedWidget QLabel {{
                color: {text_color};
                background: transparent;
            }}
            
            SegmentedWidget QPushButton:hover QLabel {{
                color: {text_color_hover};
            }}
            
            SegmentedWidget QPushButton:checked QLabel {{
                color: {text_color_selected};
            }}
            
            SegmentedWidget QToolButton,
            SegmentedWidget QToolButton * {{
                color: {text_color};
                background: transparent;
            }}
            
            SegmentedWidget QToolButton:hover,
            SegmentedWidget QToolButton:hover * {{
                color: {text_color_hover};
            }}
            
            SegmentedWidget QToolButton:checked,
            SegmentedWidget QToolButton:checked * {{
                color: {text_color_selected};
            }}
        """
        
        self.content_pivot.setStyleSheet(style_sheet)
        
        self.content_pivot.style().unpolish(self.content_pivot)
        self.content_pivot.style().polish(self.content_pivot)
        
        for child in self.content_pivot.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
    
    def _reset_container_style(self):
        pass
    
    def _apply_theme_to_container(self):
        pass
    
    def _on_download_from_search(self, index: int):
        if 0 <= index < len(self._search_results):
            song = self._search_results[index]
            self._music_service.download_song(song)
            logger.info(f"[Music] 开始下载: {song.name}")
    
    def _batch_download_songs(self):
        selected = self._selected_indices.get("search", set()).copy()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要下载的歌曲")
            return
        
        songs_to_download = []
        for index in sorted(selected):
            if 0 <= index < len(self._search_results):
                song = self._search_results[index]
                if song.source != "local":
                    songs_to_download.append(song)
        
        self._clear_selection("search")
        
        if songs_to_download:
            self._music_service.download_songs_batch(songs_to_download)
            logger.info(f"[Music] 开始批量下载 {len(songs_to_download)} 首歌曲")
        else:
            QMessageBox.information(self, "提示", "所选歌曲均为本地音乐，无需下载")
    
    def _on_download_completed(self, song_id: str, file_path: str):
        logger.info(f"[Music] 下载完成: {song_id} -> {file_path}")
    
    def _on_download_failed(self, song_id: str, error_msg: str):
        logger.error(f"[Music] 下载失败: {song_id} - {error_msg}")
    
    def _on_all_downloads_completed(self, success_count: int, fail_count: int):
        self._init_local_music()
        
        total = success_count + fail_count
        if fail_count == 0:
            QMessageBox.information(self, "下载完成", f"成功下载 {success_count} 首歌曲到本地音乐目录")
        else:
            QMessageBox.warning(self, "下载完成", f"下载完成\n成功: {success_count} 首\n失败: {fail_count} 首")
    
    def _on_download_progress(self, song_id: str, progress: int):
        pass
    
    def _toggle_playlist_dock(self):
        if not self._dockable_playlist:
            return
        
        self._dockable_playlist.toggle_dock()
        self._update_dockable_playlist()
    
    def _update_dockable_playlist(self):
        if self._dockable_playlist and self._dockable_playlist.is_visible():
            self._dockable_playlist.set_playlist(self._play_queue, self._current_index)
    
    def closeEvent(self, event):
        self.global_player.close()
        self._music_service.stop_workers()
        super().closeEvent(event)
