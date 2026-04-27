from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QPushButton, QTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QSizePolicy,
                             QApplication, QScrollArea, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QSyntaxHighlighter, QTextCharFormat
from qfluentwidgets import (CardWidget, TransparentToolButton, FluentIcon,
                            BodyLabel, StrongBodyLabel, InfoBar, InfoBarPosition)

from src.core.attachments.models import AttachmentInfo, FileCategory


class AttachmentCard(QFrame):
    clicked = pyqtSignal(str)
    remove_requested = pyqtSignal(str)

    def __init__(self, info: AttachmentInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self._status_label = None
        self._warn_label = None
        self._loading_label = None
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            AttachmentCard {
                background: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            AttachmentCard:hover {
                background: #F0F1F3;
                border: 1px solid #BDBDBD;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(48)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 8, 6)
        layout.setSpacing(8)

        icon = QLabel(self.info.icon)
        icon.setStyleSheet("font-size: 16px;")
        icon.setFixedWidth(22)
        layout.addWidget(icon)

        self._text_col = QVBoxLayout()
        self._text_col.setSpacing(0)

        name_label = QLabel(self.info.file_name)
        name_label.setStyleSheet("color: #333; font-size: 12px; font-weight: bold;")
        name_label.setToolTip(self.info.file_name)
        name_label.setFixedWidth(160)
        self._text_col.addWidget(name_label)

        self._status_label = QLabel(self._build_status_text())
        color = self.info.color
        self._status_label.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._text_col.addWidget(self._status_label)

        layout.addLayout(self._text_col)

        self._warn_label = QLabel("")
        self._warn_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self._warn_label)
        layout.addStretch()

        btn_remove = TransparentToolButton(FluentIcon.CLOSE, self)
        btn_remove.setFixedSize(22, 22)
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.info.id))
        layout.addWidget(btn_remove)

        self._refresh_warnings()

    def _build_status_text(self):
        parts = [self.info.size_display]
        if self.info.extraction_method and self.info.extraction_method != "none":
            if self.info.extraction_method == "extracting":
                parts.append("解析中...")
            elif self.info.extraction_method == "failed":
                parts.append("提取失败")
            elif self.info.extraction_method == "full":
                parts.append(f"已提取 {len(self.info.extracted_text)} 字符")
            elif self.info.extraction_method == "truncated":
                parts.append(f"已提取 {len(self.info.extracted_text)} 字符（截断）")
        return " · ".join(parts)

    def _refresh_warnings(self):
        if self.info.extraction_method == "failed":
            self._warn_label.setText("⚠")
            self._warn_label.setToolTip(self.info.error if hasattr(self.info, 'error') else "提取失败")
            self._warn_label.setVisible(True)
        elif self.info.extraction_method == "extracting":
            self._warn_label.setText("⏳")
            self._warn_label.setToolTip("正在解析...")
            self._warn_label.setVisible(True)
        else:
            self._warn_label.setVisible(False)

    def update_extraction_status(self, info: AttachmentInfo):
        self.info = info
        self._status_label.setText(self._build_status_text())
        self._refresh_warnings()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.info.id)
        super().mousePressEvent(event)


class InlinePreviewPanel(QFrame):
    closed = pyqtSignal()

    def __init__(self, info: AttachmentInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("""
            InlinePreviewPanel {
                background: white;
                border: 1px solid #CCC;
                border-radius: 6px;
            }
        """)
        self.setFixedSize(480, 400)
        self.closed.connect(self.close)
        self.setup_ui()

    def _load_original_text(self, max_chars=8000):
        try:
            with open(self.info.file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            try:
                with open(self.info.file_path, "r", encoding="gbk", errors="replace") as f:
                    text = f.read()
            except Exception:
                return None
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n... (文件共 {len(text)} 字符，仅显示前 {max_chars})"
        return text

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        icon_label = QLabel(f"{self.info.icon} {self.info.file_name}")
        icon_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #333;")
        header.addWidget(icon_label)
        header.addStretch()

        close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self.closed.emit)
        header.addWidget(close_btn)
        layout.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(line)

        cat = self.info.category
        if cat in (FileCategory.SPREADSHEET,):
            self._render_table_preview(layout)
        elif cat == FileCategory.CODE:
            self._render_original_preview(layout)
        elif cat in (FileCategory.WEB, FileCategory.DATA, FileCategory.DOCUMENT):
            self._render_dual_preview(layout)
        else:
            self._render_original_preview(layout)

        status = QHBoxLayout()
        status.addWidget(QLabel(f"类型: {self.info.file_type}"))
        status.addWidget(QLabel(f"大小: {self.info.size_display}"))
        if self.info.extraction_method == "truncated":
            status.addWidget(QLabel("⚠ 内容已截断"))
        status.addStretch()
        for i in range(status.count()):
            w = status.itemAt(i).widget()
            if w:
                w.setStyleSheet("color: #999; font-size: 10px;")
        layout.addLayout(status)

    def _render_original_preview(self, layout, monospace=True, label=""):
        text = self._load_original_text()
        if text is None:
            text = self.info.extracted_text or "(无法读取文件内容)"
            label = "提取内容" if self.info.extracted_text else ""
        if label:
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #999; font-size: 10px; padding: 2px 0;")
            layout.addWidget(lbl)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        if monospace:
            font_family = "'Consolas', 'Courier New', monospace"
            font_size = "11px"
        else:
            font_family = "'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif"
            font_size = "13px"
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: #FAFAFA;
                font-size: {font_size};
                font-family: {font_family};
                color: #333;
                line-height: 1.6;
            }}
        """)
        layout.addWidget(text_edit)

    def _render_dual_preview(self, layout):
        original = self._load_original_text()
        if original is not None:
            lbl_orig = QLabel("📄 原始内容")
            lbl_orig.setStyleSheet("color: #666; font-size: 10px; font-weight: bold; padding: 4px 0 2px 0;")
            layout.addWidget(lbl_orig)
            self._render_original_preview(layout, monospace=True, label="")
        else:
            extracted = self.info.extracted_text
            if extracted:
                lbl_ext = QLabel("📋 提取内容")
                lbl_ext.setStyleSheet("color: #666; font-size: 10px; font-weight: bold; padding: 4px 0 2px 0;")
                layout.addWidget(lbl_ext)
                self._render_text_preview(layout, monospace=False)

    def _render_text_preview(self, layout, monospace=False):
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(self.info.extracted_text[:5000])
        if monospace:
            font_family = "'Consolas', 'Courier New', monospace"
            font_size = "11px"
        else:
            font_family = "'Segoe UI', 'Microsoft YaHei', system-ui, sans-serif"
            font_size = "13px"
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: #FAFAFA;
                font-size: {font_size};
                font-family: {font_family};
                color: #333;
                line-height: 1.6;
            }}
        """)
        layout.addWidget(text_edit)

    def _render_table_preview(self, layout):
        text = self.info.extracted_text
        lines = [l for l in text.split("\n") if l.strip().startswith("|")][:100]
        if not lines:
            self._render_text_preview(layout)
            return

        table = QTableWidget()
        data_rows = []
        for line in lines:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if cells:
                data_rows.append(cells)

        if not data_rows:
            self._render_text_preview(layout)
            return

        max_cols = max(len(r) for r in data_rows)
        table.setColumnCount(max_cols)
        table.setRowCount(len(data_rows))
        for r, row in enumerate(data_rows):
            for c, cell in enumerate(row):
                item = QTableWidgetItem(cell)
                if r == 0:
                    item.setBackground(QColor("#E3F2FD"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(r, c, item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setStyleSheet("font-size: 11px;")
        layout.addWidget(table)


class AttachmentInputBar(QFrame):
    attachment_removed = pyqtSignal(str)
    attachment_clicked = pyqtSignal(str)
    files_added = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._attachments: dict = {}
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("AttachmentInputBar { background: transparent; }")
        self.setVisible(False)
        self.setMinimumHeight(0)
        self.setup_ui()

    def setup_ui(self):
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(4, 4, 4, 0)
        self.layout_main.setSpacing(4)

        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(6)
        self.layout_main.addLayout(self.cards_layout)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.btn_add = TransparentToolButton(FluentIcon.ADD, self)
        self.btn_add.setToolTip("添加文件")
        self.btn_add.setFixedSize(26, 26)
        self.btn_add.clicked.connect(self._on_add_files)
        bottom_row.addWidget(self.btn_add)

        self.token_label = QLabel("")
        self.token_label.setStyleSheet("color: #999; font-size: 10px;")
        bottom_row.addWidget(self.token_label)

        bottom_row.addStretch()

        self.btn_clear_all = TransparentToolButton(FluentIcon.DELETE, self)
        self.btn_clear_all.setToolTip("移除所有附件")
        self.btn_clear_all.setFixedSize(22, 22)
        self.btn_clear_all.clicked.connect(self._clear_all)
        bottom_row.addWidget(self.btn_clear_all)

        self.layout_main.addLayout(bottom_row)

    def add_attachment(self, info: AttachmentInfo):
        if info.id in self._attachments:
            return
        card = AttachmentCard(info, self)
        card.remove_requested.connect(self._on_remove)
        card.clicked.connect(lambda aid: self.attachment_clicked.emit(aid))
        self._attachments[info.id] = (info, card)
        self.cards_layout.addWidget(card)
        self._update_visibility()
        self._update_token_label()

    def update_attachment_status(self, attachment_id: str, info: AttachmentInfo):
        if attachment_id not in self._attachments:
            return
        old_info, card = self._attachments[attachment_id]
        self._attachments[attachment_id] = (info, card)
        card.update_extraction_status(info)
        self._update_token_label()

    def remove_attachment(self, attachment_id: str):
        if attachment_id not in self._attachments:
            return
        info, card = self._attachments.pop(attachment_id)
        self.cards_layout.removeWidget(card)
        card.setParent(None)
        card.deleteLater()
        self.attachment_removed.emit(attachment_id)
        self._update_visibility()
        self._update_token_label()

    def _on_remove(self, attachment_id: str):
        self.remove_attachment(attachment_id)

    def _on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "所有支持的文件 (*.docx *.xlsx *.xls *.csv *.pdf *.pptx *.ppt "
            "*.txt *.log *.md *.json *.xml *.yaml *.yml *.html *.htm "
            "*.py *.js *.ts *.jsx *.tsx *.java *.c *.cpp *.h *.go *.rs "
            "*.png *.jpg *.jpeg *.gif *.webp *.bmp "
            "*.zip *.tar *.gz);;所有文件 (*.*)"
        )
        if paths:
            self.files_added.emit(list(paths))

    def get_attachments(self) -> list:
        return [info for info, _ in self._attachments.values()]

    def get_total_tokens(self) -> int:
        return sum(info.token_count for info, _ in self._attachments.values())

    def _clear_all(self):
        for aid in list(self._attachments.keys()):
            self.remove_attachment(aid)

    def _update_visibility(self):
        self.setVisible(len(self._attachments) > 0)

    def _update_token_label(self):
        total = self.get_total_tokens()
        count = len(self._attachments)
        if count == 0:
            self.token_label.setText("")
        else:
            self.token_label.setText(f"📎 {count} 个附件 | ~{total} tokens")

    def clear(self):
        self._clear_all()
