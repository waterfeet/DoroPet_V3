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
        self._num_bars = 48
        self._bar_data = [0.0] * self._num_bars
        self._target_data = [0.0] * self._num_bars
        self._accent_color = QColor(96, 165, 250)
        self._is_playing = False
        
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate)
        self._animation_timer.setInterval(25)
        
        self.setFixedHeight(40)
        self.setAttribute(Qt.WA_TranslucentBackground)
    
    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()
    
    def set_playing(self, is_playing: bool):
        self._is_playing = is_playing
        if is_playing:
            self._animation_timer.start()
        else:
            self._animation_timer.stop()
            self._bar_data = [0.0] * self._num_bars
            self._target_data = [0.0] * self._num_bars
            self.update()
    
    def _animate(self):
        if not self._is_playing:
            return
        
        import random
        for i in range(self._num_bars):
            if random.random() < 0.3:
                self._target_data[i] = random.uniform(0.2, 1.0)
            elif random.random() < 0.5:
                self._target_data[i] *= 0.9
        
        smoothing = 0.25
        for i in range(self._num_bars):
            self._bar_data[i] += (self._target_data[i] - self._bar_data[i]) * smoothing
        
        self.update()
    
    def set_spectrum_data(self, data: list):
        if len(data) == self._num_bars:
            self._target_data = data[:]
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bar_width = (self.width() - 20) / self._num_bars - 2
        max_height = self.height() - 8
        
        for i in range(self._num_bars):
            x = 10 + i * (bar_width + 2)
            bar_height = self._bar_data[i] * max_height
            
            if bar_height < 2:
                bar_height = 2
            
            y = (self.height() - bar_height) / 2
            
            gradient = QLinearGradient(x, y, x, y + bar_height)
            gradient.setColorAt(0.0, self._accent_color.lighter(130))
            gradient.setColorAt(0.5, self._accent_color)
            gradient.setColorAt(1.0, self._accent_color.lighter(130))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            
            radius = min(bar_width / 2, 2)
            rect = QRectF(x, y, bar_width, bar_height)
            painter.drawRoundedRect(rect, radius, radius)
            
            if self._bar_data[i] > 0.5:
                glow_color = QColor(self._accent_color)
                glow_color.setAlpha(int(50 * self._bar_data[i]))
                painter.setBrush(QBrush(glow_color))
                glow_rect = QRectF(x - 1, y - 2, bar_width + 2, bar_height + 4)
                painter.drawRoundedRect(glow_rect, radius + 1, radius + 1)
        
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
