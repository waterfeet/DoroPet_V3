import sys
import os
import uuid
import tempfile
from enum import Enum
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QFont, QCursor


class State(Enum):
    SELECTING = 1
    EDITING = 2


class Handle(Enum):
    NONE = 0
    TOP_LEFT = 1
    TOP = 2
    TOP_RIGHT = 3
    RIGHT = 4
    BOTTOM_RIGHT = 5
    BOTTOM = 6
    BOTTOM_LEFT = 7
    LEFT = 8
    MOVE = 9


class ScreenCaptureTool(QWidget):
    screenshot_captured = pyqtSignal(str)
    canceled = pyqtSignal()

    HANDLE_SIZE = 12
    MAGNIFIER_SIZE = 150
    MAGNIFIER_ZOOM = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        self.state = State.SELECTING
        self.start_pos = None
        self.end_pos = None
        self.is_drawing = False
        self.active_handle = Handle.NONE
        self.drag_start_pos = None
        self.original_rect = None
        self.magnifier_pos = None

        self.full_screen_pixmap, self.global_geometry = self.capture_screen()
        self.setGeometry(self.global_geometry)

        self.toolbar = None
        self.info_label = None

    def capture_screen(self):
        screens = QApplication.screens()
        x_min = min(s.geometry().x() for s in screens)
        y_min = min(s.geometry().y() for s in screens)
        x_max = max(s.geometry().x() + s.geometry().width() for s in screens)
        y_max = max(s.geometry().y() + s.geometry().height() for s in screens)
        total_rect = QRect(x_min, y_min, x_max - x_min, y_max - y_min)
        full_pixmap = QPixmap(total_rect.size())
        full_pixmap.fill(Qt.black)
        painter = QPainter(full_pixmap)
        for screen in screens:
            pix = screen.grabWindow(0)
            pos = screen.geometry().topLeft() - total_rect.topLeft()
            painter.drawPixmap(pos, pix)
        painter.end()
        return full_pixmap, total_rect

    def get_selection_rect(self):
        if not self.start_pos or not self.end_pos:
            return QRect()
        return QRect(self.start_pos, self.end_pos).normalized()

    def get_handles(self):
        rect = self.get_selection_rect()
        if rect.isEmpty():
            return {}
        hs = self.HANDLE_SIZE
        half = hs // 2
        return {
            Handle.TOP_LEFT: QRect(rect.left() - half, rect.top() - half, hs, hs),
            Handle.TOP: QRect(rect.center().x() - half, rect.top() - half, hs, hs),
            Handle.TOP_RIGHT: QRect(rect.right() - half, rect.top() - half, hs, hs),
            Handle.RIGHT: QRect(rect.right() - half, rect.center().y() - half, hs, hs),
            Handle.BOTTOM_RIGHT: QRect(rect.right() - half, rect.bottom() - half, hs, hs),
            Handle.BOTTOM: QRect(rect.center().x() - half, rect.bottom() - half, hs, hs),
            Handle.BOTTOM_LEFT: QRect(rect.left() - half, rect.bottom() - half, hs, hs),
            Handle.LEFT: QRect(rect.left() - half, rect.center().y() - half, hs, hs),
        }

    def get_handle_at(self, pos):
        handles = self.get_handles()
        for handle_type, handle_rect in handles.items():
            expanded = handle_rect.adjusted(-4, -4, 4, 4)
            if expanded.contains(pos):
                return handle_type
        if self.get_selection_rect().contains(pos):
            return Handle.MOVE
        return Handle.NONE

    def get_cursor_for_handle(self, handle):
        cursors = {
            Handle.TOP_LEFT: Qt.SizeFDiagCursor,
            Handle.TOP_RIGHT: Qt.SizeBDiagCursor,
            Handle.BOTTOM_RIGHT: Qt.SizeFDiagCursor,
            Handle.BOTTOM_LEFT: Qt.SizeBDiagCursor,
            Handle.TOP: Qt.SizeVerCursor,
            Handle.BOTTOM: Qt.SizeVerCursor,
            Handle.LEFT: Qt.SizeHorCursor,
            Handle.RIGHT: Qt.SizeHorCursor,
            Handle.MOVE: Qt.SizeAllCursor,
        }
        return cursors.get(handle, Qt.CrossCursor)

    def widget_to_pixmap_rect(self, widget_rect):
        pw = self.full_screen_pixmap.width()
        ph = self.full_screen_pixmap.height()
        ww = self.width()
        wh = self.height()
        sx = pw / ww if ww > 0 else 1
        sy = ph / wh if wh > 0 else 1
        return QRect(
            int(widget_rect.x() * sx),
            int(widget_rect.y() * sy),
            int(widget_rect.width() * sx),
            int(widget_rect.height() * sy)
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.full_screen_pixmap)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        selection_rect = self.get_selection_rect()
        if not selection_rect.isEmpty():
            source_rect = self.widget_to_pixmap_rect(selection_rect)
            painter.drawPixmap(selection_rect, self.full_screen_pixmap, source_rect)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            painter.drawRect(selection_rect)

            if self.state == State.EDITING:
                handles = self.get_handles()
                for handle_rect in handles.values():
                    painter.fillRect(handle_rect, QColor(0, 120, 212))

        if self.magnifier_pos and self.state == State.SELECTING:
            self.draw_magnifier(painter, self.magnifier_pos)

        if not selection_rect.isEmpty():
            self.draw_info(painter, selection_rect)

    def draw_magnifier(self, painter, pos):
        size = self.MAGNIFIER_SIZE
        zoom = self.MAGNIFIER_ZOOM
        half = size // 2

        magnifier_rect = QRect(pos.x() + 20, pos.y() + 20, size, size)
        if magnifier_rect.right() > self.width():
            magnifier_rect.moveRight(pos.x() - 20)
        if magnifier_rect.bottom() > self.height():
            magnifier_rect.moveBottom(pos.y() - 20)

        source_size = size // zoom
        source_rect = self.widget_to_pixmap_rect(
            QRect(pos.x() - source_size // 2, pos.y() - source_size // 2, source_size, source_size)
        )

        painter.save()
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawPixmap(magnifier_rect, self.full_screen_pixmap, source_rect)
        painter.setPen(QPen(QColor(0, 120, 212), 2))
        painter.drawRect(magnifier_rect)

        center_x = magnifier_rect.x() + half
        center_y = magnifier_rect.y() + half
        cross_size = zoom * 2
        painter.setPen(QPen(QColor(255, 0, 0), 1))
        painter.drawLine(center_x - cross_size, center_y, center_x + cross_size, center_y)
        painter.drawLine(center_x, center_y - cross_size, center_x, center_y + cross_size)
        painter.restore()

        pw = self.full_screen_pixmap.width()
        ph = self.full_screen_pixmap.height()
        ww = self.width()
        wh = self.height()
        px = int(pos.x() * pw / ww) if ww > 0 else 0
        py = int(pos.y() * ph / wh) if wh > 0 else 0

        source_img = self.full_screen_pixmap.toImage()
        if source_img.valid(px, py):
            color = source_img.pixelColor(px, py)
            color_text = f"RGB({color.red()}, {color.green()}, {color.blue()})"
            pos_text = f"X: {px}  Y: {py}"

            painter.save()
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Consolas", 9)
            painter.setFont(font)

            text_y = magnifier_rect.bottom() + 5
            painter.drawText(magnifier_rect.x(), text_y, pos_text)
            painter.drawText(magnifier_rect.x(), text_y + 15, color_text)
            painter.restore()

    def draw_info(self, painter, rect):
        w, h = rect.width(), rect.height()
        text = f"{w} x {h}"
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 10)
        painter.setFont(font)

        text_rect = painter.fontMetrics().boundingRect(text)
        label_x = rect.left()
        label_y = rect.top() - text_rect.height() - 8

        if label_y < 5:
            label_y = rect.bottom() + 5

        bg_rect = QRect(label_x - 4, label_y - 2, text_rect.width() + 8, text_rect.height() + 4)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 150))
        painter.drawText(label_x, label_y + text_rect.height() - 2, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.state == State.SELECTING:
                self.start_pos = event.pos()
                self.end_pos = event.pos()
                self.is_drawing = True
            elif self.state == State.EDITING:
                handle = self.get_handle_at(event.pos())
                if handle != Handle.NONE:
                    self.active_handle = handle
                    self.drag_start_pos = event.pos()
                    self.original_rect = self.get_selection_rect()
            self.update()

    def mouseMoveEvent(self, event):
        self.magnifier_pos = event.pos()

        if self.state == State.SELECTING:
            if self.is_drawing:
                self.end_pos = event.pos()
            self.setCursor(Qt.CrossCursor)
        elif self.state == State.EDITING:
            if self.active_handle != Handle.NONE and self.drag_start_pos:
                self.adjust_selection(event.pos())
            else:
                handle = self.get_handle_at(event.pos())
                self.setCursor(self.get_cursor_for_handle(handle))

        self.update()

    def adjust_selection(self, pos):
        if not self.original_rect:
            return

        delta = pos - self.drag_start_pos
        rect = QRect(self.original_rect)

        if self.active_handle == Handle.MOVE:
            rect.translate(delta)
        elif self.active_handle == Handle.TOP_LEFT:
            rect.setTopLeft(rect.topLeft() + delta)
        elif self.active_handle == Handle.TOP:
            rect.setTop(rect.top() + delta.y())
        elif self.active_handle == Handle.TOP_RIGHT:
            rect.setTopRight(rect.topRight() + delta)
        elif self.active_handle == Handle.RIGHT:
            rect.setRight(rect.right() + delta.x())
        elif self.active_handle == Handle.BOTTOM_RIGHT:
            rect.setBottomRight(rect.bottomRight() + delta)
        elif self.active_handle == Handle.BOTTOM:
            rect.setBottom(rect.bottom() + delta.y())
        elif self.active_handle == Handle.BOTTOM_LEFT:
            rect.setBottomLeft(rect.bottomLeft() + delta)
        elif self.active_handle == Handle.LEFT:
            rect.setLeft(rect.left() + delta.x())

        normalized = rect.normalized()
        self.start_pos = normalized.topLeft()
        self.end_pos = normalized.bottomRight()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.state == State.SELECTING and self.is_drawing:
                self.is_drawing = False
                self.end_pos = event.pos()
                rect = self.get_selection_rect()
                if rect.width() >= 5 and rect.height() >= 5:
                    self.state = State.EDITING
                    self.show_toolbar()
            elif self.state == State.EDITING:
                self.active_handle = Handle.NONE
                self.drag_start_pos = None
                self.original_rect = None
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.state == State.EDITING:
            self.finish_screenshot()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel_screenshot()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.state == State.EDITING:
                self.finish_screenshot()

    def show_toolbar(self):
        if self.toolbar:
            return

        self.toolbar = QWidget(self)
        self.toolbar.setAttribute(Qt.WA_StyledBackground)
        self.toolbar.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 230);
                border-radius: 4px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton#cancelBtn {
                background-color: #444;
            }
            QPushButton#cancelBtn:hover {
                background-color: #555;
            }
        """)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        ok_btn = QPushButton("确认 (Enter)")
        ok_btn.clicked.connect(self.finish_screenshot)
        layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消 (ESC)")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.cancel_screenshot)
        layout.addWidget(cancel_btn)

        self.toolbar.adjustSize()
        self.update_toolbar_position()
        self.toolbar.show()

    def update_toolbar_position(self):
        if not self.toolbar:
            return

        rect = self.get_selection_rect()
        toolbar_width = self.toolbar.width()
        toolbar_height = self.toolbar.height()

        x = rect.left() + (rect.width() - toolbar_width) // 2
        y = rect.bottom() + 10

        if y + toolbar_height > self.height():
            y = rect.top() - toolbar_height - 10
        if x < 5:
            x = 5
        if x + toolbar_width > self.width() - 5:
            x = self.width() - toolbar_width - 5

        self.toolbar.move(x, y)

    def update(self):
        super().update()
        if self.toolbar and self.state == State.EDITING:
            self.update_toolbar_position()

    def cancel_screenshot(self):
        self.canceled.emit()
        self.close()

    def finish_screenshot(self):
        rect = self.get_selection_rect()
        if rect.width() < 5 or rect.height() < 5:
            self.canceled.emit()
            self.close()
            return

        crop_rect = self.widget_to_pixmap_rect(rect)
        cropped = self.full_screen_pixmap.copy(crop_rect)

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
