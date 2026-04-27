import math
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, pyqtProperty, pyqtSignal
from PyQt5.QtGui import (QPainter, QPainterPath, QBrush, QPen, QPixmap, QColor,
                         QLinearGradient, QRadialGradient, QFont)
from PyQt5.QtWidgets import QWidget

from ..constants import VinylConstants


class VinylRecordWidget(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cover_pixmap = None
        self._rotation_angle = 0
        self._is_playing = False
        self._is_hovered = False
        self._needle_angle = VinylConstants.NEEDLE_ANGLE_STOPPED
        self._target_needle_angle = VinylConstants.NEEDLE_ANGLE_STOPPED
        self._needle_animation = None
        self._glow_opacity = 0.0
        self._glow_animation = None
        
        self._rotation_timer = QTimer(self)
        self._rotation_timer.timeout.connect(self._on_rotation_timer)
        self._rotation_timer.setInterval(VinylConstants.ROTATION_INTERVAL)
        
        self.setFixedSize(VinylConstants.WIDGET_SIZE, VinylConstants.WIDGET_SIZE)
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
            self._target_needle_angle = VinylConstants.NEEDLE_ANGLE_PLAYING
            self._rotation_timer.start()
        else:
            self._target_needle_angle = VinylConstants.NEEDLE_ANGLE_PAUSED
            self._rotation_timer.stop()
        
        self._needle_animation.stop()
        self._needle_angle = self._needle_angle
        self._needle_animation.setStartValue(self._needle_angle)
        self._needle_animation.setEndValue(self._target_needle_angle)
        self._needle_animation.start()
    
    def _on_rotation_timer(self):
        self._rotation_angle = (self._rotation_angle + VinylConstants.ROTATION_SPEED) % 360
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
        
        record_radius = VinylConstants.RECORD_RADIUS
        
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
        
        label_radius = VinylConstants.LABEL_RADIUS
        
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
        
        center_hole_outer = VinylConstants.CENTER_HOLE_OUTER
        center_hole_inner = VinylConstants.CENTER_HOLE_INNER
        
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
        cw_gradient.setColorAt(0.0, QColor(200, 185, 165))
        cw_gradient.setColorAt(0.5, QColor(170, 155, 135))
        cw_gradient.setColorAt(1.0, QColor(140, 125, 105))
        painter.setBrush(QBrush(cw_gradient))
        painter.setPen(QPen(QColor(110, 95, 75), 1))
        painter.drawEllipse(cw_x - cw_radius, cw_y - cw_radius, cw_radius * 2, cw_radius * 2)
        
        painter.setBrush(QBrush(QColor(160, 145, 125)))
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
        record_radius = VinylConstants.RECORD_RADIUS
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
