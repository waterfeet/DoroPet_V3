import sys
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from qfluentwidgets import TextEdit, PrimaryPushButton, FluentIcon
from qfluentwidgets import StrongBodyLabel, ComboBox, BodyLabel
from src.core.logger import logger, set_log_level, get_log_level_name

class QtLogHandler(logging.Handler):
    """
    Custom logging handler that emits a signal for UI updates
    """
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        # Use a consistent formatter
        self.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', 
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signal.emit(msg + '\n')
        except Exception:
            self.handleError(record)

class StreamRedirector(QObject):
    """
    Redirects stdout/stderr to a signal
    """
    text_written = pyqtSignal(str)

    def __init__(self, stream, color=None):
        super().__init__()
        self.stream = stream
        self.color = color
        if stream:
            self.original_write = stream.write
            self.original_flush = stream.flush
        else:
            self.original_write = None
            self.original_flush = None

    def write(self, text):
        # Write to original stream if it exists
        if self.original_write:
            self.original_write(text)
        # Emit signal for UI
        self.text_written.emit(text)

    def flush(self):
        if self.original_flush:
            self.original_flush()

class LogInterface(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("LogInterface")
        
        self.init_ui()
        # self.init_redirect() # Disable stdout redirection in favor of logging handler
        self.init_logger_handler()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = StrongBodyLabel("运行日志", self)
        self.title_label.setObjectName("logTitleLabel")
        
        # Log level selector
        self.level_label = BodyLabel("日志级别:", self)
        self.level_combo = ComboBox(self)
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        current_level = get_log_level_name()
        index = self.level_combo.findText(current_level)
        if index >= 0:
            self.level_combo.setCurrentIndex(index)
        self.level_combo.currentTextChanged.connect(self.on_level_changed)
        
        self.clear_btn = PrimaryPushButton(FluentIcon.DELETE, "清空日志", self)
        self.clear_btn.clicked.connect(self.clear_logs)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.level_label)
        header_layout.addWidget(self.level_combo)
        header_layout.addWidget(self.clear_btn)
        
        self.layout.addLayout(header_layout)

        # Log Text Area
        # Use TextEdit from qfluentwidgets or QPlainTextEdit
        self.log_view = TextEdit(self)
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        # Set a monospaced font for logs (Moved to QSS)
        # font = self.log_view.font()
        # font.setFamily("Consolas")
        # font.setPointSize(10)
        # self.log_view.setFont(font)
        
        self.layout.addWidget(self.log_view)

    def init_logger_handler(self):
        # Connect signal to slot
        self.log_signal.connect(self.append_log)
        
        # Create and add handler
        self.log_handler = QtLogHandler(self.log_signal)
        logger.addHandler(self.log_handler)

    def init_redirect(self):
        # Redirect stdout
        self.stdout_redirector = StreamRedirector(sys.stdout)
        self.stdout_redirector.text_written.connect(self.append_log)
        sys.stdout = self.stdout_redirector

        # Redirect stderr
        self.stderr_redirector = StreamRedirector(sys.stderr)
        self.stderr_redirector.text_written.connect(self.append_log)
        sys.stderr = self.stderr_redirector

    def append_log(self, text):
        cursor = self.log_view.textCursor()
        cursor.movePosition(cursor.End)
        self.log_view.setTextCursor(cursor)
        self.log_view.insertPlainText(text)
        # Auto scroll
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def clear_logs(self):
        self.log_view.clear()

    def on_level_changed(self, level_name):
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        if level_name in level_map:
            set_log_level(level_map[level_name])

    def closeEvent(self, event):
        # Restore streams when destroyed (optional, but good practice if window closes)
        # However, since the app keeps running in tray, we might want to keep capturing?
        # If we restore, we lose logs when window is closed.
        # But if we don't restore and this object is destroyed, sys.stdout will point to a destroyed object.
        # Since MainWindow is hidden (not destroyed) on close, we are safe.
        super().closeEvent(event)
