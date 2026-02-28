from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem, QFrame
from PyQt5.QtCore import Qt
from qfluentwidgets import (ScrollArea, PlainTextEdit, PrimaryPushButton, PushButton,
                            TitleLabel, BodyLabel, FluentIcon, LineEdit, ListWidget, MessageBox,
                            StrongBodyLabel, isDarkTheme, CheckBox)
from src.core.database import ChatDatabase

class PromptInterface(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db if db else ChatDatabase()
        self.current_persona_id = None
        
        self.setObjectName("PromptInterface")
        self.init_ui()
        self.load_personas()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Panel: Persona List ---
        self.left_panel = QWidget()
        self.left_panel.setObjectName("promptLeftPanel")
        self.left_panel.setFixedWidth(250)
        
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 20, 10, 20)
        left_layout.setSpacing(10)

        left_title = StrongBodyLabel("角色列表", self.left_panel)
        left_layout.addWidget(left_title)

        self.persona_list = ListWidget(self.left_panel)
        self.persona_list.setObjectName("personaList")
        self.persona_list.itemClicked.connect(self.on_persona_selected)
        left_layout.addWidget(self.persona_list)

        self.add_btn = PushButton(FluentIcon.ADD, "新建角色", self.left_panel)
        self.add_btn.clicked.connect(self.create_new_persona)
        left_layout.addWidget(self.add_btn)

        main_layout.addWidget(self.left_panel)

        # --- Right Panel: Edit Details ---
        right_panel = ScrollArea(self)
        right_panel.setWidgetResizable(True)
        # right_panel.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.edit_widget = QWidget()
        self.edit_widget.setObjectName("promptEditWidget")
        right_layout = QVBoxLayout(self.edit_widget)
        right_layout.setContentsMargins(36, 36, 36, 36)
        right_layout.setSpacing(20)

        # Title
        title_label = TitleLabel("编辑角色详情", self.edit_widget)
        right_layout.addWidget(title_label)

        # Name Input
        right_layout.addWidget(BodyLabel("角色名称", self.edit_widget))
        self.name_input = LineEdit(self.edit_widget)
        self.name_input.setObjectName("promptNameInput")
        self.name_input.setPlaceholderText("例如：傲娇猫娘")
        right_layout.addWidget(self.name_input)

        # Description Input
        right_layout.addWidget(BodyLabel("简短描述", self.edit_widget))
        self.desc_input = LineEdit(self.edit_widget)
        self.desc_input.setObjectName("promptDescInput")
        self.desc_input.setPlaceholderText("例如：一只性格傲娇的可爱猫娘...")
        right_layout.addWidget(self.desc_input)

        # System Prompt Input
        right_layout.addWidget(BodyLabel("系统提示词 (System Prompt)", self.edit_widget))
        self.prompt_edit = PlainTextEdit(self.edit_widget)
        self.prompt_edit.setObjectName("promptContentEdit")
        self.prompt_edit.setPlaceholderText("在这里定义角色的详细性格、说话方式等...")
        self.prompt_edit.setMinimumHeight(300)
        right_layout.addWidget(self.prompt_edit)
        
        # Doro Tools Option
        self.doro_tools_checkbox = CheckBox("启用 Doro 表情和属性工具", self.edit_widget)
        self.doro_tools_checkbox.setToolTip("启用后，AI 可以调用 set_expression 和 modify_pet_attribute 工具")
        right_layout.addWidget(self.doro_tools_checkbox)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存修改", self.edit_widget)
        self.save_btn.clicked.connect(self.save_persona)
        
        self.delete_btn = PushButton(FluentIcon.DELETE, "删除角色", self.edit_widget)
        self.delete_btn.setObjectName("promptDeleteBtn")
        self.delete_btn.clicked.connect(self.delete_persona)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        right_panel.setWidget(self.edit_widget)
        main_layout.addWidget(right_panel)
        
        # self.update_theme()

    def load_personas(self):
        self.persona_list.clear()
        personas = self.db.get_personas()
        for p in personas:
            p_id, name, desc, prompt, avatar, enable_doro_tools = p
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, p_id)
            item.setData(Qt.UserRole + 1, desc)
            item.setData(Qt.UserRole + 2, prompt)
            item.setData(Qt.UserRole + 3, bool(enable_doro_tools))
            self.persona_list.addItem(item)
        
        if not personas:
            self.clear_inputs()
            self.current_persona_id = None

    def on_persona_selected(self, item):
        self.current_persona_id = item.data(Qt.UserRole)
        self.name_input.setText(item.text())
        self.desc_input.setText(item.data(Qt.UserRole + 1))
        self.prompt_edit.setPlainText(item.data(Qt.UserRole + 2))
        self.doro_tools_checkbox.setChecked(item.data(Qt.UserRole + 3) or False)

    def create_new_persona(self):
        # Create a default new persona in DB immediately or just clear inputs?
        # Better to just clear inputs and set current_id to None, act as "New"
        # But to show in list, we usually add it first.
        # Let's just clear inputs for a "New" state.
        self.persona_list.clearSelection()
        self.clear_inputs()
        self.current_persona_id = None
        self.name_input.setFocus()

    def clear_inputs(self):
        self.name_input.clear()
        self.desc_input.clear()
        self.prompt_edit.clear()
        self.doro_tools_checkbox.setChecked(False)

    def save_persona(self):
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        enable_doro_tools = self.doro_tools_checkbox.isChecked()
        
        if not name:
            MessageBox("错误", "角色名称不能为空", self).exec_()
            return

        if self.current_persona_id:
            self.db.update_persona(self.current_persona_id, name, desc, prompt, enable_doro_tools=enable_doro_tools)
            MessageBox("成功", "角色已更新", self).exec_()
        else:
            new_id = self.db.add_persona(name, desc, prompt, enable_doro_tools=enable_doro_tools)
            self.current_persona_id = new_id
            MessageBox("成功", "新角色已创建", self).exec_()
        
        self.load_personas()
        # Reselect the saved item
        for i in range(self.persona_list.count()):
            item = self.persona_list.item(i)
            if item.data(Qt.UserRole) == self.current_persona_id:
                self.persona_list.setCurrentItem(item)
                break

    def delete_persona(self, checked=False): # checked is ignored
        if not self.current_persona_id:
            return
            
        w = MessageBox("确认删除", "确定要删除这个角色吗？此操作无法撤销。", self)
        if w.exec_():
            self.db.delete_persona(self.current_persona_id)
            self.load_personas()
            self.create_new_persona()

    def update_theme(self):
        pass
        # Theme handling is now done via global QSS
        # All inline styles have been migrated to light.qss and dark.qss
