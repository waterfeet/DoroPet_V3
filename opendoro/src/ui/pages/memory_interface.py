import json
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QHeaderView,
                             QDialog, QDialogButtonBox, QTableWidgetItem, QComboBox,
                             QSpinBox, QTextEdit, QMessageBox, QMenu, QAbstractItemView)
from PyQt5.QtCore import Qt, QSettings
from qfluentwidgets import (ScrollArea, PrimaryPushButton, PushButton, TableWidget,
                            TitleLabel, BodyLabel, FluentIcon, LineEdit, MessageBox,
                            StrongBodyLabel, InfoBar)

from src.core.database import ChatDatabase

CATEGORY_MAP = {
    "fact": "📋 用户信息",
    "preference": "⭐ 用户偏好",
    "event": "📅 重要事件",
    "emotion": "💭 情绪状态",
    "normal": "📝 日常"
}

CATEGORY_ORDER = ["fact", "preference", "event", "emotion", "normal"]


class MemoryEditDialog(QDialog):
    def __init__(self, parent=None, memory=None):
        super().__init__(parent)
        self.setWindowTitle("编辑记忆" if memory else "添加记忆")
        self.setMinimumWidth(450)
        self._memory = memory

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(BodyLabel("类别", self))
        self.category_combo = QComboBox(self)
        for key in CATEGORY_ORDER:
            self.category_combo.addItem(CATEGORY_MAP[key], key)
        layout.addWidget(self.category_combo)

        layout.addWidget(BodyLabel("记忆内容", self))
        self.content_edit = QTextEdit(self)
        self.content_edit.setPlaceholderText("输入记忆内容...")
        self.content_edit.setMinimumHeight(80)
        layout.addWidget(self.content_edit)

        layout.addWidget(BodyLabel("重要性 (1-5)", self))
        self.importance_spin = QSpinBox(self)
        self.importance_spin.setRange(1, 5)
        self.importance_spin.setValue(3)
        layout.addWidget(self.importance_spin)

        if memory:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == memory.get("category", "normal"):
                    self.category_combo.setCurrentIndex(i)
                    break
            self.content_edit.setPlainText(memory.get("content", ""))
            self.importance_spin.setValue(memory.get("importance", 3))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "category": self.category_combo.currentData(),
            "content": self.content_edit.toPlainText().strip(),
            "importance": self.importance_spin.value(),
        }


class MemoryInterface(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db if db else ChatDatabase()
        self.setObjectName("MemoryInterface")
        self.current_filter = None
        self._all_memories = []
        self.init_ui()
        self.load_memories()

    def update_theme(self):
        pass

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title = TitleLabel("记忆管理", self)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem("全部类别", None)
        for key in CATEGORY_ORDER:
            self.filter_combo.addItem(CATEGORY_MAP[key], key)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.filter_combo)

        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索记忆...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)
        header_layout.addWidget(self.search_input)

        main_layout.addLayout(header_layout)

        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["类别", "记忆内容", "重要性", "关键词", "创建时间"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)
        self.table.itemDoubleClicked.connect(self.on_double_click)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.add_btn = PrimaryPushButton(FluentIcon.ADD, "添加记忆", self)
        self.add_btn.clicked.connect(self.add_memory)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = PushButton(FluentIcon.EDIT, "编辑记忆", self)
        self.edit_btn.clicked.connect(self.edit_memory)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = PushButton(FluentIcon.DELETE, "删除记忆", self)
        self.delete_btn.clicked.connect(self.delete_memory)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.refresh_btn = PushButton(FluentIcon.SYNC, "刷新", self)
        self.refresh_btn.clicked.connect(self.load_memories)
        btn_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(btn_layout)

    def load_memories(self):
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT id, category, content, importance, keywords, created_at
                FROM user_memories
                ORDER BY importance DESC, created_at DESC
            """)
            self._all_memories = []
            for row in cursor.fetchall():
                self._all_memories.append({
                    "id": row[0],
                    "category": row[1],
                    "content": row[2],
                    "importance": row[3],
                    "keywords": json.loads(row[4]) if row[4] else [],
                    "created_at": row[5]
                })
            self._apply_filter()
        except Exception as e:
            InfoBar.error("错误", f"加载记忆失败：{e}", duration=3000, parent=self)

    def _apply_filter(self):
        self.table.setRowCount(0)
        text = self.search_input.text().strip().lower()
        category = self.filter_combo.currentData()

        filtered = []
        for m in self._all_memories:
            if category and m["category"] != category:
                continue
            if text:
                if text not in m["content"].lower() and text not in " ".join(m.get("keywords", [])).lower():
                    continue
            filtered.append(m)

        self.table.setRowCount(len(filtered))
        for i, m in enumerate(filtered):
            cat_text = CATEGORY_MAP.get(m["category"], m["category"])
            self.table.setItem(i, 0, QTableWidgetItem(cat_text))
            self.table.setItem(i, 1, QTableWidgetItem(m["content"]))

            stars = "★" * m["importance"] + "☆" * (5 - m["importance"])
            self.table.setItem(i, 2, QTableWidgetItem(stars))

            keywords_str = ", ".join(m.get("keywords", []))
            self.table.setItem(i, 3, QTableWidgetItem(keywords_str))

            self.table.setItem(i, 4, QTableWidgetItem(m.get("created_at", "")))

            for col in range(5):
                item = self.table.item(i, col)
                if item:
                    item.setData(Qt.UserRole, m)

    def get_selected_memory(self):
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        if len(rows) == 1:
            row = list(rows)[0]
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None

    def get_selected_memories(self):
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        memories = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                data = item.data(Qt.UserRole)
                if data:
                    memories.append(data)
        return memories

    def add_memory(self):
        dialog = MemoryEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["content"]:
                InfoBar.warning("提示", "记忆内容不能为空", duration=2000, parent=self)
                return
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    INSERT INTO user_memories (category, content, importance, keywords, original_content, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (data["category"], data["content"], data["importance"], json.dumps([]), data["content"]))
                self.db.conn.commit()
                InfoBar.success("成功", "记忆已添加", duration=2000, parent=self)
                self.load_memories()
            except Exception as e:
                InfoBar.error("错误", f"添加失败：{e}", duration=3000, parent=self)

    def edit_memory(self):
        memory = self.get_selected_memory()
        if not memory:
            InfoBar.warning("提示", "请先选择一条记忆", duration=2000, parent=self)
            return

        dialog = MemoryEditDialog(self, memory)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["content"]:
                InfoBar.warning("提示", "记忆内容不能为空", duration=2000, parent=self)
                return
            try:
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    UPDATE user_memories
                    SET category=?, content=?, importance=?, keywords=?, original_content=?
                    WHERE id=?
                """, (data["category"], data["content"], data["importance"],
                      json.dumps(memory.get("keywords", [])), data["content"], memory["id"]))
                self.db.conn.commit()
                InfoBar.success("成功", "记忆已更新", duration=2000, parent=self)
                self.load_memories()
            except Exception as e:
                InfoBar.error("错误", f"编辑失败：{e}", duration=3000, parent=self)

    def delete_memory(self):
        memories = self.get_selected_memories()
        if not memories:
            InfoBar.warning("提示", "请先选择要删除的记忆", duration=2000, parent=self)
            return

        count = len(memories)
        msg = f"确定要删除选中的 {count} 条记忆吗？" if count > 1 else "确定要删除这条记忆吗？"
        reply = QMessageBox.question(self, "确认删除", msg,
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            cursor = self.db.conn.cursor()
            for m in memories:
                cursor.execute("DELETE FROM user_memories WHERE id=?", (m["id"],))
            self.db.conn.commit()
            InfoBar.success("成功", f"已删除 {count} 条记忆", duration=2000, parent=self)
            self.load_memories()
        except Exception as e:
            InfoBar.error("错误", f"删除失败：{e}", duration=3000, parent=self)

    def on_filter_changed(self, index):
        self._apply_filter()

    def on_search_changed(self, text):
        self._apply_filter()

    def on_context_menu(self, pos):
        menu = QMenu(self)
        edit_action = menu.addAction(FluentIcon.EDIT.icon(), "编辑")
        delete_action = menu.addAction(FluentIcon.DELETE.icon(), "删除")
        menu.addSeparator()
        select_all_action = menu.addAction("全选")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == edit_action:
            self.edit_memory()
        elif action == delete_action:
            self.delete_memory()
        elif action == select_all_action:
            self.table.selectAll()

    def on_double_click(self, item):
        self.edit_memory()

    def delete_all_memories(self):
        reply = QMessageBox.warning(
            self, "确认清空", "确定要删除所有记忆吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM user_memories")
            self.db.conn.commit()
            InfoBar.success("成功", "所有记忆已清空", duration=2000, parent=self)
            self.load_memories()
        except Exception as e:
            InfoBar.error("错误", f"清空失败：{e}", duration=3000, parent=self)
