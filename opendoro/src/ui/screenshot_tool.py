import sys
import os
import uuid
import tempfile
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QScreen

class ScreenCaptureTool(QWidget):
    screenshot_captured = pyqtSignal(str) # Path to saved file
    canceled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Frameless, on top
        # Removed Qt.Tool to avoid potential taskbar/window manager conflicts
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        
        self.start_pos = None
        self.end_pos = None
        self.is_drawing = False
        
        # Capture the full screen safely
        self.full_screen_pixmap, self.global_geometry = self.capture_screen()
        
        # Resize this widget to match the virtual desktop geometry
        self.setGeometry(self.global_geometry)

    def capture_screen(self):
        """
        Safely capture all screens and stitch them together.
        This avoids issues with grabWindow(0) on virtual geometry causing crashes.
        """
        screens = QApplication.screens()
        
        # Calculate bounding box of all screens
        x_min = min(s.geometry().x() for s in screens)
        y_min = min(s.geometry().y() for s in screens)
        x_max = max(s.geometry().x() + s.geometry().width() for s in screens)
        y_max = max(s.geometry().y() + s.geometry().height() for s in screens)
        
        total_rect = QRect(x_min, y_min, x_max - x_min, y_max - y_min)
        
        full_pixmap = QPixmap(total_rect.size())
        full_pixmap.fill(Qt.black)
        
        painter = QPainter(full_pixmap)
        
        for screen in screens:
            # Grab specific screen content
            pix = screen.grabWindow(0)
            
            # Draw at correct relative position
            # geometry() is global, we need relative to total_rect
            pos = screen.geometry().topLeft() - total_rect.topLeft()
            painter.drawPixmap(pos, pix)
            
        painter.end()
        return full_pixmap, total_rect

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 1. Draw the frozen full screen background
        # Scale it to the widget size (handles High DPI differences)
        painter.drawPixmap(self.rect(), self.full_screen_pixmap)
        
        # 2. Draw a semi-transparent black overlay
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())
        
        # 3. If dragging, "cut out" the selection area
        if self.start_pos and self.end_pos:
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Calculate source rect in the pixmap
            # Map widget coords (logical) to pixmap coords (physical)
            pw = self.full_screen_pixmap.width()
            ph = self.full_screen_pixmap.height()
            ww = self.width()
            wh = self.height()
            
            sx = pw / ww if ww > 0 else 1
            sy = ph / wh if wh > 0 else 1
            
            source_rect = QRect(
                int(selection_rect.x() * sx),
                int(selection_rect.y() * sy),
                int(selection_rect.width() * sx),
                int(selection_rect.height() * sy)
            )
            
            # Draw the original bright pixels in the selection rect
            painter.drawPixmap(selection_rect, self.full_screen_pixmap, source_rect)
            
            # Border
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            painter.drawRect(selection_rect)
            
            # Text info
            w, h = selection_rect.width(), selection_rect.height()
            text = f"{w} x {h}"
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(selection_rect.topLeft() - QPoint(0, 5), text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            self.end_pos = event.pos()
            self.finish_screenshot()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.canceled.emit()
            self.close()

    def finish_screenshot(self):
        if not self.start_pos or not self.end_pos:
            self.canceled.emit()
            self.close()
            return
            
        rect = QRect(self.start_pos, self.end_pos).normalized()
        if rect.width() < 5 or rect.height() < 5:
            self.canceled.emit()
            self.close()
            return

        # Calculate scale to crop correctly
        pw = self.full_screen_pixmap.width()
        ph = self.full_screen_pixmap.height()
        ww = self.width()
        wh = self.height()
        
        sx = pw / ww if ww > 0 else 1
        sy = ph / wh if wh > 0 else 1
        
        crop_rect = QRect(
            int(rect.x() * sx),
            int(rect.y() * sy),
            int(rect.width() * sx),
            int(rect.height() * sy)
        )

        cropped = self.full_screen_pixmap.copy(crop_rect)
        
        # Save
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "doropet_images")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            filename = f"screenshot_{uuid.uuid4().hex}.png"
            file_path = os.path.join(temp_dir, filename)
            cropped.save(file_path, "PNG")
            
            self.screenshot_captured.emit(file_path)
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            self.canceled.emit()
            
        self.close()
