from qfluentwidgets import CheckBox
from PyQt5.QtWidgets import QCheckBox
import os
import random
import math
from enum import Enum
from typing import List
from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal, QSize, QEvent, QPropertyAnimation, QEasingCurve, QRectF, pyqtProperty
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QFrame, QScrollArea, QLineEdit, QPushButton, QComboBox, QSpinBox,
                             QListWidget, QListWidgetItem, QAbstractItemView, QMenu, QAction,
                             QInputDialog, QMessageBox, QStackedWidget, QDialog)
from PyQt5.QtGui import (QFont, QColor, QFontMetrics, QPalette, QLinearGradient, QRadialGradient, QPainter, QPainterPath, QBrush, QPen, 
                         QPixmap, QImage, QConicalGradient)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from qfluentwidgets import (CardWidget, PushButton, TransparentToolButton, ScrollArea,
                           LineEdit, ComboBox, SearchLineEdit, PrimaryPushButton,
                           IconWidget, BodyLabel, StrongBodyLabel, isDarkTheme, TabBar, ListWidget, SpinBox,
                           SubtitleLabel, Dialog)
from qfluentwidgets.common.style_sheet import setCustomStyleSheet
from qfluentwidgets import FluentIcon as FIF

from src.core.cookie_manager import CookieManager

from src.services.extended_music_service import ExtendedMusicService, SongInfo, Playlist, MUSIC_SOURCES
from src.services.global_music_player import GlobalMusicPlayer
from src.core.logger import logger
from src.utils.lyric_parser import LyricParser, LyricLine
from musicdl import musicdl

class PlayMode(Enum):
    SEQUENCE = "sequence"
    LIST_LOOP = "list_loop"
    SINGLE_LOOP = "single_loop"
    SHUFFLE = "shuffle"


class LyricsCardWidget(CardWidget):
    textColorChanged = pyqtSignal(str, str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dominant_color: QColor = None
        self.setObjectName("musicLyricsCard")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
    
    def set_dominant_color(self, color: QColor):
        self._dominant_color = color
        self.update()
    
    def _extract_dominant_color(self, pixmap: QPixmap) -> QColor:
        if pixmap.isNull():
            return QColor(42, 42, 42)
        
        small = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image = small.toImage()
        
        color_counts = {}
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                h = color.hue()
                s = color.saturation()
                v = color.value()
                
                hue_key = h // 30
                if hue_key not in color_counts:
                    color_counts[hue_key] = {'count': 0, 'total_r': 0, 'total_g': 0, 'total_b': 0, 'total_h': 0, 'total_s': 0, 'total_v': 0}
                color_counts[hue_key]['count'] += 1
                color_counts[hue_key]['total_r'] += color.red()
                color_counts[hue_key]['total_g'] += color.green()
                color_counts[hue_key]['total_b'] += color.blue()
                color_counts[hue_key]['total_h'] += h if h >= 0 else 0
                color_counts[hue_key]['total_s'] += s
                color_counts[hue_key]['total_v'] += v
        
        if not color_counts:
            return QColor(42, 42, 42)
        
        dominant_group = max(color_counts.items(), key=lambda x: x[1]['count'])
        count = dominant_group[1]['count']
        
        avg_r = dominant_group[1]['total_r'] // count
        avg_g = dominant_group[1]['total_g'] // count
        avg_b = dominant_group[1]['total_b'] // count
        
        return QColor(avg_r, avg_g, avg_b)
    
    def _get_text_colors(self) -> tuple:
        if not self._dominant_color:
            return ("rgba(255, 255, 255, 0.6)", "rgba(255, 255, 255, 0.9)", "white")
        
        r = self._dominant_color.red()
        g = self._dominant_color.green()
        b = self._dominant_color.blue()
        
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        
        if luminance > 180:
            normal_color = "rgba(0, 0, 0, 0.7)"
            hover_color = "rgba(0, 0, 0, 0.95)"
            selected_color = "black"
        elif luminance > 100:
            normal_color = "rgba(255, 255, 255, 0.7)"
            hover_color = "rgba(255, 255, 255, 0.95)"
            selected_color = "white"
        else:
            normal_color = "rgba(255, 255, 255, 0.75)"
            hover_color = "rgba(255, 255, 255, 0.95)"
            selected_color = "white"
        
        return (normal_color, hover_color, selected_color)
    
    def set_background_from_pixmap(self, pixmap: QPixmap):
        self._dominant_color = self._extract_dominant_color(pixmap)
        self.update()
        
        normal_color, hover_color, selected_color = self._get_text_colors()
        self.textColorChanged.emit(normal_color, hover_color, selected_color)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.fillRect(self.rect(), Qt.transparent)
        
        painter.end()


class VinylRecordWidget(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cover_pixmap = None
        self._rotation_angle = 0
        self._is_playing = False
        self._is_hovered = False
        self._needle_angle = -30
        self._target_needle_angle = -30
        self._needle_animation = None
        self._glow_opacity = 0.0
        self._glow_animation = None
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._on_rotation_timer)
        self._rotation_timer.setInterval(25)
        self.setFixedSize(420, 420)
        self.setCursor(Qt.PointingHandCursor)
        self._init_needle_animation()
        self._init_glow_animation()
    
    def _init_needle_animation(self):
        self._needle_animation = QPropertyAnimation(self, b"needle_angle")
        self._needle_animation.setDuration(1000)
        self._needle_animation.setEasingCurve(QEasingCurve.OutElastic)
    
    def _init_glow_animation(self):
        self._glow_animation = QPropertyAnimation(self, b"glow_opacity")
        self._glow_animation.setDuration(300)
        self._glow_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def get_glow_opacity(self):
        return self._glow_opacity
    
    def set_glow_opacity(self, opacity):
        self._glow_opacity = opacity
        self.update()
    
    glow_opacity = pyqtProperty(float, get_glow_opacity, set_glow_opacity)
    
    def get_needle_angle(self):
        return self._needle_angle
    
    def set_needle_angle(self, angle):
        self._needle_angle = angle
        self.update()
    
    needle_angle = pyqtProperty(float, get_needle_angle, set_needle_angle)
    
    def _create_round_cover(self, pixmap: QPixmap, size: int) -> QPixmap:
        if pixmap.isNull():
            return QPixmap()
        
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        x_offset = (size - scaled.width()) // 2
        y_offset = (size - scaled.height()) // 2
        painter.drawPixmap(x_offset, y_offset, scaled)
        
        painter.end()
        return result
    
    def set_cover(self, pixmap: QPixmap):
        if pixmap.isNull():
            self._cover_pixmap = None
        else:
            self._cover_pixmap = pixmap
        self.update()
    
    def set_playing(self, is_playing: bool):
        if self._is_playing == is_playing:
            return
        
        self._is_playing = is_playing
        
        if is_playing:
            self._target_needle_angle = 25
            self._rotation_timer.start()
        else:
            self._target_needle_angle = -20
            self._rotation_timer.stop()
        
        self._needle_animation.setStartValue(self._needle_angle)
        self._needle_animation.setEndValue(self._target_needle_angle)
        self._needle_animation.start()
    
    def _on_rotation_timer(self):
        self._rotation_angle = (self._rotation_angle + 2.0) % 360
        self.update()
    
    def _draw_turntable_base(self, painter, center_x, center_y):
        base_radius = 150
        
        shadow_gradient = QRadialGradient(center_x, center_y + 5, base_radius + 30)
        shadow_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        shadow_gradient.setColorAt(0.5, QColor(0, 0, 0, 40))
        shadow_gradient.setColorAt(0.8, QColor(0, 0, 0, 60))
        shadow_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(shadow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center_x - base_radius - 30, center_y - base_radius - 25, 
                           (base_radius + 30) * 2, (base_radius + 30) * 2)
        
        base_gradient = QRadialGradient(center_x - 30, center_y - 30, base_radius + 20)
        base_gradient.setColorAt(0.0, QColor(60, 60, 65))
        base_gradient.setColorAt(0.3, QColor(45, 45, 50))
        base_gradient.setColorAt(0.7, QColor(35, 35, 40))
        base_gradient.setColorAt(1.0, QColor(25, 25, 30))
        painter.setBrush(QBrush(base_gradient))
        painter.setPen(QPen(QColor(20, 20, 25), 2))
        painter.drawEllipse(center_x - base_radius - 20, center_y - base_radius - 20, 
                           (base_radius + 20) * 2, (base_radius + 20) * 2)
        
        platter_gradient = QRadialGradient(center_x - 20, center_y - 20, base_radius)
        platter_gradient.setColorAt(0.0, QColor(50, 50, 55))
        platter_gradient.setColorAt(0.5, QColor(40, 40, 45))
        platter_gradient.setColorAt(0.9, QColor(35, 35, 40))
        platter_gradient.setColorAt(1.0, QColor(30, 30, 35))
        painter.setBrush(QBrush(platter_gradient))
        painter.setPen(QPen(QColor(25, 25, 30), 1))
        painter.drawEllipse(center_x - base_radius, center_y - base_radius, 
                           base_radius * 2, base_radius * 2)
        
        for i in range(12):
            angle = i * 30
            rad = math.radians(angle)
            x1 = center_x + (base_radius - 15) * math.cos(rad)
            y1 = center_y + (base_radius - 15) * math.sin(rad)
            x2 = center_x + (base_radius - 5) * math.cos(rad)
            y2 = center_y + (base_radius - 5) * math.sin(rad)
            painter.setPen(QPen(QColor(60, 60, 65, 100), 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        self._draw_turntable_base(painter, center_x, center_y)
        
        painter.translate(center_x, center_y)
        
        self._draw_record(painter)
        
        self._draw_needle(painter)
        
        if self._glow_opacity > 0:
            self._draw_glow_effect(painter)
        
        painter.end()
    
    def _draw_record(self, painter):
        painter.save()
        painter.rotate(self._rotation_angle)
        
        record_radius = 130
        
        outer_shadow = QRadialGradient(0, 0, record_radius + 8)
        outer_shadow.setColorAt(0.85, QColor(0, 0, 0, 0))
        outer_shadow.setColorAt(0.95, QColor(0, 0, 0, 80))
        outer_shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(outer_shadow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-record_radius - 8, -record_radius - 8, 
                           (record_radius + 8) * 2, (record_radius + 8) * 2)
        
        vinyl_gradient = QRadialGradient(0, 0, record_radius)
        vinyl_gradient.setColorAt(0.0, QColor(20, 20, 22))
        vinyl_gradient.setColorAt(0.3, QColor(15, 15, 18))
        vinyl_gradient.setColorAt(0.6, QColor(18, 18, 20))
        vinyl_gradient.setColorAt(0.85, QColor(22, 22, 25))
        vinyl_gradient.setColorAt(0.95, QColor(28, 28, 32))
        vinyl_gradient.setColorAt(1.0, QColor(18, 18, 20))
        painter.setBrush(QBrush(vinyl_gradient))
        painter.setPen(QPen(QColor(8, 8, 10), 1.5))
        painter.drawEllipse(-record_radius, -record_radius, record_radius * 2, record_radius * 2)
        
        for i in range(40):
            r = record_radius - 5 - i * 3
            if r < 60:
                break
            alpha = 8 + (i % 3) * 4
            painter.setPen(QPen(QColor(255, 255, 255, alpha), 0.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(-r, -r, r * 2, r * 2)
        
        highlight = QLinearGradient(-record_radius * 0.8, -record_radius * 0.8,
                                    record_radius * 0.8, record_radius * 0.8)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 0))
        highlight.setColorAt(0.35, QColor(255, 255, 255, 8))
        highlight.setColorAt(0.45, QColor(255, 255, 255, 45))
        highlight.setColorAt(0.55, QColor(255, 255, 255, 8))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-record_radius, -record_radius, record_radius * 2, record_radius * 2)
        
        label_radius = 65
        
        label_ring = QRadialGradient(0, 0, label_radius + 5)
        label_ring.setColorAt(0.0, QColor(100, 80, 60))
        label_ring.setColorAt(0.5, QColor(120, 100, 75))
        label_ring.setColorAt(0.8, QColor(90, 70, 50))
        label_ring.setColorAt(1.0, QColor(70, 55, 40))
        painter.setBrush(QBrush(label_ring))
        painter.setPen(QPen(QColor(60, 45, 30), 1.5))
        painter.drawEllipse(-label_radius - 3, -label_radius - 3, 
                           (label_radius + 3) * 2, (label_radius + 3) * 2)
        
        if self._cover_pixmap and not self._cover_pixmap.isNull():
            round_cover = self._create_round_cover(self._cover_pixmap, label_radius * 2)
            painter.drawPixmap(-label_radius, -label_radius, round_cover)
            
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(-label_radius, -label_radius, label_radius * 2, label_radius * 2)
            
            inner_shadow = QRadialGradient(0, 0, label_radius + 5)
            inner_shadow.setColorAt(0.0, QColor(0, 0, 0, 0))
            inner_shadow.setColorAt(0.7, QColor(0, 0, 0, 20))
            inner_shadow.setColorAt(0.9, QColor(0, 0, 0, 50))
            inner_shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(inner_shadow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-label_radius - 3, -label_radius - 3, 
                               (label_radius + 3) * 2, (label_radius + 3) * 2)
        else:
            no_cover_gradient = QRadialGradient(0, 0, label_radius)
            no_cover_gradient.setColorAt(0.0, QColor(70, 60, 50))
            no_cover_gradient.setColorAt(1.0, QColor(45, 40, 35))
            painter.setBrush(QBrush(no_cover_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-label_radius, -label_radius, label_radius * 2, label_radius * 2)
            
            painter.setPen(QPen(QColor(140, 120, 90), 2.5))
            painter.setFont(QFont("", 32, QFont.Bold))
            painter.drawText(QRectF(-label_radius, -label_radius, label_radius * 2, label_radius * 2), 
                            Qt.AlignCenter, "♪")
        
        center_hole_outer = 12
        center_hole_inner = 6
        
        center_outer = QRadialGradient(0, 0, center_hole_outer)
        center_outer.setColorAt(0.0, QColor(180, 180, 185))
        center_outer.setColorAt(0.5, QColor(150, 150, 155))
        center_outer.setColorAt(1.0, QColor(120, 120, 125))
        painter.setBrush(QBrush(center_outer))
        painter.setPen(QPen(QColor(100, 100, 105), 1))
        painter.drawEllipse(-center_hole_outer, -center_hole_outer, 
                           center_hole_outer * 2, center_hole_outer * 2)
        
        painter.setBrush(QBrush(QColor(10, 10, 12)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-center_hole_inner, -center_hole_inner, 
                           center_hole_inner * 2, center_hole_inner * 2)
        
        painter.setBrush(QBrush(QColor(230, 230, 235)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-2, -2, 4, 4)
        
        painter.restore()
    
    def _draw_needle(self, painter):
        base_x = 135
        base_y = -130
        
        self._draw_tonearm_base(painter, base_x, base_y)
        
        painter.save()
        painter.translate(base_x, base_y)
        painter.rotate(self._needle_angle)
        
        self._draw_counterweight(painter)
        self._draw_s_shaped_arm(painter)
        self._draw_headshell(painter)
        self._draw_stylus(painter)
        
        painter.restore()
    
    def _draw_tonearm_base(self, painter, base_x, base_y):
        shadow_offset = 6
        painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(base_x - 24 + shadow_offset, base_y - 24 + shadow_offset, 48, 48)
        
        outer_ring = QRadialGradient(base_x - 5, base_y - 5, 24)
        outer_ring.setColorAt(0.0, QColor(180, 165, 145))
        outer_ring.setColorAt(0.5, QColor(160, 145, 125))
        outer_ring.setColorAt(0.8, QColor(140, 125, 105))
        outer_ring.setColorAt(1.0, QColor(120, 105, 85))
        painter.setBrush(QBrush(outer_ring))
        painter.setPen(QPen(QColor(90, 75, 55), 2))
        painter.drawEllipse(base_x - 24, base_y - 24, 48, 48)
        
        inner_base = QRadialGradient(base_x - 3, base_y - 3, 18)
        inner_base.setColorAt(0.0, QColor(200, 185, 165))
        inner_base.setColorAt(0.4, QColor(180, 165, 145))
        inner_base.setColorAt(0.7, QColor(160, 145, 125))
        inner_base.setColorAt(1.0, QColor(140, 125, 105))
        painter.setBrush(QBrush(inner_base))
        painter.setPen(QPen(QColor(110, 95, 75), 1.5))
        painter.drawEllipse(base_x - 18, base_y - 18, 36, 36)
        
        painter.setPen(QPen(QColor(100, 85, 65, 120), 1))
        for i in range(12):
            angle = i * 30
            rad = math.radians(angle)
            x1 = base_x + 14 * math.cos(rad)
            y1 = base_y + 14 * math.sin(rad)
            x2 = base_x + 17 * math.cos(rad)
            y2 = base_y + 17 * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        center_hub = QRadialGradient(base_x, base_y, 8)
        center_hub.setColorAt(0.0, QColor(220, 205, 185))
        center_hub.setColorAt(0.5, QColor(190, 175, 155))
        center_hub.setColorAt(1.0, QColor(150, 135, 115))
        painter.setBrush(QBrush(center_hub))
        painter.setPen(QPen(QColor(120, 105, 85), 1))
        painter.drawEllipse(base_x - 8, base_y - 8, 16, 16)
        
        painter.setBrush(QBrush(QColor(80, 70, 60)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(base_x - 3, base_y - 3, 6, 6)
        
        painter.setBrush(QBrush(QColor(60, 50, 40)))
        painter.drawEllipse(base_x - 1, base_y - 1, 2, 2)
    
    def _draw_counterweight(self, painter):
        cw_x = 50
        cw_y = -15
        cw_radius = 16
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cw_x - cw_radius + 3, cw_y - cw_radius + 3, cw_radius * 2, cw_radius * 2)
        
        cw_gradient = QRadialGradient(cw_x - 4, cw_y - 4, cw_radius)
        cw_gradient.setColorAt(0.0, QColor(180, 165, 145))
        cw_gradient.setColorAt(0.3, QColor(160, 145, 125))
        cw_gradient.setColorAt(0.6, QColor(140, 125, 105))
        cw_gradient.setColorAt(1.0, QColor(100, 85, 65))
        painter.setBrush(QBrush(cw_gradient))
        painter.setPen(QPen(QColor(80, 65, 45), 1.5))
        painter.drawEllipse(cw_x - cw_radius, cw_y - cw_radius, cw_radius * 2, cw_radius * 2)
        
        ring_gradient = QRadialGradient(cw_x, cw_y, cw_radius - 3)
        ring_gradient.setColorAt(0.0, QColor(150, 135, 115))
        ring_gradient.setColorAt(0.7, QColor(130, 115, 95))
        ring_gradient.setColorAt(1.0, QColor(110, 95, 75))
        painter.setBrush(QBrush(ring_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cw_x - cw_radius + 3, cw_y - cw_radius + 3, (cw_radius - 3) * 2, (cw_radius - 3) * 2)
        
        painter.setPen(QPen(QColor(90, 75, 55, 150), 1))
        for i in range(8):
            angle = i * 45
            rad = math.radians(angle)
            x1 = cw_x + (cw_radius - 6) * math.cos(rad)
            y1 = cw_y + (cw_radius - 6) * math.sin(rad)
            x2 = cw_x + (cw_radius - 2) * math.cos(rad)
            y2 = cw_y + (cw_radius - 2) * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    def _draw_s_shaped_arm(self, painter):
        arm_path = QPainterPath()
        
        arm_path.moveTo(8, -3)
        arm_path.lineTo(8, 3)
        
        arm_path.cubicTo(8, 3, -5, 20, -20, 25)
        arm_path.cubicTo(-35, 30, -55, 20, -75, 35)
        arm_path.cubicTo(-95, 50, -110, 70, -115, 85)
        arm_path.lineTo(-120, 85)
        
        arm_path.cubicTo(-115, 70, -100, 55, -80, 40)
        arm_path.cubicTo(-60, 25, -40, 35, -25, 30)
        arm_path.cubicTo(-10, 25, 5, 10, 8, -3)
        arm_path.closeSubpath()
        
        arm_gradient = QLinearGradient(50, -15, -120, 85)
        arm_gradient.setColorAt(0.0, QColor(200, 185, 165))
        arm_gradient.setColorAt(0.2, QColor(220, 205, 185))
        arm_gradient.setColorAt(0.4, QColor(240, 225, 205))
        arm_gradient.setColorAt(0.6, QColor(220, 205, 185))
        arm_gradient.setColorAt(0.8, QColor(190, 175, 155))
        arm_gradient.setColorAt(1.0, QColor(170, 155, 135))
        
        painter.setBrush(QBrush(arm_gradient))
        painter.setPen(QPen(QColor(130, 115, 95), 1.2))
        painter.drawPath(arm_path)
        
        highlight_path = QPainterPath()
        highlight_path.moveTo(6, -1)
        highlight_path.cubicTo(6, 2, -8, 18, -22, 23)
        highlight_path.cubicTo(-36, 28, -55, 22, -73, 36)
        highlight_path.lineTo(-75, 34)
        highlight_path.cubicTo(-58, 20, -38, 26, -24, 21)
        highlight_path.cubicTo(-10, 16, 4, 1, 6, -1)
        highlight_path.closeSubpath()
        
        painter.setBrush(QBrush(QColor(255, 250, 240, 60)))
        painter.setPen(Qt.NoPen)
        painter.drawPath(highlight_path)
        
        self._draw_arm_details(painter)
    
    def _draw_arm_details(self, painter):
        painter.setPen(QPen(QColor(100, 85, 65, 100), 0.8))
        painter.drawLine(-30, 27, -32, 29)
        painter.drawLine(-60, 30, -62, 32)
        painter.drawLine(-90, 55, -92, 57)
        
        wire_path = QPainterPath()
        wire_path.moveTo(5, 5)
        wire_path.cubicTo(-10, 15, -30, 25, -50, 35)
        wire_path.cubicTo(-70, 45, -90, 60, -105, 75)
        painter.setPen(QPen(QColor(80, 70, 60, 80), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(wire_path)
    
    def _draw_headshell(self, painter):
        hs_x = -118
        hs_y = 88
        
        headshell_path = QPainterPath()
        headshell_path.moveTo(hs_x + 8, hs_y - 6)
        headshell_path.lineTo(hs_x + 15, hs_y + 5)
        headshell_path.lineTo(hs_x + 12, hs_y + 18)
        headshell_path.lineTo(hs_x - 2, hs_y + 22)
        headshell_path.lineTo(hs_x - 8, hs_y + 15)
        headshell_path.lineTo(hs_x - 6, hs_y + 2)
        headshell_path.lineTo(hs_x + 8, hs_y - 6)
        headshell_path.closeSubpath()
        
        hs_gradient = QLinearGradient(hs_x - 8, hs_y, hs_x + 15, hs_y + 22)
        hs_gradient.setColorAt(0.0, QColor(180, 165, 145))
        hs_gradient.setColorAt(0.3, QColor(200, 185, 165))
        hs_gradient.setColorAt(0.5, QColor(220, 205, 185))
        hs_gradient.setColorAt(0.7, QColor(190, 175, 155))
        hs_gradient.setColorAt(1.0, QColor(160, 145, 125))
        
        painter.setBrush(QBrush(hs_gradient))
        painter.setPen(QPen(QColor(120, 105, 85), 1.2))
        painter.drawPath(headshell_path)
        
        painter.setBrush(QBrush(QColor(255, 250, 240, 50)))
        painter.setPen(Qt.NoPen)
        highlight_rect = QPainterPath()
        highlight_rect.moveTo(hs_x + 6, hs_y - 4)
        highlight_rect.lineTo(hs_x + 10, hs_y + 2)
        highlight_rect.lineTo(hs_x + 8, hs_y + 8)
        highlight_rect.lineTo(hs_x + 4, hs_y + 2)
        highlight_rect.closeSubpath()
        painter.drawPath(highlight_rect)
        
        cart_x = hs_x + 3
        cart_y = hs_y + 8
        cart_width = 12
        cart_height = 10
        
        cart_gradient = QLinearGradient(cart_x, cart_y, cart_x + cart_width, cart_y + cart_height)
        cart_gradient.setColorAt(0.0, QColor(60, 55, 50))
        cart_gradient.setColorAt(0.3, QColor(80, 75, 70))
        cart_gradient.setColorAt(0.5, QColor(100, 95, 90))
        cart_gradient.setColorAt(0.7, QColor(80, 75, 70))
        cart_gradient.setColorAt(1.0, QColor(60, 55, 50))
        
        painter.setBrush(QBrush(cart_gradient))
        painter.setPen(QPen(QColor(40, 35, 30), 0.8))
        painter.drawRoundedRect(int(cart_x), int(cart_y), cart_width, cart_height, 2, 2)
        
        painter.setBrush(QBrush(QColor(140, 130, 120)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cart_x + 2), int(cart_y + 3), 2, 2)
        painter.drawEllipse(int(cart_x + 7), int(cart_y + 3), 2, 2)
    
    def _draw_stylus(self, painter):
        stylus_x = -112
        stylus_y = 110
        
        painter.setPen(QPen(QColor(180, 170, 160), 1.5))
        painter.drawLine(int(stylus_x), int(stylus_y), int(stylus_x - 2), int(stylus_y + 8))
        
        needle_path = QPainterPath()
        needle_path.moveTo(stylus_x - 2, stylus_y + 8)
        needle_path.lineTo(stylus_x - 4, stylus_y + 14)
        needle_path.lineTo(stylus_x - 2, stylus_y + 16)
        needle_path.lineTo(stylus_x, stylus_y + 14)
        needle_path.lineTo(stylus_x - 1, stylus_y + 10)
        needle_path.closeSubpath()
        
        needle_gradient = QLinearGradient(stylus_x - 4, stylus_y + 8, stylus_x, stylus_y + 16)
        needle_gradient.setColorAt(0.0, QColor(200, 190, 180))
        needle_gradient.setColorAt(0.5, QColor(240, 235, 230))
        needle_gradient.setColorAt(1.0, QColor(180, 170, 160))
        
        painter.setBrush(QBrush(needle_gradient))
        painter.setPen(QPen(QColor(120, 110, 100), 0.6))
        painter.drawPath(needle_path)
        
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(stylus_x - 2), int(stylus_y + 13), 2, 2)
    
    def _draw_glow_effect(self, painter):
        record_radius = 130
        glow_color = QColor(100, 150, 255, int(self._glow_opacity * 80))
        
        glow_gradient = QRadialGradient(0, 0, record_radius + 15)
        glow_gradient.setColorAt(0.0, QColor(100, 150, 255, 0))
        glow_gradient.setColorAt(0.7, QColor(100, 150, 255, int(self._glow_opacity * 40)))
        glow_gradient.setColorAt(0.9, QColor(100, 150, 255, int(self._glow_opacity * 80)))
        glow_gradient.setColorAt(1.0, QColor(100, 150, 255, 0))
        
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-record_radius - 15, -record_radius - 15, 
                           (record_radius + 15) * 2, (record_radius + 15) * 2)
    
    def enterEvent(self, event):
        self._is_hovered = True
        if self._glow_animation:
            self._glow_animation.setStartValue(self._glow_opacity)
            self._glow_animation.setEndValue(1.0)
            self._glow_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        if self._glow_animation:
            self._glow_animation.setStartValue(self._glow_opacity)
            self._glow_animation.setEndValue(0.0)
            self._glow_animation.start()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


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
        self.setFixedWidth(350)
        
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
        self._animation.setDuration(300)
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
        target_x = parent_rect.width() - 350
        target_y = 0
        
        bottom_player_height = 70
        bottom_player_margin = 24
        target_height = parent_rect.height() - bottom_player_height - bottom_player_margin
        
        start_rect = QRectF(parent_rect.width(), target_y, 350, target_height)
        end_rect = QRectF(target_x, target_y, 350, target_height)
        
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
        end_rect = QRectF(parent_rect.width(), current_rect.top(), 350, current_rect.height())
        
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
        self._animation.setDuration(300)
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
        self._animation.setDuration(300)
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
    
    def __init__(self, song_info: SongInfo, index: int, is_playing: bool = False, parent=None, show_remove: bool = False, show_playqueue_actions: bool = False, show_checkbox: bool = False, show_download: bool = True):
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
        
        self.setFixedHeight(50 if self.show_playqueue_actions else 60)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()
        self._load_cover()
    
    def _load_cover(self):
        if not self.song_info.img_url:
            return
        
        self._cover_manager = QNetworkAccessManager(self)
        request = QNetworkRequest(QUrl(self.song_info.img_url))
        self._cover_reply = self._cover_manager.get(request)
        
        def on_loaded():
            if self._cover_reply.error() == QNetworkReply.NoError:
                data = self._cover_reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    scaled = pixmap.scaled(44, 44, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self.cover_label.setPixmap(scaled)
            self._cover_reply.deleteLater()
        
        self._cover_reply.finished.connect(on_loaded)
    
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


class CookieSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cookie 设置")
        self.cookie_manager = CookieManager.get_instance()
        self.platforms = [
            ('netease', '奈缇斯', 'NeteaseMusicClient'),
            ('qq', '咕嘎', 'QQMusicClient'),
            ('kugou', '酷汪', 'KugouMusicClient'),
            ('kuwo', '酷me', 'KuwoMusicClient'),
            ('migu', '咪咕', 'MiguMusicClient'),
        ]
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        
        self.platform_tabs = {}
        self.cookie_inputs = {}
        
        for platform_key, platform_name, music_client_name in self.platforms:
            has_cookies = self.cookie_manager.has_cookies(platform_key)
            status = "✓ 已设置" if has_cookies else "✗ 未设置"
            
            card = CardWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            
            header_layout = QHBoxLayout()
            title_label = StrongBodyLabel(platform_name)
            header_layout.addWidget(title_label)
            
            self.platform_tabs[platform_key] = QLabel(status)
            self.platform_tabs[platform_key].setObjectName("statusLabel")
            header_layout.addWidget(self.platform_tabs[platform_key])
            header_layout.addStretch()
            
            card_layout.addLayout(header_layout)
            
            instruction_label = BodyLabel("请从浏览器开发者工具中复制 Cookie 字符串，格式为 name=value; 形式")
            instruction_label.setWordWrap(True)
            card_layout.addWidget(instruction_label)
            
            self.cookie_inputs[platform_key] = LineEdit()
            self.cookie_inputs[platform_key].setPlaceholderText("输入 Cookie 字符串...")
            existing_cookies = self.cookie_manager.get_cookies(platform_key)
            if existing_cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in existing_cookies.items()])
                self.cookie_inputs[platform_key].setText(cookie_str)
            card_layout.addWidget(self.cookie_inputs[platform_key])
            
            btn_layout = QHBoxLayout()
            save_btn = PrimaryPushButton("保存")
            save_btn.clicked.connect(lambda _, p=platform_key: self._save_cookies(p))
            btn_layout.addWidget(save_btn)
            
            test_btn = PushButton("测试")
            test_btn.clicked.connect(lambda _, p=platform_key: self._test_cookies(p))
            btn_layout.addWidget(test_btn)
            
            clear_btn = PushButton("清除")
            clear_btn.clicked.connect(lambda _, p=platform_key: self._clear_cookies(p))
            btn_layout.addWidget(clear_btn)
            
            card_layout.addLayout(btn_layout)
            content_layout.addWidget(card)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        close_btn = PrimaryPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        self.setMinimumSize(500, 500)
        self.setMaximumSize(600, 700)
    
    def _parse_cookie_string(self, cookie_str: str) -> dict:
        cookies = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                cookies[name.strip()] = value.strip()
        return cookies
    
    def _save_cookies(self, platform: str):
        cookie_str = self.cookie_inputs[platform].text()
        if cookie_str:
            cookies = self._parse_cookie_string(cookie_str)
            self.cookie_manager.set_cookies(platform, cookies)
            self.platform_tabs[platform].setText("✓ 已设置")
            QMessageBox.information(self, "成功", f"已保存 {self._get_platform_name(platform)} 的 Cookie\n\n注意：Cookie 是否有效取决于 Cookie 是否过期以及是否包含必要的登录信息。")
        else:
            self.cookie_manager.clear_cookies(platform)
            self.platform_tabs[platform].setText("✗ 未设置")
            QMessageBox.information(self, "成功", f"已清除 {self._get_platform_name(platform)} 的 Cookie")
    
    def _test_cookies(self, platform: str):
        cookies = self.cookie_manager.get_cookies(platform)
        if not cookies:
            QMessageBox.warning(self, "测试失败", f"【{self._get_platform_name(platform)}】\n\n当前没有设置 Cookie，请先保存 Cookie 后再测试。")
            return
        
        platform_name = self._get_platform_name(platform)
        music_client_name = self._get_music_client_name(platform)
        
        try:
            from musicdl import musicdl
            
            os.makedirs(os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'DoroPet', 'musicdl_outputs'), exist_ok=True)
            
            init_cfg = {
                music_client_name: {
                    'work_dir': os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'DoroPet', 'musicdl_outputs'),
                    'default_search_cookies': cookies,
                    'default_parse_cookies': cookies,
                }
            }
            
            music_client = musicdl.MusicClient(
                music_sources=[music_client_name],
                init_music_clients_cfg=init_cfg
            )
            
            results = music_client.search(keyword="test")
            
            if results and any(results.values()):
                QMessageBox.information(self, "测试成功", f"【{platform_name}】\n\n✓ Cookie 配置有效！\n✓ 共获取到 {sum(len(songs) for songs in results.values())} 首测试歌曲。")
            else:
                QMessageBox.warning(self, "测试结果", f"【{platform_name}】\n\n⚠ Cookie 配置可能有效，但没有返回结果。\n⚠ 可能需要更长的登录 Cookie（包含登录 token）。")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"【{platform_name}】\n\n✗ 测试过程中发生错误：\n{str(e)}")
    
    def _clear_cookies(self, platform: str):
        self.cookie_manager.clear_cookies(platform)
        self.cookie_inputs[platform].clear()
        self.platform_tabs[platform].setText("✗ 未设置")
        QMessageBox.information(self, "成功", f"已清除 {self._get_platform_name(platform)} 的 Cookie")
    
    def _get_platform_name(self, platform: str) -> str:
        for p_key, p_name, p_client in self.platforms:
            if p_key == platform:
                return p_name
        return platform
    
    def _get_music_client_name(self, platform: str) -> str:
        for p_key, p_name, p_client in self.platforms:
            if p_key == platform:
                return p_client
        return platform


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
        self._playlists: list = []
        self._play_queue: list = []
        self._current_index: int = -1
        self._play_mode = PlayMode.LIST_LOOP
        self._played_indices = set()
        self._is_user_seeking = False
        self._retry_count = 0
        self._max_retry = 3
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
        from src.services.extended_music_service import get_music_data_dir
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
        self._dockable_playlist.hide()
    
    def _init_content_area(self):
        from qfluentwidgets import SegmentedWidget
        from PyQt5.QtWidgets import QStackedWidget
        
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
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._update_nav_style)
    
    def _toggle_home_view(self):
        """切换首页的显示/隐藏"""
        if self._sliding_panel.is_expanded():
            self._sliding_panel.collapse()
        else:
            self._sliding_panel.expand()
    
    def _on_panel_expanded(self):
        """滑动面板展开时的回调"""
        self._previous_widget = self.content_stack.currentWidget()
        self._is_home_visible = True
        self._apply_theme_to_container()
        self.progress_bar_widget.raise_()
        self.bottom_player.raise_()
    
    def _on_panel_collapsed(self):
        """滑动面板收起时的回调"""
        self._is_home_visible = False
        self._update_nav_style_for_widget(self._previous_widget)
    
    def _update_nav_style_for_widget(self, widget):
        """根据当前widget更新导航栏样式"""
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
    
    def _switch_to_home(self):
        """切换到首页"""
        self._sliding_panel.expand()
    
    def _switch_to_search(self):
        """切换到搜索页面"""
        self._is_home_visible = False
        self._nav_container.show()
        self.content_stack.setCurrentWidget(self.search_widget)
        self._reset_container_style()
        self._update_nav_style()
    
    def _switch_to_local(self):
        """切换到本地音乐页面"""
        self._is_home_visible = False
        self._nav_container.show()
        self._update_local_music_view()
        self.content_stack.setCurrentWidget(self.local_music_widget)
        self._reset_container_style()
        self._update_nav_style()
    
    def _switch_to_playlist(self):
        """切换到歌单页面"""
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
        if obj == self.bottom_player:
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
        return super().eventFilter(obj, event)
    
    def _init_home_view(self):
        self.home_widget = QWidget()
        home_layout = QHBoxLayout(self.home_widget)
        home_layout.setContentsMargins(30, 30, 30, 124)
        home_layout.setSpacing(30)
        
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        vinyl_container = QWidget()
        vinyl_container.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        vinyl_layout = QVBoxLayout(vinyl_container)
        vinyl_layout.setContentsMargins(0, 0, 0, 0)
        vinyl_layout.setSpacing(20)
        
        self._vinyl_record = VinylRecordWidget()
        self._vinyl_record.clicked.connect(self._toggle_play)
        vinyl_layout.addWidget(self._vinyl_record, 0, Qt.AlignCenter)
        
        song_info_widget = QWidget()
        song_info_widget.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
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
        
        self.platform_map = {
            "全部平台": "NeteaseMusicClient,QQMusicClient,KuwoMusicClient,KugouMusicClient,MiguMusicClient",
            "🎵 奈缇斯": "NeteaseMusicClient",
            "🎶 咕嘎": "QQMusicClient",
            "🎧 酷汪": "KugouMusicClient",
            "📻 酷me": "KuwoMusicClient",
            "🎤 咪咕": "MiguMusicClient",
            "📺 B站音乐": "BilibiliMusicClient",
        }
        
        self.platform_combo = ComboBox()
        for text in self.platform_map.keys():
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
        
        self.cookie_settings_btn = TransparentToolButton(FIF.SETTING, self)
        self.cookie_settings_btn.setFixedSize(28, 28)
        self.cookie_settings_btn.setToolTip("Cookie 设置")
        self.cookie_settings_btn.clicked.connect(self._show_cookie_settings)
        
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
        
        search_card_layout.addWidget(self.cookie_settings_btn)
        
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
    
    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "新建歌单", "请输入歌单名称:")
        if ok and name.strip():
            description, _ = QInputDialog.getText(self, "新建歌单", "请输入歌单描述(可选):")
            self._music_service.create_playlist(name.strip(), description or "")
            self._load_playlists()
    
    def _open_playlist(self, playlist: Playlist):
        self._update_playlist_view(playlist)
    
    def _init_local_music_view(self):
        self.local_music_widget = QWidget()
        local_layout = QVBoxLayout(self.local_music_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        
        local_header = QHBoxLayout()
        
        local_title = StrongBodyLabel("📁 本地音乐")
        local_header.addWidget(local_title)
        
        local_header.addStretch()
        
        self.local_count = BodyLabel("0 首歌曲")
        local_header.addWidget(self.local_count)
        
        self.refresh_local_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_local_btn.setFixedSize(28, 28)
        self.refresh_local_btn.setToolTip("刷新本地音乐")
        self.refresh_local_btn.clicked.connect(self._refresh_local_music)
        local_header.addWidget(self.refresh_local_btn)
        
        self.open_music_dir_btn = TransparentToolButton(FIF.FOLDER, self)
        self.open_music_dir_btn.setFixedSize(28, 28)
        self.open_music_dir_btn.setToolTip("打开音乐目录")
        self.open_music_dir_btn.clicked.connect(self._open_music_directory)
        local_header.addWidget(self.open_music_dir_btn)
        
        local_layout.addLayout(local_header)
        
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
        self.progress_bar_widget.setFixedHeight(24)
        self.progress_bar_widget.setStyleSheet("background: transparent;")
        
        progress_layout = QHBoxLayout(self.progress_bar_widget)
        progress_layout.setContentsMargins(20, 0, 20, 0)
        progress_layout.setSpacing(8)
        
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setObjectName("musicTimeLabel")
        self.current_time_label.setFixedWidth(40)
        
        self.progress_slider = ClickableSlider(Qt.Horizontal)
        self.progress_slider.setObjectName("musicProgressSlider")
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setFixedHeight(20)
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
        self.bottom_player.setFixedHeight(70)
        
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
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("musicVolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setFixedHeight(20)
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
    
    def eventFilter(self, obj, event):
        if obj == self and event.type() == QEvent.Resize:
            self._resize_bottom_player()
        return super().eventFilter(obj, event)
    
    def _resize_bottom_player(self):
        self.progress_bar_widget.setFixedWidth(self.width())
        self.progress_bar_widget.move(0, self.height() - 70 - 24)
        self.bottom_player.setFixedWidth(self.width())
        self.bottom_player.move(0, self.height() - 70)
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
    
    def _on_playqueue_reordered(self):
        pass
    
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
        from src.services.extended_music_service import get_music_data_dir
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
    
    def _random_play(self):
        keyword = "热门歌曲"
        platforms_str = self.platform_map.get(self.platform_combo.text(), "")
        platforms = platforms_str.split(',') if platforms_str else []
        self._music_service.search(keyword, platforms)
    
    def _on_search_toggle(self):
        if self._is_searching:
            self._stop_search()
        else:
            self._on_search()
    
    def _on_search(self):
        keyword = self.search_input.text().strip()
        if keyword:
            self._is_searching = True
            self.search_btn.setText("停止")
            self.search_btn.setIcon(FIF.CANCEL)
            self.search_input.setEnabled(False)
            self.platform_combo.setEnabled(False)
            self.search_count_box.setEnabled(False)
            platforms_str = self.platform_map.get(self.platform_combo.currentText(), "")
            platforms = platforms_str.split(',') if platforms_str else []
            search_size = self.search_count_box.value()
            self._music_service.search(keyword, platforms, search_size=search_size)
    
    def _stop_search(self):
        self._music_service.stop_search()
        self._is_searching = False
        self.search_btn.setText("搜索")
        self.search_btn.setIcon(FIF.SEARCH)
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.platform_combo.setEnabled(True)
        self.search_count_box.setEnabled(True)
    
    def _on_search_completed(self, songs: list):
        self._is_searching = False
        self.search_btn.setEnabled(True)
        self.search_btn.setText("搜索")
        self.search_btn.setIcon(FIF.SEARCH)
        self.search_input.setEnabled(True)
        self.platform_combo.setEnabled(True)
        self.search_count_box.setEnabled(True)
        self._search_results = songs
        self._update_search_results_view(songs)
        self.content_pivot.setCurrentItem("search")
        self.content_stack.setCurrentWidget(self.search_widget)
    
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
        self.progress_dialog.setRange(0, 0)  # 使用滚动进度条
        self.progress_dialog.canceled.connect(self._on_import_cancelled)
        self.progress_dialog.show()
        
        self.import_playlist_btn.setEnabled(False)
        
        import threading
        def parse_thread():
            try:
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
        self.local_count.setText(f"{len(self._local_playlist)} 首歌曲")
        
        for i, song in enumerate(self._local_playlist):
            item = QListWidgetItem()
            widget = SongListItemWidget(song, i, i == self._current_index, show_download=False)
            widget.double_clicked.connect(self._on_local_music_double_clicked)
            widget.add_to_playlist_clicked.connect(self._on_add_to_playlist_from_local)
            widget.add_to_playqueue_clicked.connect(self._on_add_to_playqueue_from_local)
            widget.update_theme(isDarkTheme())
            item.setSizeHint(widget.sizeHint())
            self.local_music_list.addItem(item)
            self.local_music_list.setItemWidget(item, widget)
    
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
    
    def _on_add_to_playlist_from_playlist(self, index: int):
        if 0 <= index < len(self._playlist_songs):
            self._show_add_to_playlist_dialog(self._playlist_songs[index])
    
    def _show_cookie_settings(self):
        dialog = CookieSettingsDialog(self)
        dialog.exec_()
    
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
    
    def _play_url(self, url: str):
        logger.info(f"[Music] Playing: {url[:50]}...")
        
        self.global_player._play_url(url)
        self._retry_count = 0
    
    def _on_global_playback_state_changed(self, is_playing: bool):
        logger.info(f"[MusicUI] _on_global_playback_state_changed: is_playing={is_playing}")
        if is_playing:
            self.play_btn.setIcon(FIF.PAUSE)
            self.play_btn.setToolTip("暂停")
            if self._vinyl_record:
                self._vinyl_record.set_playing(True)
        else:
            self.play_btn.setIcon(FIF.PLAY)
            self.play_btn.setToolTip("播放")
            if self._vinyl_record:
                self._vinyl_record.set_playing(False)
    
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
        
        self._network_manager = QNetworkAccessManager()
        
        request = QNetworkRequest(QUrl(img_url))
        self._network_manager.finished.connect(self._on_cover_loaded)
        self._network_manager.get(request)
    
    def _on_cover_loaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled_pixmap = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.cover_label.setPixmap(scaled_pixmap)
            else:
                self.cover_label.setText("🎵")
        else:
            self.cover_label.setText("🎵")
        reply.deleteLater()
    
    def _update_lyric(self, song: SongInfo):
        if song.lyric:
            # logger.info(f"[Lyric] 原始歌词长度: {len(song.lyric)}")
            # logger.info(f"[Lyric] 原始歌词前200字符: {song.lyric[:200]}")
            self._lyric_lines = LyricParser.parse(song.lyric)
            # logger.info(f"[Lyric] 解析歌词成功，共 {len(self._lyric_lines)} 行")
            # if self._lyric_lines:
            #     logger.info(f"[Lyric] 前5行: {[(l.time_ms, l.text) for l in self._lyric_lines[:5]]}")
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
        
        self._home_cover_manager = QNetworkAccessManager()
        request = QNetworkRequest(QUrl(img_url))
        self._home_cover_reply = self._home_cover_manager.get(request)
        
        def on_loaded():
            if self._home_cover_reply.error() == QNetworkReply.NoError:
                data = self._home_cover_reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    self._set_lyrics_card_background(pixmap)
            self._home_cover_reply.deleteLater()
        
        self._home_cover_reply.finished.connect(on_loaded)
    
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
            text_color = QColor.fromHsv(h, min(s + 20, 255), max(v + 20, 180))
        else:
            center_color = QColor.fromHsv(h, min(s + 30, 255), max(v - 10, 40))
            edge_color = QColor.fromHsv(h, min(s + 30, 255), max(v - 60, 20))
            text_color = QColor.fromHsv(h, min(s + 40, 255), max(v - 40, 60))
        
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
        
        self._update_nav_style()
    
    def _apply_theme_to_container(self):
        """应用主题色到容器（仅在首页）"""
        if self._dominant_color and self._original_cover_pixmap:
            self._apply_theme_color_to_window(self._original_cover_pixmap)
    
    def _reset_container_style(self):
        """重置容器样式为默认（非首页）"""
        self._container.setStyleSheet("")
        self._update_nav_style()
    
    def _display_lyrics(self):
        self.home_lyrics_list.clear()
        
        if not self._lyric_lines:
            self.home_lyrics_list.addItem("暂无歌词")
            return
        
        for line in self._lyric_lines:
            item = QListWidgetItem()
            item.setText(line.text)
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
    
    def _update_list_highlight(self):
        pass
    
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
        mode_config = {
            PlayMode.SEQUENCE: (FIF.RIGHT_ARROW, "顺序播放"),
            PlayMode.LIST_LOOP: (FIF.SYNC, "列表循环"),
            PlayMode.SINGLE_LOOP: (FIF.UPDATE, "单曲循环"),
            PlayMode.SHUFFLE: (FIF.TILES, "随机播放"),
        }
        icon, tooltip = mode_config[self._play_mode]
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
    
    def _on_duration_changed(self, duration: int):
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(self._format_time(duration))
    
    def _on_position_changed(self, position: int):
        if not self._is_user_seeking:
            self.progress_slider.setValue(position)
            self.current_time_label.setText(self._format_time(position))
    
    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(FIF.PAUSE)
            self.play_btn.setToolTip("暂停")
            self._position_timer.start()
        else:
            self.play_btn.setIcon(FIF.PLAY)
            self.play_btn.setToolTip("播放")
            self._position_timer.stop()
            
            if state == QMediaPlayer.StoppedState and self._current_playlist:
                if self.progress_slider.value() >= self.progress_slider.maximum() - 100:
                    self._handle_track_finished()
    
    def _on_error_occurred(self, error):
        error_string = self.global_player.player.errorString()
        logger.warning(f"[Music] Playback error: {error} - {error_string}")
        
        if self._retry_count < self._max_retry:
            self._retry_count += 1
            logger.info(f"[Music] Retrying ({self._retry_count}/{self._max_retry})")
            QTimer.singleShot(1000, self._retry_current)
        else:
            self.now_playing_label.setText("播放失败")
            self._retry_count = 0
    
    def _retry_current(self):
        if 0 <= self._current_index < len(self._play_queue):
            song = self._play_queue[self._current_index]
            if song.play_url:
                self._play_url(song.play_url)
            else:
                self._music_service.get_play_url(song)
    
    def _handle_track_finished(self):
        if self._play_mode == PlayMode.SINGLE_LOOP:
            self.global_player.set_position(0)
            self.global_player.resume()
        else:
            self._play_next()
    
    def _update_position(self):
        pass
    
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
