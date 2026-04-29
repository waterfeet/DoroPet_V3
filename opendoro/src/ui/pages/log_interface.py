import os
import re
import json
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from qfluentwidgets import (
    TextEdit, PrimaryPushButton, FluentIcon,
    StrongBodyLabel, ComboBox, BodyLabel,
    ToolButton, isDarkTheme,
)
from src.core.logger import (
    logger, set_log_level, get_log_level_name,
    _LEVEL_NAMES, _LEVEL_ICONS,
)

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

LEVEL_COLORS_DARK = {
    "DEBUG":    "#6b7280",
    "INFO":     "#10b981",
    "WARNING":  "#f59e0b",
    "ERROR":    "#ef4444",
    "CRITICAL": "#a855f7",
}

LEVEL_BG_DARK = {
    "DEBUG":    "#1f2937",
    "INFO":     "#064e3b",
    "WARNING":  "#451a03",
    "ERROR":    "#3b0a0a",
    "CRITICAL": "#2e0a4e",
}

LEVEL_COLORS_LIGHT = {
    "DEBUG":    "#4b5563",
    "INFO":     "#059669",
    "WARNING":  "#b45309",
    "ERROR":    "#dc2626",
    "CRITICAL": "#7c3aed",
}

LEVEL_BG_LIGHT = {
    "DEBUG":    "#e5e7eb",
    "INFO":     "#d1fae5",
    "WARNING":  "#fef3c7",
    "ERROR":    "#fee2e2",
    "CRITICAL": "#ede9fe",
}

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_dir)))
FONT_CONFIG_PATH = os.path.join(_project_root, "config", "log_font.json")
DEFAULT_FONT_SIZE = 11

def _load_font_size():
    try:
        if os.path.exists(FONT_CONFIG_PATH):
            with open(FONT_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            size = data.get("font_size", DEFAULT_FONT_SIZE)
            if 8 <= size <= 24:
                return size
    except Exception:
        pass
    return DEFAULT_FONT_SIZE

def _save_font_size(size):
    try:
        os.makedirs(os.path.dirname(FONT_CONFIG_PATH), exist_ok=True)
        with open(FONT_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"font_size": size}, f, indent=2)
    except Exception:
        pass


class QtLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            level_name = _LEVEL_NAMES.get(record.levelno, "INFO")
            icon = _LEVEL_ICONS.get(record.levelno, "")
            module_name = record.name.replace("DoroPet.", "")
            if module_name == "DoroPet":
                module_name = "Core"
            self.signal.emit({
                "time": self.formatter.formatTime(record, '%H:%M:%S'),
                "level": level_name,
                "icon": icon,
                "module": module_name,
                "message": record.getMessage(),
            })
        except Exception:
            self.handleError(record)


class StreamRedirector(QObject):
    text_written = pyqtSignal(str)

    def __init__(self, stream):
        super().__init__()
        self.stream = stream
        if stream:
            self.original_write = stream.write
            self.original_flush = stream.flush
        else:
            self.original_write = None
            self.original_flush = None

    def write(self, text):
        clean = ANSI_ESCAPE.sub('', text)
        if self.original_write:
            self.original_write(text)
        if clean.strip():
            self.text_written.emit(clean)

    def flush(self):
        if self.original_flush:
            self.original_flush()


class LogInterface(QWidget):
    log_signal = pyqtSignal(dict)

    _LEVEL_MAP = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("LogInterface")
        self._all_entries = []
        self._visible_entries = []
        self._auto_scroll = True
        self._search_text = ""
        self._display_level = logging.INFO
        self._is_dark = isDarkTheme()
        self._font_size = _load_font_size()

        self.init_ui()
        self.init_logger_handler()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(8)

        header_layout = QHBoxLayout()
        self.title_label = StrongBodyLabel("运行日志", self)
        self.title_label.setObjectName("logTitleLabel")

        self.clear_btn = PrimaryPushButton(FluentIcon.DELETE, "清空", self)
        self.clear_btn.clicked.connect(self.clear_logs)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        self.layout.addLayout(header_layout)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.auto_scroll_btn = ToolButton(FluentIcon.SCROLL, self)
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.setToolTip("自动滚动")
        self.auto_scroll_btn.toggled.connect(self._on_auto_scroll_toggled)
        toolbar.addWidget(self.auto_scroll_btn)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("搜索日志...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        self.font_minus_btn = ToolButton(FluentIcon.REMOVE, self)
        self.font_minus_btn.setFixedSize(28, 28)
        self.font_minus_btn.setToolTip("缩小字体")
        self.font_minus_btn.clicked.connect(self._on_font_decrease)
        toolbar.addWidget(self.font_minus_btn)

        self.font_size_label = BodyLabel(str(self._font_size), self)
        self.font_size_label.setFixedWidth(24)
        self.font_size_label.setAlignment(Qt.AlignCenter)
        self.font_size_label.setToolTip("当前字体大小")
        toolbar.addWidget(self.font_size_label)

        self.font_plus_btn = ToolButton(FluentIcon.ADD, self)
        self.font_plus_btn.setFixedSize(28, 28)
        self.font_plus_btn.setToolTip("放大字体")
        self.font_plus_btn.clicked.connect(self._on_font_increase)
        toolbar.addWidget(self.font_plus_btn)

        toolbar.addSpacing(8)

        self.level_combo = ComboBox(self)
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        current_level = get_log_level_name()
        idx = self.level_combo.findText(current_level)
        if idx >= 0:
            self.level_combo.setCurrentIndex(idx)
        self.level_combo.currentTextChanged.connect(self.on_level_changed)
        self.level_combo.setFixedWidth(110)
        toolbar.addWidget(self.level_combo)

        self.layout.addLayout(toolbar)

        self.log_view = TextEdit(self)
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layout.addWidget(self.log_view)

        self._count_label = BodyLabel("共 0 条", self)
        self._count_label.setObjectName("logCountLabel")
        self.layout.addWidget(self._count_label)

    def init_logger_handler(self):
        self.log_signal.connect(self._append_entry)
        self.log_handler = QtLogHandler(self.log_signal)
        logger.addHandler(self.log_handler)

    def _get_colors(self):
        if self._is_dark:
            return (
                LEVEL_COLORS_DARK, LEVEL_BG_DARK,
                "#9ca3af", "#60a5fa", "#e5e7eb",
            )
        else:
            return (
                LEVEL_COLORS_LIGHT, LEVEL_BG_LIGHT,
                "#6b7280", "#2563eb", "#1f2937",
            )

    def _should_show_level(self, level_name):
        entry_level = self._LEVEL_MAP.get(level_name, logging.DEBUG)
        return entry_level >= self._display_level

    def _append_entry(self, entry):
        self._all_entries.append(entry)

        visible = (
            self._should_show_level(entry["level"]) and
            (
                not self._search_text or
                self._search_text.lower() in entry["message"].lower() or
                self._search_text.lower() in entry["module"].lower()
            )
        )
        self._visible_entries.append(visible)

        if visible:
            self._render_entry(entry)
        self._update_count()

    def _render_entry(self, entry):
        level_colors, level_bg, time_color, module_color, msg_color = self._get_colors()
        color = level_colors.get(entry["level"], "#9ca3af")
        bg = level_bg.get(entry["level"], "#f3f4f6")
        icon = entry.get("icon", "")
        fs = self._font_size
        fs_small = max(8, fs - 1)

        html = (
            f'<span style="color:{time_color};font-size:{fs_small}px;">{entry["time"]}</span> '
            f'<span style="display:inline-block;background:{bg};color:{color};'
            f'font-weight:bold;padding:1px 6px;border-radius:3px;font-size:{fs_small}px;'
            f'margin-right:4px;">{icon} {entry["level"]}</span> '
            f'<span style="color:{module_color};font-size:{fs_small}px;margin-right:4px;">[{entry["module"]}]</span> '
            f'<span style="color:{msg_color};font-size:{fs}px;">{self._escape_html(entry["message"])}</span>'
        )
        self.log_view.append(html)
        if self._auto_scroll:
            self.log_view.verticalScrollBar().setValue(
                self.log_view.verticalScrollBar().maximum()
            )

    def _rebuild_view(self):
        self.log_view.clear()
        for i, entry in enumerate(self._all_entries):
            visible = (
                self._should_show_level(entry["level"]) and
                (
                    not self._search_text or
                    self._search_text.lower() in entry["message"].lower() or
                    self._search_text.lower() in entry["module"].lower()
                )
            )
            self._visible_entries[i] = visible
            if visible:
                self._render_entry(entry)
        self._update_count()

    def _update_count(self):
        total = len(self._all_entries)
        visible = sum(1 for v in self._visible_entries if v)
        if total == visible:
            self._count_label.setText(f"共 {total} 条")
        else:
            self._count_label.setText(f"共 {total} 条 | 显示 {visible} 条")

    def _on_auto_scroll_toggled(self, checked):
        self._auto_scroll = checked

    def _on_search_changed(self, text):
        self._search_text = text.strip()
        self._rebuild_view()

    def _on_font_decrease(self):
        if self._font_size > 8:
            self._font_size -= 1
            self._apply_font_size()

    def _on_font_increase(self):
        if self._font_size < 24:
            self._font_size += 1
            self._apply_font_size()

    def _apply_font_size(self):
        self.font_size_label.setText(str(self._font_size))
        _save_font_size(self._font_size)
        self._rebuild_view()

    def _escape_html(self, text):
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )

    def clear_logs(self):
        self._all_entries.clear()
        self._visible_entries.clear()
        self.log_view.clear()
        self._count_label.setText("共 0 条")

    def on_level_changed(self, level_name):
        if level_name in self._LEVEL_MAP:
            new_level = self._LEVEL_MAP[level_name]
            self._display_level = new_level
            set_log_level(new_level)
            self._rebuild_view()

    def update_theme(self):
        self._is_dark = isDarkTheme()
        self._rebuild_view()

    def closeEvent(self, event):
        super().closeEvent(event)
