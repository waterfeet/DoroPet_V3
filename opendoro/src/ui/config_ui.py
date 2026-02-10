from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QListWidgetItem, QLineEdit
from PyQt5.QtCore import Qt, QSettings
from qfluentwidgets import (ScrollArea, ComboBox, LineEdit, StrongBodyLabel, 
                            TitleLabel, PushButton, FluentIcon, ListWidget, 
                            BodyLabel, PrimaryPushButton, isDarkTheme, SegmentedWidget)

class ConfigInterface(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("ConfigInterface")
        self.current_model_id = None
        self.current_mode = "LLM" # "LLM" or "TTS"
        
        # Check if we need to migrate from QSettings
        self.migrate_settings()
        
        self.init_ui()
        self.load_models()
        self.update_form_visibility()

    def migrate_settings(self):
        # Check if DB has models
        models = self.db.get_models()
        if not models:
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")
            
            if api_key:
                self.db.add_model("Default Model", "openai", api_key, base_url, model)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Panel: Model List ---
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(250)
            
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 20, 10, 20)
        left_layout.setSpacing(10)

        # Mode Switcher
        self.pivot = SegmentedWidget(self.left_panel)
        self.pivot.addItem("LLM", "LLM 模型")
        self.pivot.addItem("TTS", "TTS 语音")
        self.pivot.addItem("IMAGE", "AI 绘图")
        self.pivot.setCurrentItem("LLM")
        self.pivot.currentItemChanged.connect(self.switch_mode)
        left_layout.addWidget(self.pivot)

        left_layout.addWidget(StrongBodyLabel("模型列表", self.left_panel))

        self.model_list = ListWidget(self.left_panel)
        self.model_list.itemClicked.connect(self.on_model_selected)
        left_layout.addWidget(self.model_list)

        self.add_btn = PushButton(FluentIcon.ADD, "添加新模型", self.left_panel)
        self.add_btn.clicked.connect(self.create_new_model)
        left_layout.addWidget(self.add_btn)

        main_layout.addWidget(self.left_panel)

        # --- Right Panel: Edit Form ---
        right_panel = ScrollArea(self)
        right_panel.setWidgetResizable(True)
        right_panel.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.edit_widget = QWidget()
        right_layout = QVBoxLayout(self.edit_widget)
        right_layout.setContentsMargins(36, 36, 36, 36)
        right_layout.setSpacing(20)

        right_layout.addWidget(TitleLabel("模型配置", self.edit_widget))

        # 1. Configuration Name
        right_layout.addWidget(StrongBodyLabel("配置名称 (显示名)", self.edit_widget))
        self.name_input = LineEdit(self.edit_widget)
        self.name_input.setPlaceholderText("例如: 我的 DeepSeek")
        right_layout.addWidget(self.name_input)

        # 2. Provider Preset
        right_layout.addWidget(StrongBodyLabel("预设模版 (自动填充 URL)", self.edit_widget))
        self.provider_combo = ComboBox(self.edit_widget)
        self.provider_combo.addItems(["Custom (自定义)", "OpenAI", "DeepSeek", "Anthropic", "Ollama", "Moonshot (Kimi)"])
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        right_layout.addWidget(self.provider_combo)

        # 3. Model ID
        right_layout.addWidget(StrongBodyLabel("模型 ID (Model Name)", self.edit_widget))
        self.model_id_input = LineEdit(self.edit_widget)
        self.model_id_input.setPlaceholderText("例如: gpt-4, deepseek-chat")
        right_layout.addWidget(self.model_id_input)

        # 4. Voice (TTS only)
        self.voice_label = StrongBodyLabel("Voice (语音包名)", self.edit_widget)
        right_layout.addWidget(self.voice_label)
        self.voice_input = LineEdit(self.edit_widget)
        self.voice_input.setPlaceholderText("例如: fishaudio/fish-speech-1.5:alex")
        right_layout.addWidget(self.voice_input)

        # 5. API Key
        right_layout.addWidget(StrongBodyLabel("API Key", self.edit_widget))
        self.api_key_input = LineEdit(self.edit_widget)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        right_layout.addWidget(self.api_key_input)

        # 6. Base URL
        right_layout.addWidget(StrongBodyLabel("Base URL", self.edit_widget))
        self.base_url_input = LineEdit(self.edit_widget)
        self.base_url_input.setPlaceholderText("API 基础地址")
        right_layout.addWidget(self.base_url_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存修改", self.edit_widget)
        self.save_btn.clicked.connect(self.save_model)
        
        self.use_btn = PushButton(FluentIcon.ACCEPT, "启用此配置", self.edit_widget)
        self.use_btn.clicked.connect(self.set_active_model_handler)
        
        self.delete_btn = PushButton(FluentIcon.DELETE, "删除配置", self.edit_widget)
        self.delete_btn.clicked.connect(self.delete_model)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.use_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        right_layout.addLayout(btn_layout)
        right_layout.addStretch()

        right_panel.setWidget(self.edit_widget)
        main_layout.addWidget(right_panel)

        # Disable right panel initially
        self.edit_widget.setEnabled(False)
        
        self.update_theme()

    def switch_mode(self, item_key):
        self.current_mode = item_key
        self.create_new_model() # Reset form and selection
        self.edit_widget.setEnabled(False) # Disable form until selection
        self.load_models()
        self.update_form_visibility()

    def update_form_visibility(self):
        is_tts = (self.current_mode == "TTS")
        self.voice_label.setVisible(is_tts)
        self.voice_input.setVisible(is_tts)
        
        # Update provider options based on mode
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        if is_tts:
             self.provider_combo.addItems(["Custom (自定义)", "SiliconFlow"])
        elif self.current_mode == "IMAGE":
             self.provider_combo.addItems(["Custom (自定义)", "OpenAI (DALL-E)", "DeepSeek (Not Supported)", "SiliconFlow", "Gitee AI"])
        else:
             self.provider_combo.addItems(["Custom (自定义)", "OpenAI", "DeepSeek", "Anthropic", "Ollama", "Moonshot (Kimi)"])
        self.provider_combo.blockSignals(False)

    def load_models(self):
        self.model_list.clear()
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()
            
        for m in models:
            # m: id, name, provider, api_key, base_url, model_name, [voice], is_active
            # TTS has voice at index 6, is_active at 7
            # LLM/IMAGE has is_active at 6
            item = QListWidgetItem(m[1], self.model_list)
            item.setData(Qt.UserRole, m[0]) # ID
            self.model_list.addItem(item)
            
            is_active_idx = 7 if self.current_mode == "TTS" else 6
            if m[is_active_idx] == 1: # is_active
                self.model_list.setCurrentItem(item)
                self.on_model_selected(item)

    def on_model_selected(self, item):
        if not item: return
        self.edit_widget.setEnabled(True)
        model_id = item.data(Qt.UserRole)
        self.current_model_id = model_id
        
        # Find model data
        target = None
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()
            
        for m in models:
            if m[0] == model_id:
                target = m
                break
        
        if target:
            # Common fields: id(0), name(1), provider(2), api_key(3), base_url(4), model_name(5)
            self.name_input.setText(target[1])
            
            # Set combo box
            provider = target[2]
            if provider:
                index = self.provider_combo.findText(provider)
                if index == -1:
                    # Try partial match manually (case insensitive)
                    for i in range(self.provider_combo.count()):
                        if provider.lower() in self.provider_combo.itemText(i).lower():
                            index = i
                            break
                
                if index >= 0:
                    self.provider_combo.setCurrentIndex(index)
                else:
                    self.provider_combo.setCurrentIndex(0) # Custom
            else:
                 self.provider_combo.setCurrentIndex(0)
            
            if self.current_mode == "IMAGE":
                # IMAGE: base_url(3), api_key(4), model_name(5)
                self.base_url_input.setText(target[3])
                self.api_key_input.setText(target[4])
                self.model_id_input.setText(target[5])
            else:
                # LLM/TTS: api_key(3), base_url(4), model_name(5)
                self.api_key_input.setText(target[3])
                self.base_url_input.setText(target[4])
                self.model_id_input.setText(target[5])
            
            if self.current_mode == "TTS":
                # TTS has voice at index 6
                self.voice_input.setText(target[6])

    def create_new_model(self):
        self.model_list.clearSelection()
        self.edit_widget.setEnabled(True)
        self.current_model_id = None
        
        self.name_input.clear()
        self.provider_combo.setCurrentIndex(0)
        self.api_key_input.clear()
        self.base_url_input.clear()
        self.model_id_input.clear()
        self.voice_input.clear()
        self.name_input.setFocus()

    def on_provider_changed(self, index):
        text = self.provider_combo.currentText()
        if self.current_mode == "TTS":
            if "SiliconFlow" in text:
                self.base_url_input.setText("https://api.siliconflow.cn/v1")
                self.model_id_input.setText("fishaudio/fish-speech-1.5")
                self.voice_input.setText("fishaudio/fish-speech-1.5:alex")
        elif self.current_mode == "IMAGE":
            if "OpenAI" in text:
                self.base_url_input.setText("https://api.openai.com/v1")
                self.model_id_input.setText("dall-e-3")
            elif "SiliconFlow" in text:
                self.base_url_input.setText("https://api.siliconflow.cn/v1")
                self.model_id_input.setText("stabilityai/stable-diffusion-3-5-large")
            elif "Gitee AI" in text:
                self.base_url_input.setText("https://ai.gitee.com/v1")
                self.model_id_input.setText("Z-Image")
        else:
            if "OpenAI" in text:
                self.base_url_input.setText("https://api.openai.com/v1")
                self.model_id_input.setText("gpt-3.5-turbo")
            elif "DeepSeek" in text:
                self.base_url_input.setText("https://api.deepseek.com")
                self.model_id_input.setText("deepseek-chat")
            elif "Anthropic" in text:
                self.base_url_input.setText("https://api.anthropic.com/v1")
                self.model_id_input.setText("claude-3-opus-20240229")
            elif "Ollama" in text:
                self.base_url_input.setText("http://localhost:11434/v1")
                self.model_id_input.setText("llama3")
            elif "Moonshot" in text:
                self.base_url_input.setText("https://api.moonshot.cn/v1")
                self.model_id_input.setText("moonshot-v1-8k")

    def save_model(self):
        name = self.name_input.text().strip()
        if not name:
            name = "Unnamed Model"
            
        provider = self.provider_combo.currentText()
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model_name = self.model_id_input.text().strip()
        
        if self.current_mode == "TTS":
            voice = self.voice_input.text().strip()
            if self.current_model_id:
                self.db.update_tts_model(self.current_model_id, name, provider, api_key, base_url, model_name, voice)
            else:
                self.current_model_id = self.db.add_tts_model(name, provider, api_key, base_url, model_name, voice)
        elif self.current_mode == "IMAGE":
            if self.current_model_id:
                self.db.update_image_model(self.current_model_id, name, provider, base_url, api_key, model_name)
            else:
                self.current_model_id = self.db.add_image_model(name, provider, base_url, api_key, model_name)
        else:
            if self.current_model_id:
                self.db.update_model(self.current_model_id, name, provider, api_key, base_url, model_name)
            else:
                self.current_model_id = self.db.add_model(name, provider, api_key, base_url, model_name)
            
        self.load_models()

    def delete_model(self):
        if self.current_model_id:
            if self.current_mode == "TTS":
                self.db.delete_tts_model(self.current_model_id)
            elif self.current_mode == "IMAGE":
                self.db.delete_image_model(self.current_model_id)
            else:
                self.db.delete_model(self.current_model_id)
            self.create_new_model()
            self.load_models()

    def set_active_model_handler(self):
        if not self.current_model_id:
            return

        if self.current_mode == "TTS":
            self.db.set_active_tts_model(self.current_model_id)
            QMessageBox.information(self, "成功", "已启用该语音配置")
        elif self.current_mode == "IMAGE":
            self.db.set_active_image_model(self.current_model_id)
            QMessageBox.information(self, "成功", "已启用该绘图配置")
        else:
            self.db.set_active_model(self.current_model_id)
            QMessageBox.information(self, "成功", "已启用该模型配置")
            
        self.load_models()

    def update_theme(self):
        if isDarkTheme():
            # Main Window Background
            self.setStyleSheet("background-color: #272727; color: white;")
            
            self.left_panel.setStyleSheet("background-color: rgba(255, 255, 255, 0.03); border-right: 1px solid #333333;")
            self.model_list.setStyleSheet("""
                QListWidget {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    height: 36px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    color: #ffffff;
                    margin: 2px 4px;
                }
                QListWidget::item:hover {
                    background-color: rgba(255, 255, 255, 0.04);
                }
                QListWidget::item:selected {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #ffffff;
                }
                QListWidget::item:selected:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                }
            """)
            
            # Input fields style for Dark Mode
            input_style = """
                QLineEdit {
                    color: white;
                    background-color: #333333;
                    border: 1px solid #454545;
                    border-radius: 4px;
                    padding: 5px;
                }
                QLineEdit:hover { background-color: #383838; }
                QLineEdit:focus { border: 1px solid #4cc2ff; background-color: #2b2b2b; }
            """
            self.name_input.setStyleSheet(input_style)
            self.model_id_input.setStyleSheet(input_style)
            self.api_key_input.setStyleSheet(input_style)
            self.base_url_input.setStyleSheet(input_style)
            self.voice_input.setStyleSheet(input_style)
            
            # Combo Box
            self.provider_combo.setStyleSheet("""
                QComboBox {
                    background-color: #333333;
                    border: 1px solid #454545;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: white;
                }
                QComboBox:hover { background-color: #383838; }
                QComboBox::drop-down { border: none; width: 20px; }
                QComboBox QAbstractItemView {
                    background-color: #2b2b2b;
                    border: 1px solid #454545;
                    color: white;
                }
            """)
        else:
            # Main Window Background
            self.setStyleSheet("background-color: #f9f9f9; color: black;")
            
            self.left_panel.setStyleSheet("background-color: rgba(255, 255, 255, 0.5); border-right: 1px solid #E0E0E0;")
            self.model_list.setStyleSheet("""
                QListWidget {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    height: 36px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    color: black;
                    margin: 2px 4px;
                }
                QListWidget::item:hover {
                    background-color: rgba(0, 0, 0, 0.04);
                }
                QListWidget::item:selected {
                    background-color: rgba(0, 0, 0, 0.08);
                    color: black;
                }
                QListWidget::item:selected:hover {
                    background-color: rgba(0, 0, 0, 0.12);
                }
            """)
            
            # Input fields style for Light Mode
            input_style = """
                QLineEdit {
                    color: black;
                    background-color: white;
                    border: 1px solid #e5e5e5;
                    border-radius: 4px;
                    padding: 5px;
                }
                QLineEdit:hover { background-color: #fdfdfd; }
                QLineEdit:focus { border: 1px solid #0078d4; background-color: white; }
            """
            self.name_input.setStyleSheet(input_style)
            self.model_id_input.setStyleSheet(input_style)
            self.api_key_input.setStyleSheet(input_style)
            self.base_url_input.setStyleSheet(input_style)
            self.voice_input.setStyleSheet(input_style)
            
            # Combo Box
            self.provider_combo.setStyleSheet("""
                QComboBox {
                    background-color: white;
                    border: 1px solid #e5e5e5;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: black;
                }
                QComboBox:hover { background-color: #fdfdfd; }
                QComboBox::drop-down { border: none; width: 20px; }
                QComboBox QAbstractItemView {
                    background-color: white;
                    border: 1px solid #e5e5e5;
                    color: black;
                }
            """)
