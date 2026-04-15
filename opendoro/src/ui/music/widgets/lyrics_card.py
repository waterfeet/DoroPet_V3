from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap, QPainter
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import CardWidget


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
        step = 2
        
        for y in range(0, image.height(), step):
            for x in range(0, image.width(), step):
                color = image.pixelColor(x, y)
                h = color.hue()
                s = color.saturation()
                v = color.value()
                
                if s < 20 or v < 20 or v > 240:
                    continue
                
                hue_key = h // 30
                if hue_key not in color_counts:
                    color_counts[hue_key] = {
                        'count': 0, 
                        'total_r': 0, 
                        'total_g': 0, 
                        'total_b': 0,
                        'total_h': 0, 
                        'total_s': 0, 
                        'total_v': 0
                    }
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
        
        if count == 0:
            return QColor(42, 42, 42)
        
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
