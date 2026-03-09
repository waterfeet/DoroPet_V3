from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGraphicsDropShadowEffect

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_COLORS
)
from src.resource_utils import resource_path


class AttributeBar(QWidget):
    def __init__(self, icon_name: str, attr_name: str, parent=None):
        super().__init__(parent)
        self.attr_name = attr_name
        self._value = 0
        
        self.setFixedHeight(24)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(18, 18)
        icon_path = resource_path(f"data/icons/attrs/{icon_name}.svg")
        try:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.icon_label.setText(self._get_fallback_icon(icon_name))
                self.icon_label.setStyleSheet("font-size: 14px;")
        except:
            self.icon_label.setText(self._get_fallback_icon(icon_name))
            self.icon_label.setStyleSheet("font-size: 14px;")
        
        self.bar_widget = _ProgressBar(self)
        self.bar_widget.setFixedHeight(12)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.bar_widget, 1)
    
    def _get_fallback_icon(self, icon_name: str) -> str:
        fallbacks = {
            "hunger": "🍖",
            "mood": "💖",
            "cleanliness": "✨",
            "energy": "⚡"
        }
        return fallbacks.get(icon_name, "?")
    
    def set_value(self, value: float):
        self._value = max(0, min(100, value))
        self.bar_widget.setValue(int(self._value))
        self.bar_widget.setColor(self._get_color())
        
        attr_name_cn = ATTR_NAMES.get(self.attr_name, self.attr_name)
        self.setToolTip(f"{attr_name_cn}: {int(self._value)}%")
    
    def _get_color(self) -> str:
        if self._value < 20:
            return STATUS_COLORS["critical"]
        elif self._value < 50:
            return STATUS_COLORS["warning"]
        else:
            return STATUS_COLORS["good"]


class _ProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._color = STATUS_COLORS["good"]
        self._border_radius = 6
        
    def setValue(self, value: int):
        self._value = value
        self.update()
    
    def setColor(self, color: str):
        self._color = color
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        r = self._border_radius
        
        bg_path_color = QColor(255, 255, 255, 60)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_path_color))
        painter.drawRoundedRect(0, 0, w, h, r, r)
        
        if self._value > 0:
            fill_width = int(w * self._value / 100)
            
            gradient = QLinearGradient(0, 0, fill_width, 0)
            base_color = QColor(self._color)
            gradient.setColorAt(0, base_color.lighter(120))
            gradient.setColorAt(1, base_color)
            
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(0, 0, fill_width, h, r, r)


class PetStatusOverlay(QWidget):
    def __init__(self, attr_manager, parent=None):
        super().__init__(parent)
        self.attr_manager = attr_manager
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._is_pinned = False
        
        self._init_ui()
        self._bind_attributes()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)
        
        self._opacity = 1.0
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(200)
        self._fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self._apply_styles()

    def _init_ui(self):
        self.container = QWidget(self)
        self.container.setObjectName("statusContainer")
        self.container.setFixedSize(180, 130)
        
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        self.attr_bars = {}
        
        attr_configs = [
            ("hunger", ATTR_HUNGER),
            ("mood", ATTR_MOOD),
            ("cleanliness", ATTR_CLEANLINESS),
            ("energy", ATTR_ENERGY),
        ]
        
        for icon_name, attr_name in attr_configs:
            bar = AttributeBar(icon_name, attr_name, self.container)
            self.attr_bars[attr_name] = bar
            layout.addWidget(bar)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

    def _apply_styles(self):
        self.container.setStyleSheet("""
            QWidget#statusContainer {
                background: rgba(255, 255, 255, 200);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 100);
            }
        """)

    def _bind_attributes(self):
        for attr_name, bar in self.attr_bars.items():
            self.attr_manager.bind_attribute_widget(
                attr_name,
                bar.set_value
            )

    def follow_pet(self, pet_pos: QPoint, pet_size: QSize):
        if self._is_pinned:
            return
        
        x = pet_pos.x() + (pet_size.width() - self.width()) // 2
        y = pet_pos.y() + pet_size.height() + 10
        self.move(x, y)

    def show_with_auto_hide(self):
        self._fade_in()
        self.hide_timer.stop()
        self.hide_timer.start(5000)

    def _fade_in(self):
        self._fade_animation.stop()
        try:
            self._fade_animation.finished.disconnect()
        except:
            pass
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()
        self.show()

    def _fade_out(self):
        self._fade_animation.stop()
        try:
            self._fade_animation.finished.disconnect()
        except:
            pass
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self.hide)
        self._fade_animation.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.hide_timer.stop()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self.move(event.globalPos() - self._drag_start_pos)
            self._is_pinned = True
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self.hide_timer.start(5000)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        self._is_pinned = False
        if self.parent():
            parent_rect = self.parent().frameGeometry()
            pet_size = self.parent().size() if hasattr(self.parent(), 'size') else QSize(200, 200)
            self.follow_pet(parent_rect.topLeft(), pet_size)
        event.accept()

    def set_visible_by_setting(self, visible: bool):
        if visible:
            self.show_with_auto_hide()
        else:
            self._fade_animation.stop()
            self.hide()
