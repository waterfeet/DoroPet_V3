from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QApplication
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QPixmap
from qfluentwidgets import TransparentToolButton, FluentIcon as FIF, isDarkTheme

from src.services.global_music_player import GlobalMusicPlayer
from src.ui.music.network_manager import NetworkManager

_DARK_QSS = """
#MiniMusicWindow {
    background-color: #2b2b2b;
    border: 1px solid #3a3a3a;
    border-radius: 10px;
}
#trackNameLabel {
    color: #e0e0e0;
    font-size: 12px;
    font-weight: bold;
    background: transparent;
}
#timeLabel {
    color: #9ca3af;
    font-size: 10px;
    background: transparent;
}
#coverLabel {
    background: #333333;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    color: #6b7280;
    font-size: 18px;
}
#expandedWidget {
    background: transparent;
}
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #3a3a3a;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #9ca3af;
    border: none;
    width: 10px;
    height: 10px;
    margin: -3px 0;
    border-radius: 5px;
}
QSlider::handle:horizontal:hover {
    background: #c0c0c0;
}
QSlider::sub-page:horizontal {
    background: #60a5fa;
    border-radius: 2px;
}
"""

_LIGHT_QSS = """
#MiniMusicWindow {
    background-color: #f9f9f9;
    border: 1px solid #d0d0d0;
    border-radius: 10px;
}
#trackNameLabel {
    color: #1f2937;
    font-size: 12px;
    font-weight: bold;
    background: transparent;
}
#timeLabel {
    color: #6b7280;
    font-size: 10px;
    background: transparent;
}
#coverLabel {
    background: #e5e7eb;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    color: #9ca3af;
    font-size: 18px;
}
#expandedWidget {
    background: transparent;
}
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #e5e7eb;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #9ca3af;
    border: none;
    width: 10px;
    height: 10px;
    margin: -3px 0;
    border-radius: 5px;
}
QSlider::handle:horizontal:hover {
    background: #6b7280;
}
QSlider::sub-page:horizontal {
    background: #0078d4;
    border-radius: 2px;
}
"""


class HoverVolumeWidget(QWidget):

    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 20)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setToolTip("音量")
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

    def _on_slider_changed(self, value):
        self.volume_changed.emit(value)

    def set_volume(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)


class MiniMusicWindow(QWidget):

    COLLAPSED_WIDTH = 56
    EXPANDED_WIDTH = 280
    HEIGHT = 56

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MiniMusicWindow")
        self._dragging = False
        self._drag_pos = QPoint()
        self._current_position = 0
        self._total_duration = 0
        self._cover_url = ""
        self._expanded = False
        self._expand_anim = None

        self._init_window()
        self._init_ui()
        self._connect_player()
        self.update_theme()

    def _init_window(self):
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setFixedHeight(self.HEIGHT)
        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        self.resize(self.COLLAPSED_WIDTH, self.HEIGHT)

    def _init_ui(self):
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self.cover_label = QLabel("\U0001f3b5")
        self.cover_label.setObjectName("coverLabel")
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setScaledContents(False)
        self._main_layout.addWidget(self.cover_label)

        self.expanded_widget = QWidget(self)
        self.expanded_widget.setObjectName("expandedWidget")
        self.expanded_widget.hide()
        expanded_layout = QVBoxLayout(self.expanded_widget)
        expanded_layout.setContentsMargins(8, 1, 2, 1)
        expanded_layout.setSpacing(1)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        self.track_label = QLabel("未加载音乐")
        self.track_label.setObjectName("trackNameLabel")
        self.track_label.setMaximumWidth(120)
        top_row.addWidget(self.track_label)

        top_row.addStretch()

        self.close_btn = TransparentToolButton(FIF.CLOSE, self)
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setIconSize(self.close_btn.size())
        self.close_btn.setToolTip("关闭小窗")
        self.close_btn.clicked.connect(self.hide)
        top_row.addWidget(self.close_btn)

        expanded_layout.addLayout(top_row)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("timeLabel")
        controls.addWidget(self.time_label)

        controls.addSpacing(10)

        self.prev_btn = TransparentToolButton(FIF.CARE_LEFT_SOLID, self)
        self.prev_btn.setFixedSize(16, 16)
        self.prev_btn.setIconSize(self.prev_btn.size())
        self.prev_btn.setToolTip("上一首")
        self.prev_btn.clicked.connect(self._play_previous)
        controls.addWidget(self.prev_btn)

        self.play_btn = TransparentToolButton(FIF.PLAY, self)
        self.play_btn.setFixedSize(18, 18)
        self.play_btn.setIconSize(self.play_btn.size())
        self.play_btn.setToolTip("播放")
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)

        self.next_btn = TransparentToolButton(FIF.CARE_RIGHT_SOLID, self)
        self.next_btn.setFixedSize(16, 16)
        self.next_btn.setIconSize(self.next_btn.size())
        self.next_btn.setToolTip("下一首")
        self.next_btn.clicked.connect(self._play_next)
        controls.addWidget(self.next_btn)

        controls.addSpacing(6)

        self.volume_widget = HoverVolumeWidget(self)
        self.volume_widget.volume_changed.connect(self._on_volume_changed)
        controls.addWidget(self.volume_widget)

        controls.addStretch()
        expanded_layout.addLayout(controls)
        self._main_layout.addWidget(self.expanded_widget, 1)


    def _connect_player(self):
        self.global_player = GlobalMusicPlayer.get_instance(self)
        self.global_player.playback_state_changed.connect(self._on_state_changed)
        self.global_player.position_changed.connect(self._on_position_changed)
        self.global_player.duration_changed.connect(self._on_duration_changed)
        self.global_player.current_song_changed.connect(self._on_song_changed)
        self.global_player.volume_changed.connect(self._on_global_volume_changed)

    def _on_global_volume_changed(self, value):
        self.volume_widget.set_volume(value)

    def _on_state_changed(self, is_playing):
        if is_playing:
            self.play_btn.setIcon(FIF.PAUSE)
            self.play_btn.setToolTip("暂停")
        else:
            self.play_btn.setIcon(FIF.PLAY)
            self.play_btn.setToolTip("播放")

    def _on_position_changed(self, position):
        self._current_position = position
        self._update_time_label()

    def _on_duration_changed(self, duration):
        self._total_duration = duration
        self._update_time_label()

    def _on_song_changed(self, song):
        if song:
            track_name = f"{song.name} - {song.singer}" if song.singer else song.name
            short_name = track_name[:18] + "..." if len(track_name) > 18 else track_name
            self.track_label.setText(short_name)
            self._load_cover(song.img_url)
        else:
            self.track_label.setText("未加载音乐")
            self._set_default_cover()

    def _load_cover(self, img_url):
        self._cover_url = img_url
        if not img_url:
            self._set_default_cover()
            return
        self.cover_label.setText("")
        cover_size = 56 if not self._expanded else 54

        def on_loaded(pixmap):
            if not pixmap.isNull():
                sz = 56 if not self._expanded else 54
                scaled = pixmap.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cover_label.setPixmap(scaled)
            else:
                self._set_default_cover()

        def on_error():
            self._set_default_cover()

        NetworkManager.get_instance().fetch_image(img_url, on_loaded, on_error)

    def _set_default_cover(self):
        self._cover_url = ""
        self.cover_label.setText("\U0001f3b5")
        self.cover_label.setPixmap(QPixmap())

    def _update_time_label(self):
        cur = self._format_time(self._current_position)
        total = self._format_time(self._total_duration)
        self.time_label.setText(f"{cur} / {total}")

    def _format_time(self, ms):
        if ms <= 0:
            return "0:00"
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    def _toggle_play(self):
        self.global_player.toggle_play()

    def _play_previous(self):
        self.global_player.play_previous()

    def _play_next(self):
        self.global_player.play_next()

    def _on_volume_changed(self, value):
        self.global_player.set_volume(value)

    def update_theme(self):
        is_dark = isDarkTheme()
        self.setStyleSheet(_DARK_QSS if is_dark else _LIGHT_QSS)

    def showEvent(self, event):
        self.update_theme()
        self._sync_all_state()
        if not self._expanded:
            self._set_collapsed_state()
        super().showEvent(event)

    def _sync_all_state(self):
        try:
            vol = self.global_player.get_volume()
            self.volume_widget.set_volume(vol)

            song = self.global_player.get_current_song()
            if song:
                self._on_song_changed(song)

            is_playing = self.global_player.is_playing()
            self._on_state_changed(is_playing)

            self._current_position = self.global_player.get_position()
            self._total_duration = self.global_player.get_duration()
            self._update_time_label()
        except Exception:
            pass

    def _sync_volume(self):
        try:
            vol = self.global_player.get_volume()
            self.volume_widget.set_volume(vol)
        except Exception:
            pass

    def _animate_width(self, target_width):
        if self._expand_anim and self._expand_anim.state() == QPropertyAnimation.Running:
            self._expand_anim.stop()
        self._expand_anim = QPropertyAnimation(self, b"size")
        self._expand_anim.setDuration(280)
        self._expand_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._expand_anim.setStartValue(self.size())
        self._expand_anim.setEndValue(QSize(target_width, self.HEIGHT))
        self._expand_anim.start()

    def enterEvent(self, event):
        if self._dragging:
            super().enterEvent(event)
            return
        if not self._expanded:
            self._expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._dragging:
            super().leaveEvent(event)
            return
        if self._expanded:
            self._collapse()
        super().leaveEvent(event)

    def _expand(self):
        self._expanded = True
        self._adjust_position_for_expand()
        self._main_layout.setContentsMargins(1, 1, 1, 1)
        self.cover_label.setFixedSize(54, 54)
        self._refresh_cover_size(54)
        self._animate_width(self.EXPANDED_WIDTH)
        self.expanded_widget.show()

    def _collapse(self):
        self._expanded = False
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self.cover_label.setFixedSize(56, 56)
        self._refresh_cover_size(56)
        self.expanded_widget.hide()
        self._animate_width(self.COLLAPSED_WIDTH)

    def _set_collapsed_state(self):
        self._expanded = False
        self.resize(self.COLLAPSED_WIDTH, self.HEIGHT)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self.cover_label.setFixedSize(56, 56)
        self.expanded_widget.hide()

    def _refresh_cover_size(self, size):
        if self._cover_url:
            NetworkManager.get_instance().fetch_image(
                self._cover_url,
                lambda pixmap: self._apply_cover_pixmap(pixmap, size),
                lambda: None,
            )

    def _apply_cover_pixmap(self, pixmap, size):
        if not pixmap.isNull():
            scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_label.setPixmap(scaled)

    def _adjust_position_for_expand(self):
        screen = QApplication.desktop().availableGeometry(self)
        current_geo = self.geometry()
        expand_offset = self.EXPANDED_WIDTH - self.COLLAPSED_WIDTH
        if current_geo.right() + expand_offset > screen.right():
            new_x = screen.right() - self.EXPANDED_WIDTH
            if new_x >= screen.left():
                self.move(new_x, current_geo.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)
