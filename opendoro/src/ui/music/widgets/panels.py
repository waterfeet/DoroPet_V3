import math
import random

from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF, QEvent, QPoint
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QListWidgetItem, QAbstractItemView, QSlider, QStyle,
                             QStyleOptionSlider, QStylePainter)
from PyQt5.QtGui import QColor, QPainter, QLinearGradient, QPen, QBrush, QPainterPath
from qfluentwidgets import (CardWidget, TransparentToolButton, ListWidget, 
                           StrongBodyLabel, FluentIcon as FIF, isDarkTheme)

from ..constants import PlaylistConstants, PlayerConstants
from .song_list_item import SongListItemWidget


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


class StyledProgressBar(ClickableSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._accent_color = QColor(96, 165, 250)
        self._bg_color = QColor(60, 60, 70)
        self._glow_enabled = True
        self._hovered = False
        self.setFixedHeight(24)
        self.setCursor(Qt.PointingHandCursor)
    
    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()
    
    def set_glow_enabled(self, enabled: bool):
        self._glow_enabled = enabled
        self.update()
    
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        groove_height = 6
        groove_y = (self.height() - groove_height) // 2
        groove_rect = QRectF(0, groove_y, self.width(), groove_height)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(groove_rect, 3, 3)
        
        if self.maximum() > 0:
            progress = self.value() / self.maximum()
            progress_width = int(self.width() * progress)
            
            if progress_width > 0:
                progress_gradient = QLinearGradient(0, 0, progress_width, 0)
                progress_gradient.setColorAt(0.0, self._accent_color.lighter(120))
                progress_gradient.setColorAt(0.5, self._accent_color)
                progress_gradient.setColorAt(1.0, self._accent_color.darker(110))
                
                progress_rect = QRectF(0, groove_y, progress_width, groove_height)
                painter.setBrush(QBrush(progress_gradient))
                painter.drawRoundedRect(progress_rect, 3, 3)
                
                if self._glow_enabled and self._hovered:
                    glow_color = QColor(self._accent_color)
                    glow_color.setAlpha(60)
                    glow_rect = QRectF(progress_width - 20, groove_y - 2, 40, groove_height + 4)
                    painter.setBrush(QBrush(glow_color))
                    painter.drawRoundedRect(glow_rect, 5, 5)
        
        handle_size = 14 if self._hovered else 12
        handle_x = int((self.value() / max(self.maximum(), 1)) * (self.width() - handle_size))
        handle_y = (self.height() - handle_size) // 2
        handle_rect = QRectF(handle_x, handle_y, handle_size, handle_size)
        
        handle_gradient = QLinearGradient(handle_x, handle_y, handle_x, handle_y + handle_size)
        handle_gradient.setColorAt(0.0, QColor(255, 255, 255))
        handle_gradient.setColorAt(0.5, QColor(240, 240, 245))
        handle_gradient.setColorAt(1.0, QColor(220, 220, 230))
        
        painter.setBrush(QBrush(handle_gradient))
        painter.setPen(QPen(self._accent_color, 2))
        painter.drawEllipse(handle_rect)
        
        if self._hovered:
            glow_color = QColor(self._accent_color)
            glow_color.setAlpha(80)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.NoPen)
            glow_rect = handle_rect.adjusted(-4, -4, 4, 4)
            painter.drawEllipse(glow_rect)
        
        painter.end()


class StyledVolumeSlider(ClickableSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._accent_color = QColor(96, 165, 250)
        self._bg_color = QColor(50, 50, 60)
        self._hovered = False
        self.setFixedSize(100, 20)
        self.setCursor(Qt.PointingHandCursor)
    
    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()
    
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        groove_height = 4
        groove_y = (self.height() - groove_height) // 2
        groove_rect = QRectF(0, groove_y, self.width(), groove_height)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(groove_rect, 2, 2)
        
        if self.maximum() > 0:
            progress = self.value() / self.maximum()
            progress_width = int(self.width() * progress)
            
            if progress_width > 0:
                progress_gradient = QLinearGradient(0, 0, progress_width, 0)
                progress_gradient.setColorAt(0.0, self._accent_color.lighter(130))
                progress_gradient.setColorAt(1.0, self._accent_color)
                
                progress_rect = QRectF(0, groove_y, progress_width, groove_height)
                painter.setBrush(QBrush(progress_gradient))
                painter.drawRoundedRect(progress_rect, 2, 2)
        
        handle_size = 10 if self._hovered else 8
        handle_x = int((self.value() / max(self.maximum(), 1)) * (self.width() - handle_size))
        handle_y = (self.height() - handle_size) // 2
        handle_rect = QRectF(handle_x, handle_y, handle_size, handle_size)
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(self._accent_color, 1.5))
        painter.drawEllipse(handle_rect)
        
        painter.end()


class SpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._num_bars = 32
        self._bar_data = [0.0] * self._num_bars
        self._target_data = [0.0] * self._num_bars
        self._peak_data = [0.0] * self._num_bars
        self._peak_fall_speed = [0.0] * self._num_bars
        self._accent_color = QColor(96, 165, 250)
        self._is_playing = False
        self._idle_phase = 0.0
        self._bar_gap = 3
        self._bar_radius = 2.5
        self._reflection_ratio = 0.25
        self._peak_height = 3
        self._peak_gap = 2
        self._use_real_data = False
        self._real_data_timeout = 0

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.setInterval(20)

        self.setFixedHeight(64)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()

    def set_playing(self, is_playing: bool):
        was_playing = self._is_playing
        self._is_playing = is_playing
        if is_playing:
            self._target_data = [0.0] * self._num_bars
            self._peak_data = [0.0] * self._num_bars
            self._peak_fall_speed = [0.0] * self._num_bars
            self._use_real_data = False
        else:
            self._target_data = [0.0] * self._num_bars
        if not self._animation_timer.isActive():
            self._animation_timer.start()
        self.update()

    def _get_frequency_weight(self, index: int) -> float:
        center = self._num_bars / 2.0
        distance = abs(index - center) / center
        return max(0.3, 1.0 - distance * 0.4)

    def _get_bar_color(self, index: int, value: float) -> QColor:
        t = index / max(self._num_bars - 1, 1)
        base = self._accent_color

        if t < 0.33:
            r = int(base.red() * 0.7 + 255 * 0.3)
            g = int(base.green() * 0.5 + 120 * 0.5)
            b = int(base.blue() * 0.3 + 200 * 0.7)
        elif t < 0.66:
            r = base.red()
            g = base.green()
            b = base.blue()
        else:
            r = int(base.red() * 0.5 + 180 * 0.5)
            g = int(base.green() * 0.7 + 80 * 0.3)
            b = int(base.blue() * 0.9 + 255 * 0.1)

        intensity = 0.6 + value * 0.4
        r = min(255, int(r * intensity))
        g = min(255, int(g * intensity))
        b = min(255, int(b * intensity))
        return QColor(r, g, b)

    def _animate(self):
        if self._is_playing:
            if self._use_real_data:
                self._real_data_timeout += 1
                if self._real_data_timeout > 10:
                    self._use_real_data = False
                    self._real_data_timeout = 0
            else:
                beat = math.sin(self._idle_phase * 0.5) * 0.15 + 0.85
                self._idle_phase += 0.15

                for i in range(self._num_bars):
                    weight = self._get_frequency_weight(i)
                    if random.random() < 0.35:
                        base = random.uniform(0.15, 0.95) * weight * beat
                        self._target_data[i] = max(0.05, min(1.0, base))
                    elif random.random() < 0.4:
                        self._target_data[i] *= random.uniform(0.7, 0.95)

            smoothing = 0.22
            for i in range(self._num_bars):
                self._bar_data[i] += (self._target_data[i] - self._bar_data[i]) * smoothing
                if self._bar_data[i] < 0.01:
                    self._bar_data[i] = 0.0

                if self._bar_data[i] > self._peak_data[i]:
                    self._peak_data[i] = self._bar_data[i]
                    self._peak_fall_speed[i] = 0.0
                else:
                    self._peak_fall_speed[i] += 0.008
                    self._peak_data[i] -= self._peak_fall_speed[i]
                    if self._peak_data[i] < 0:
                        self._peak_data[i] = 0.0
        else:
            self._idle_phase += 0.03
            for i in range(self._num_bars):
                breath = math.sin(self._idle_phase + i * 0.2) * 0.5 + 0.5
                self._bar_data[i] += (breath * 0.08 - self._bar_data[i]) * 0.05
                self._peak_data[i] *= 0.95

        self.update()

    def set_spectrum_data(self, data: list):
        if len(data) == self._num_bars:
            self._target_data = data[:]
            self._use_real_data = True
            self._real_data_timeout = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total_gap = self._bar_gap * (self._num_bars - 1)
        bar_width = (self.width() - total_gap) / self._num_bars
        main_height = self.height() * (1.0 - self._reflection_ratio)
        max_bar_height = main_height - self._peak_height - self._peak_gap - 4

        for i in range(self._num_bars):
            x = i * (bar_width + self._bar_gap)
            value = self._bar_data[i]
            bar_height = max(2, value * max_bar_height)
            bar_y = main_height - bar_height

            color = self._get_bar_color(i, value)
            gradient = QLinearGradient(x, bar_y, x, main_height)
            top_color = QColor(color)
            top_color.setAlpha(220)
            gradient.setColorAt(0.0, top_color)
            gradient.setColorAt(0.4, color)
            mid_color = QColor(color)
            mid_color = mid_color.darker(110)
            gradient.setColorAt(1.0, mid_color)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            bar_rect = QRectF(x, bar_y, bar_width, bar_height)
            painter.drawRoundedRect(bar_rect, self._bar_radius, self._bar_radius)

            if value > 0.4:
                glow_color = QColor(color)
                glow_alpha = int(40 * value)
                glow_color.setAlpha(glow_alpha)
                painter.setBrush(QBrush(glow_color))
                glow_rect = QRectF(x - 1, bar_y - 1, bar_width + 2, bar_height + 2)
                painter.drawRoundedRect(glow_rect, self._bar_radius + 1, self._bar_radius + 1)

            peak_val = self._peak_data[i]
            if peak_val > 0.05:
                peak_y = main_height - peak_val * max_bar_height - self._peak_gap
                peak_color = QColor(color.lighter(140))
                peak_color.setAlpha(200)
                painter.setBrush(QBrush(peak_color))
                peak_rect = QRectF(x, peak_y, bar_width, self._peak_height)
                painter.drawRoundedRect(peak_rect, 1.5, 1.5)

            reflection_height = bar_height * self._reflection_ratio
            if reflection_height > 1:
                ref_y = main_height + 1
                ref_gradient = QLinearGradient(x, ref_y, x, ref_y + reflection_height)
                ref_color = QColor(color)
                ref_color.setAlpha(50)
                ref_gradient.setColorAt(0.0, ref_color)
                ref_color_end = QColor(color)
                ref_color_end.setAlpha(0)
                ref_gradient.setColorAt(1.0, ref_color_end)
                painter.setBrush(QBrush(ref_gradient))
                ref_rect = QRectF(x, ref_y, bar_width, reflection_height)
                painter.drawRoundedRect(ref_rect, self._bar_radius, self._bar_radius)

        painter.end()


class DockablePlaylistWidget(QWidget):
    song_double_clicked = pyqtSignal(int)
    song_remove_clicked = pyqtSignal(int)
    song_download_clicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_visible = False
        self._animation = None
        self._init_ui()
        self._init_animation()
    
    def _init_ui(self):
        self.setFixedWidth(PlaylistConstants.DOCK_WIDTH)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self._container = QWidget()
        self._container.setObjectName("playlistDockContainer")
        self._update_theme()
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        
        title_label = StrongBodyLabel("播放列表")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self._count_label = QLabel("0 首")
        self._count_label.setObjectName("musicTimeLabel")
        header_layout.addWidget(self._count_label)
        
        close_btn = TransparentToolButton(FIF.CLOSE, self)
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.hide_dock)
        header_layout.addWidget(close_btn)
        
        container_layout.addLayout(header_layout)
        
        self._playlist_list = ListWidget()
        self._playlist_list.setSpacing(2)
        self._playlist_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        container_layout.addWidget(self._playlist_list)
        
        main_layout.addWidget(self._container)
    
    def _update_theme(self):
        is_dark = isDarkTheme()
        if is_dark:
            bg_color = "rgba(32, 32, 40, 0.9)"
        else:
            bg_color = "rgba(243, 243, 255, 0.9)"
        
        self._container.setStyleSheet(f"""
            #playlistDockContainer {{
                background: {bg_color};
                border: none;
            }}
        """)
    
    def _init_animation(self):
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(PlaylistConstants.DOCK_ANIMATION_DURATION)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def set_playlist(self, songs: list, current_index: int):
        self._playlist_list.clear()
        self._count_label.setText(f"{len(songs)} 首")
        
        for i, song in enumerate(songs):
            item = QListWidgetItem()
            widget = SongListItemWidget(song, i, i == current_index, show_playqueue_actions=True)
            widget.update_theme(isDarkTheme())
            widget.double_clicked.connect(self.song_double_clicked.emit)
            widget.remove_from_playqueue_clicked.connect(self.song_remove_clicked.emit)
            widget.download_clicked.connect(self.song_download_clicked.emit)
            item.setSizeHint(widget.sizeHint())
            self._playlist_list.addItem(item)
            self._playlist_list.setItemWidget(item, widget)
    
    def show_dock(self):
        if self._is_visible:
            return
        
        self._update_theme()
        
        parent_rect = self.parent().rect()
        target_x = parent_rect.width() - PlaylistConstants.DOCK_WIDTH
        target_y = 0
        
        target_height = parent_rect.height() - PlayerConstants.BOTTOM_PLAYER_HEIGHT - PlayerConstants.BOTTOM_PLAYER_MARGIN
        
        start_rect = QRectF(parent_rect.width(), target_y, PlaylistConstants.DOCK_WIDTH, target_height)
        end_rect = QRectF(target_x, target_y, PlaylistConstants.DOCK_WIDTH, target_height)
        
        self.setGeometry(start_rect.toRect())
        self.show()
        self.raise_()
        
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        self._is_visible = True
    
    def hide_dock(self):
        if not self._is_visible:
            return
        
        current_rect = self.geometry()
        parent_rect = self.parent().rect()
        end_rect = QRectF(parent_rect.width(), current_rect.top(), PlaylistConstants.DOCK_WIDTH, current_rect.height())
        
        self._animation.finished.connect(self._on_hide_finished)
        self._animation.setStartValue(QRectF(current_rect))
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        self._is_visible = False
    
    def _on_hide_finished(self):
        self.hide()
        self._animation.finished.disconnect(self._on_hide_finished)
    
    def toggle_dock(self):
        if self._is_visible:
            self.hide_dock()
        else:
            self.show_dock()
    
    def is_visible(self):
        return self._is_visible


class SlidingPlayerPanel(QWidget):
    expanded = pyqtSignal()
    collapsed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_expanded = False
        self._animation = None
        self._drag_start_y = 0
        self._is_dragging = False
        self._drag_threshold = 50
        
        self._content_widget = None
        self._handle_widget = None
        self._background_widget = None
        
        self.hide()
        
    def setup_ui(self):
        if self._handle_widget:
            return
            
        self._background_widget = QWidget(self)
        self._background_widget.setStyleSheet("""
            QWidget {
                background: qradialgradient(
                    cx: 0.5, cy: 0.5, radius: 0.8,
                    fx: 0.5, fy: 0.5,
                    stop: 0 rgb(60, 60, 80),
                    stop: 1 rgb(30, 30, 50)
                );
            }
        """)
        self._background_widget.lower()
            
        self._handle_widget = QWidget(self)
        self._handle_widget.setFixedHeight(40)
        self._handle_widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 0.9);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)
        
        handle_indicator = QWidget(self._handle_widget)
        handle_indicator.setFixedSize(40, 5)
        handle_indicator.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.4);
                border-radius: 2px;
            }
        """)
        handle_indicator.move((self._handle_widget.width() - 40) // 2, 12)
        
        self._handle_widget.installEventFilter(self)
        
    def set_content(self, widget):
        self._content_widget = widget
        widget.setParent(self)
        
    def set_background_style(self, style_sheet):
        if self._background_widget:
            self._background_widget.setStyleSheet(style_sheet)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._background_widget:
            self._background_widget.setGeometry(0, 0, self.width(), self.height())
        if self._handle_widget:
            self._handle_widget.setGeometry(0, 0, self.width(), 40)
            handle_indicator = self._handle_widget.findChild(QWidget)
            if handle_indicator:
                handle_indicator.move((self.width() - 40) // 2, 12)
        if self._content_widget:
            self._content_widget.setGeometry(0, 40, self.width(), self.height() - 40)
            
    def eventFilter(self, obj, event):
        if obj == self._handle_widget:
            if event.type() == QEvent.MouseButtonPress:
                self._drag_start_y = event.globalY()
                self._is_dragging = True
                return True
            elif event.type() == QEvent.MouseMove and self._is_dragging:
                delta = event.globalY() - self._drag_start_y
                if self._is_expanded and delta > self._drag_threshold:
                    self.collapse()
                    self._is_dragging = False
                    return True
                elif not self._is_expanded and delta < -self._drag_threshold:
                    self.expand()
                    self._is_dragging = False
                    return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._is_dragging = False
                return True
            elif event.type() == QEvent.MouseButtonDblClick:
                if self._is_expanded:
                    self.collapse()
                else:
                    self.expand()
                return True
        return super().eventFilter(obj, event)
        
    def expand(self):
        if self._is_expanded:
            return
        self._is_expanded = True
        self.show()
        
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(PlaylistConstants.DOCK_ANIMATION_DURATION)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        
        parent_rect = self.parent().rect()
        start_rect = QRectF(0, parent_rect.height(), parent_rect.width(), parent_rect.height())
        end_rect = QRectF(0, 0, parent_rect.width(), parent_rect.height())
        
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        self.expanded.emit()
        
    def collapse(self):
        if not self._is_expanded:
            return
        self._is_expanded = False
        
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(PlaylistConstants.DOCK_ANIMATION_DURATION)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        
        parent_rect = self.parent().rect()
        start_rect = QRectF(0, 0, parent_rect.width(), parent_rect.height())
        end_rect = QRectF(0, parent_rect.height(), parent_rect.width(), parent_rect.height())
        
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        self._animation.finished.connect(self.hide)
        self.collapsed.emit()
        
    def is_expanded(self):
        return self._is_expanded
