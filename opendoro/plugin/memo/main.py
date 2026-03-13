# -*- coding: utf-8 -*-
"""
备忘录插件 - DoroPet
功能：创建、编辑、删除、搜索备忘录，支持分类和标签管理
"""

import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QStackedWidget, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

from qfluentwidgets import (
    CardWidget, TitleLabel, SubtitleLabel, BodyLabel,
    StrongBodyLabel, PushButton, PrimaryPushButton, LineEdit,
    TextEdit, Pivot, IconWidget, FluentIcon, isDarkTheme,
    ComboBox, MessageBoxBase, SubtitleLabel as DialogTitleLabel,
    MessageBox
)


class Plugin(QWidget):
    """备忘录插件入口"""
    
    name = "备忘录"  # 导航栏显示名称
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.memo_data_file = os.path.join(os.path.dirname(__file__), "memo_data.json")
        self.memos = []  # 存储备忘录数据
        self.load_memos()  # 加载备忘录数据
        self.initUI()
    
    def initUI(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 主容器
        container = CardWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(16)
        
        # 标题区域
        header_layout = QHBoxLayout()
        title = TitleLabel("📝 备忘录")
        title.setTextColor(QColor(3, 120, 212), QColor(3, 120, 212))
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 统计信息
        self.stats_label = BodyLabel("")
        self.update_stats()
        header_layout.addWidget(self.stats_label)
        
        container_layout.addLayout(header_layout)
        
        # 搜索栏
        search_card = CardWidget()
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(12, 8, 12, 8)
        
        search_icon = IconWidget(FluentIcon.SEARCH)
        search_icon.setFixedSize(20, 20)
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("搜索备忘录...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.search_memos)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        container_layout.addWidget(search_card)
        
        # Pivot 切换器
        self.pivot = Pivot(self)
        self.pivot.setFixedHeight(40)
        self.pivot.addItem(routeKey="all", text="📋 全部", onClick=lambda: self.filter_memos("all"))
        self.pivot.addItem(routeKey="work", text="💼 工作", onClick=lambda: self.filter_memos("work"))
        self.pivot.addItem(routeKey="life", text="🏠 生活", onClick=lambda: self.filter_memos("life"))
        self.pivot.addItem(routeKey="study", text="📚 学习", onClick=lambda: self.filter_memos("study"))
        self.pivot.addItem(routeKey="other", text="📁 其他", onClick=lambda: self.filter_memos("other"))
        container_layout.addWidget(self.pivot)
        
        # 备忘录列表容器
        self.memo_list_widget = QWidget()
        self.memo_list_layout = QVBoxLayout(self.memo_list_widget)
        self.memo_list_layout.setContentsMargins(0, 0, 0, 0)
        self.memo_list_layout.setSpacing(8)
        
        container_layout.addWidget(self.memo_list_widget)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.add_btn = PrimaryPushButton("➕ 新建备忘录")
        self.add_btn.setFixedHeight(40)
        self.add_btn.clicked.connect(self.create_memo)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addStretch()
        
        container_layout.addLayout(button_layout)
        
        layout.addWidget(container)
        
        # 默认显示全部
        self.current_filter = "all"
        self.refresh_memo_list()
    
    def update_stats(self):
        """更新统计信息"""
        total = len(self.memos)
        self.stats_label.setText(f"共 {total} 条备忘录")
        self.stats_label.setTextColor(QColor(96, 96, 96), QColor(208, 208, 208))
    
    def load_memos(self):
        """从文件加载备忘录数据"""
        try:
            if os.path.exists(self.memo_data_file):
                with open(self.memo_data_file, 'r', encoding='utf-8') as f:
                    self.memos = json.load(f)
            else:
                # 添加一些示例备忘录
                self.memos = [
                    {
                        "id": 1,
                        "title": "欢迎使用备忘录",
                        "content": "这是一个功能强大的备忘录插件，支持创建、编辑、删除、搜索和分类功能。",
                        "category": "other",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "id": 2,
                        "title": "完成项目报告",
                        "content": "需要在周五之前完成第三季度的项目总结报告。",
                        "category": "work",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "id": 3,
                        "title": "购买生活用品",
                        "content": "牛奶、面包、鸡蛋、蔬菜、水果",
                        "category": "life",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                ]
                self.save_memos()
        except Exception as e:
            print(f"加载备忘录数据失败: {e}")
            self.memos = []
    
    def save_memos(self):
        """保存备忘录数据到文件"""
        try:
            with open(self.memo_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.memos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存备忘录数据失败: {e}")
    
    def get_filtered_memos(self):
        """获取过滤后的备忘录列表"""
        filtered = self.memos
        
        # 按分类过滤
        if self.current_filter != "all":
            filtered = [m for m in filtered if m.get("category") == self.current_filter]
        
        # 按搜索关键词过滤
        search_text = self.search_input.text().strip().lower()
        if search_text:
            filtered = [
                m for m in filtered 
                if search_text in m.get("title", "").lower() 
                or search_text in m.get("content", "").lower()
            ]
        
        # 按更新时间倒序排列
        filtered.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return filtered
    
    def refresh_memo_list(self):
        """刷新备忘录列表显示"""
        # 清空现有列表
        while self.memo_list_layout.count():
            item = self.memo_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取过滤后的备忘录
        filtered_memos = self.get_filtered_memos()
        
        if not filtered_memos:
            # 显示空状态
            empty_label = StrongBodyLabel("暂无备忘录")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
            self.memo_list_layout.addWidget(empty_label)
            self.memo_list_layout.addStretch()
        else:
            # 显示备忘录卡片
            for memo in filtered_memos:
                memo_card = MemoCard(memo, self)
                self.memo_list_layout.addWidget(memo_card)
            
            self.memo_list_layout.addStretch()
        
        self.update_stats()
    
    def search_memos(self):
        """搜索备忘录"""
        self.refresh_memo_list()
    
    def filter_memos(self, category):
        """过滤备忘录"""
        self.current_filter = category
        self.refresh_memo_list()
    
    def create_memo(self):
        """创建新备忘录"""
        dialog = MemoEditDialog(self)
        if dialog.exec():
            memo_data = dialog.get_memo_data()
            memo_data["id"] = max([m["id"] for m in self.memos], default=0) + 1
            memo_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            memo_data["updated_at"] = memo_data["created_at"]
            
            self.memos.append(memo_data)
            self.save_memos()
            self.refresh_memo_list()
            
            # 显示成功提示
            self.show_success_message("创建成功", "备忘录已成功创建")
    
    def edit_memo(self, memo_id):
        """编辑备忘录"""
        memo = next((m for m in self.memos if m["id"] == memo_id), None)
        if memo:
            dialog = MemoEditDialog(self, memo)
            if dialog.exec():
                updated_data = dialog.get_memo_data()
                memo.update(updated_data)
                memo["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                self.save_memos()
                self.refresh_memo_list()
                self.show_success_message("更新成功", "备忘录已成功更新")
    
    def delete_memo(self, memo_id):
        """删除备忘录"""
        memo = next((m for m in self.memos if m["id"] == memo_id), None)
        if not memo:
            return
        
        # 使用Fluent风格的确认对话框
        message_box = MessageBox(
            "确认删除",
            f"确定要删除备忘录「{memo.get('title', '')}」吗？\n此操作无法撤销。",
            self
        )
        message_box.yesButton.setText("删除")
        message_box.cancelButton.setText("取消")
        
        if message_box.exec():
            self.memos = [m for m in self.memos if m["id"] != memo_id]
            self.save_memos()
            self.refresh_memo_list()
            self.show_success_message("删除成功", "备忘录已成功删除")
    
    def show_success_message(self, title, message):
        """显示成功提示消息"""
        message_box = MessageBox(title, message, self)
        message_box.cancelButton.hide()
        message_box.yesButton.setText("确定")
        
        # 自动关闭
        QTimer.singleShot(1500, message_box.close)
        message_box.exec()


class MemoCard(CardWidget):
    """备忘录卡片组件"""
    
    # 分类图标和颜色映射
    CATEGORY_CONFIG = {
        "work": {"icon": "💼", "name": "工作", "color": QColor(59, 130, 246)},
        "life": {"icon": "🏠", "name": "生活", "color": QColor(16, 185, 129)},
        "study": {"icon": "📚", "name": "学习", "color": QColor(245, 158, 11)},
        "other": {"icon": "📁", "name": "其他", "color": QColor(139, 92, 246)}
    }
    
    def __init__(self, memo_data, parent_plugin):
        super().__init__()
        self.memo_data = memo_data
        self.parent_plugin = parent_plugin
        self.initUI()
    
    def initUI(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # 顶部：标题和分类
        header_layout = QHBoxLayout()
        
        # 标题
        title = StrongBodyLabel(self.memo_data.get("title", "无标题"))
        title.setWordWrap(True)
        header_layout.addWidget(title, 1)
        
        # 分类标签
        category = self.memo_data.get("category", "other")
        cat_config = self.CATEGORY_CONFIG.get(category, self.CATEGORY_CONFIG["other"])
        
        category_label = BodyLabel(f"{cat_config['icon']} {cat_config['name']}")
        category_label.setTextColor(cat_config['color'], cat_config['color'])
        header_layout.addWidget(category_label)
        
        layout.addLayout(header_layout)
        
        # 内容
        content = BodyLabel(self.memo_data.get("content", ""))
        content.setWordWrap(True)
        content.setTextColor(QColor(96, 96, 96), QColor(208, 208, 208))
        content.setMaximumHeight(60)  # 限制高度
        layout.addWidget(content)
        
        # 底部：时间和操作按钮
        footer_layout = QHBoxLayout()
        
        # 时间信息
        updated_at = self.memo_data.get("updated_at", "")
        time_label = BodyLabel(f"更新于: {updated_at}")
        time_label.setTextColor(QColor(128, 128, 128), QColor(160, 160, 160))
        footer_layout.addWidget(time_label)
        
        footer_layout.addStretch()
        
        # 编辑按钮
        edit_btn = PushButton("编辑")
        edit_btn.setFixedSize(60, 28)
        edit_btn.clicked.connect(lambda: self.parent_plugin.edit_memo(self.memo_data["id"]))
        footer_layout.addWidget(edit_btn)
        
        # 删除按钮
        delete_btn = PushButton("删除")
        delete_btn.setFixedSize(60, 28)
        delete_btn.clicked.connect(lambda: self.parent_plugin.delete_memo(self.memo_data["id"]))
        footer_layout.addWidget(delete_btn)
        
        layout.addLayout(footer_layout)


class MemoEditDialog(MessageBoxBase):
    """备忘录编辑对话框 - Fluent风格"""
    
    def __init__(self, parent=None, memo_data=None):
        self.memo_data = memo_data or {}
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        """初始化界面"""
        # 标题
        self.titleLabel = DialogTitleLabel(
            "编辑备忘录" if self.memo_data else "新建备忘录", 
            self
        )
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题输入
        title_section = QVBoxLayout()
        title_section.setSpacing(8)
        
        title_label = StrongBodyLabel("标题")
        self.title_input = LineEdit()
        self.title_input.setText(self.memo_data.get("title", ""))
        self.title_input.setPlaceholderText("请输入备忘录标题")
        self.title_input.setFixedHeight(36)
        
        title_section.addWidget(title_label)
        title_section.addWidget(self.title_input)
        content_layout.addLayout(title_section)
        
        # 分类选择
        category_section = QVBoxLayout()
        category_section.setSpacing(8)
        
        category_label = StrongBodyLabel("分类")
        self.category_combo = ComboBox()
        self.category_combo.addItems(["💼 工作", "🏠 生活", "📚 学习", "📁 其他"])
        self.category_combo.setFixedHeight(36)
        self.category_combo.setPlaceholderText("选择分类")
        
        # 设置当前分类
        category_map = {"work": 0, "life": 1, "study": 2, "other": 3}
        current_category = self.memo_data.get("category", "other")
        self.category_combo.setCurrentIndex(category_map.get(current_category, 3))
        
        category_section.addWidget(category_label)
        category_section.addWidget(self.category_combo)
        content_layout.addLayout(category_section)
        
        # 内容输入
        content_section = QVBoxLayout()
        content_section.setSpacing(8)
        
        content_label = StrongBodyLabel("内容")
        self.content_input = TextEdit()
        self.content_input.setPlainText(self.memo_data.get("content", ""))
        self.content_input.setPlaceholderText("请输入备忘录内容...")
        self.content_input.setFixedHeight(180)
        
        content_section.addWidget(content_label)
        content_section.addWidget(self.content_input)
        content_layout.addLayout(content_section)
        
        # 添加到对话框布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        self.viewLayout.addWidget(content_widget)
        
        # 设置按钮文本
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        
        # 设置对话框最小宽度
        self.widget.setMinimumWidth(500)
    
    def get_memo_data(self):
        """获取备忘录数据"""
        category_map = {0: "work", 1: "life", 2: "study", 3: "other"}
        
        return {
            "title": self.title_input.text().strip() or "无标题",
            "content": self.content_input.toPlainText().strip(),
            "category": category_map[self.category_combo.currentIndex()]
        }


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # 设置深色主题
    from qfluentwidgets import setTheme, Theme
    setTheme(Theme.DARK)
    
    window = Plugin()
    window.resize(600, 700)
    window.setWindowTitle("备忘录")
    window.show()
    
    sys.exit(app.exec_())
