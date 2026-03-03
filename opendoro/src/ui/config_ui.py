from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, 
                             QListWidgetItem, QLineEdit, QDialog, QLabel, 
                             QListWidget as QtListWidget, QDialogButtonBox, 
                             QApplication, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QFont
from qfluentwidgets import (ScrollArea, ComboBox, LineEdit, StrongBodyLabel, 
                            TitleLabel, PushButton, FluentIcon, ListWidget, 
                            BodyLabel, PrimaryPushButton, isDarkTheme, 
                            SegmentedWidget, CheckBox, InfoBar, InfoBarPosition,
                            ToolButton, CardWidget, SubtitleLabel, CaptionLabel,
                            TransparentToolButton, HyperlinkLabel, ExpandLayout,
                            ExpandGroupSettingCard, SettingCardGroup, MessageBox)

from src.provider.register import (
    provider_registry, provider_cls_map, 
    get_all_providers_by_type, get_provider_metadata
)
from src.provider.entities import ProviderType, ProviderConfig
from src.provider.manager import ProviderManager


PROVIDER_HELP_INFO = {
    "openai_chat_completion": {
        "name": "OpenAI",
        "api_key_url": "https://platform.openai.com/api-keys",
        "doc_url": "https://platform.openai.com/docs",
        "desc": "ChatGPT 的官方 API 服务"
    },
    "deepseek_chat_completion": {
        "name": "DeepSeek",
        "api_key_url": "https://platform.deepseek.com/api_keys",
        "doc_url": "https://platform.deepseek.com/docs",
        "desc": "国产大模型，性价比高"
    },
    "anthropic_chat_completion": {
        "name": "Anthropic (Claude)",
        "api_key_url": "https://console.anthropic.com/settings/keys",
        "doc_url": "https://docs.anthropic.com",
        "desc": "Claude 系列模型的官方 API"
    },
    "gemini_chat_completion": {
        "name": "Google Gemini",
        "api_key_url": "https://aistudio.google.com/app/apikey",
        "doc_url": "https://ai.google.dev/docs",
        "desc": "Google 的多模态大模型"
    },
    "moonshot_chat_completion": {
        "name": "Moonshot (Kimi)",
        "api_key_url": "https://platform.moonshot.cn/console/api-keys",
        "doc_url": "https://platform.moonshot.cn/docs",
        "desc": "长文本处理能力强"
    },
    "zhipu_chat_completion": {
        "name": "智谱 AI",
        "api_key_url": "https://open.bigmodel.cn/usercenter/apikeys",
        "doc_url": "https://open.bigmodel.cn/dev/api",
        "desc": "国产 GLM 系列大模型"
    },
    "groq_chat_completion": {
        "name": "Groq",
        "api_key_url": "https://console.groq.com/keys",
        "doc_url": "https://console.groq.com/docs",
        "desc": "超快推理速度"
    },
    "ollama_chat_completion": {
        "name": "Ollama (本地)",
        "api_key_url": "",
        "doc_url": "https://ollama.ai",
        "desc": "本地运行，无需联网"
    },
    "edge_tts": {
        "name": "Edge TTS",
        "api_key_url": "",
        "doc_url": "",
        "desc": "微软免费语音合成"
    },
    "openai_tts": {
        "name": "OpenAI TTS",
        "api_key_url": "https://platform.openai.com/api-keys",
        "doc_url": "https://platform.openai.com/docs",
        "desc": "OpenAI 语音合成服务"
    },
    "openai_image": {
        "name": "OpenAI Image",
        "api_key_url": "https://platform.openai.com/api-keys",
        "doc_url": "https://platform.openai.com/docs",
        "desc": "DALL-E 图像生成"
    }
}


class HelpLabel(QWidget):
    def __init__(self, text: str, help_text: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.label = BodyLabel(text, self)
        layout.addWidget(self.label)
        
        if help_text:
            self.help_btn = ToolButton(FluentIcon.HELP, self)
            self.help_btn.setFixedSize(16, 16)
            self.help_btn.setToolTip(help_text)
            self.help_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
            layout.addWidget(self.help_btn)


class FormField(QWidget):
    def __init__(self, label: str, widget, help_text: str = "", 
                 link_text: str = "", link_url: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("formField")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(4)
        
        self.label = BodyLabel(label, self)
        label_layout.addWidget(self.label)
        
        if help_text:
            help_btn = ToolButton(FluentIcon.HELP, self)
            help_btn.setFixedSize(16, 16)
            help_btn.setToolTip(help_text)
            help_btn.setStyleSheet("QToolButton { border: none; background: transparent; opacity: 0.6; }")
            label_layout.addWidget(help_btn)
        
        if link_text and link_url:
            link = HyperlinkLabel(self)
            link.setUrl(link_url)
            link.setText(link_text)
            link.setStyleSheet("font-size: 12px;")
            label_layout.addWidget(link)
        
        label_layout.addStretch()
        layout.addLayout(label_layout)
        
        self.widget = widget
        layout.addWidget(widget)
    
    def set_visible(self, visible: bool):
        self.setVisible(visible)


class SettingCard(CardWidget):
    def __init__(self, title: str, icon: FluentIcon = None, parent=None):
        super().__init__(parent)
        self.setObjectName("settingCard")
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        if icon:
            icon_label = ToolButton(icon, self)
            icon_label.setFixedSize(20, 20)
            icon_label.setStyleSheet("QToolButton { border: none; background: transparent; }")
            header_layout.addWidget(icon_label)
        
        self.title_label = SubtitleLabel(title, self)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self._layout.addLayout(header_layout)
        
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        
        self._layout.addWidget(self.content_widget)
    
    def add_field(self, field: FormField):
        self.content_layout.addWidget(field)
    
    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


class CollapsibleCard(CardWidget):
    toggled = pyqtSignal(bool)
    
    def __init__(self, title: str, icon: FluentIcon = None, collapsed: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsibleCard")
        self._collapsed = collapsed
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 12, 20, 12)
        self._layout.setSpacing(0)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        if icon:
            icon_label = ToolButton(icon, self)
            icon_label.setFixedSize(18, 18)
            icon_label.setStyleSheet("QToolButton { border: none; background: transparent; }")
            header_layout.addWidget(icon_label)
        
        self.title_label = BodyLabel(title, self)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.toggle_btn = ToolButton(FluentIcon.CHEVRON_DOWN_MED, self)
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self.toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self.toggle_btn)
        
        self._layout.addLayout(header_layout)
        
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 12, 0, 0)
        self.content_layout.setSpacing(12)
        
        self._layout.addWidget(self.content_widget)
        
        if collapsed:
            self.content_widget.setVisible(False)
            self.toggle_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED)
    
    def _toggle(self):
        self._collapsed = not self._collapsed
        self.content_widget.setVisible(not self._collapsed)
        self.toggle_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED if self._collapsed else FluentIcon.CHEVRON_DOWN_MED)
        self.toggled.emit(not self._collapsed)
    
    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        self.content_layout.addLayout(layout)
    
    def set_collapsed(self, collapsed: bool):
        if self._collapsed != collapsed:
            self._toggle()
    
    def is_collapsed(self):
        return self._collapsed


class ModelSelectDialog(QDialog):
    def __init__(self, items: list, title: str = "选择模型", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        self.selected_model = None
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("从列表中选择:"))
        
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索...")
        self.search_input.textChanged.connect(self.filter_models)
        layout.addWidget(self.search_input)
        
        self.model_list = QtListWidget(self)
        self.model_list.addItems(items)
        self.model_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.model_list)
        
        self.all_items = items
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def filter_models(self, text: str):
        self.model_list.clear()
        filtered = [m for m in self.all_items if text.lower() in m.lower()]
        self.model_list.addItems(filtered)
    
    def accept(self):
        current_item = self.model_list.currentItem()
        if current_item:
            self.selected_model = current_item.text()
        super().accept()


class QuickAddDialog(QDialog):
    def __init__(self, providers: list, mode: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快速添加配置")
        self.setMinimumWidth(500)
        self.selected_provider = None
        self.api_key = ""
        self.providers = providers
        self.mode = mode
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        layout.addWidget(SubtitleLabel("选择 AI 平台", self))
        
        hint_label = CaptionLabel("选择平台后，只需填入 API 密钥即可完成配置", self)
        hint_label.setStyleSheet("color: gray;")
        layout.addWidget(hint_label)
        
        provider_grid = QWidget(self)
        grid_layout = QVBoxLayout(provider_grid)
        grid_layout.setSpacing(8)
        
        self.provider_buttons = []
        for p in self.providers:
            btn = PushButton(p["display_name"], provider_grid)
            btn.setFixedHeight(40)
            btn.setToolTip(p.get("desc", ""))
            btn.clicked.connect(lambda checked, provider=p: self._select_provider(provider))
            self.provider_buttons.append((btn, p))
            grid_layout.addWidget(btn)
        
        layout.addWidget(provider_grid)
        
        self.api_section = QWidget(self)
        api_layout = QVBoxLayout(self.api_section)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(8)
        
        self.api_label = BodyLabel("API 密钥", self)
        api_layout.addWidget(self.api_label)
        
        self.api_input = LineEdit(self)
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText("粘贴您的 API Key...")
        api_layout.addWidget(self.api_input)
        
        self.help_link = HyperlinkLabel(self)
        self.help_link.setText("如何获取?")
        api_layout.addWidget(self.help_link)
        
        self.api_section.setVisible(False)
        layout.addWidget(self.api_section)
        
        self.name_section = QWidget(self)
        name_layout = QVBoxLayout(self.name_section)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        
        name_layout.addWidget(BodyLabel("配置名称 (可选)", self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("默认使用平台名称")
        name_layout.addWidget(self.name_input)
        
        self.name_section.setVisible(False)
        layout.addWidget(self.name_section)
        
        layout.addStretch()
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _select_provider(self, provider: dict):
        self.selected_provider = provider
        
        for btn, p in self.provider_buttons:
            if p == provider:
                btn.setStyleSheet("QPushButton { background-color: #0078d4; color: white; }")
            else:
                btn.setStyleSheet("")
        
        self.api_section.setVisible(True)
        self.name_section.setVisible(True)
        
        provider_type = provider.get("type", "")
        help_info = PROVIDER_HELP_INFO.get(provider_type, {})
        
        self.api_label.setText(f"{provider['display_name']} API 密钥")
        
        if help_info.get("api_key_url"):
            self.help_link.setUrl(help_info["api_key_url"])
            self.help_link.setVisible(True)
        else:
            self.help_link.setVisible(False)
        
        self.api_input.setFocus()
    
    def accept(self):
        if not self.selected_provider:
            InfoBar.warning("提示", "请先选择一个 AI 平台", duration=2000, parent=self)
            return
        
        self.api_key = self.api_input.text().strip()
        self.config_name = self.name_input.text().strip()
        
        if not self.api_key and self.mode != "TTS":
            provider_type = self.selected_provider.get("type", "")
            if "ollama" not in provider_type and "edge" not in provider_type:
                InfoBar.warning("提示", "请输入 API 密钥", duration=2000, parent=self)
                return
        
        super().accept()


class ConfigInterface(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("ModelConfigInterface")
        self.current_model_id = None
        self.current_mode = "LLM"
        self._provider_help_link = ""
        
        self._init_provider_registry()
        self.migrate_settings()
        self.init_ui()
        self.load_models()
        self.update_form_visibility()

    def _init_provider_registry(self):
        try:
            from src.provider.sources import (
                ProviderOpenAI, ProviderDeepSeek, ProviderAnthropic,
                ProviderOllama, ProviderMoonshot, ProviderGemini,
                ProviderGroq, ProviderZhipu,
                ProviderEdgeTTS, ProviderOpenAITTS,
                ProviderOpenAIImage
            )
        except ImportError as e:
            print(f"Warning: Some providers could not be imported: {e}")

    def migrate_settings(self):
        models = self.db.get_models()
        if not models:
            settings = QSettings("MyApp", "LLMClient")
            api_key = settings.value("api_key", "")
            base_url = settings.value("base_url", "https://api.openai.com/v1")
            model = settings.value("model", "gpt-3.5-turbo")
            
            if api_key:
                self.db.add_model("Default Model", "openai", api_key, base_url, model)

    def _get_providers_for_mode(self, mode: str) -> list:
        if mode == "LLM":
            provider_type = ProviderType.CHAT_COMPLETION
        elif mode == "TTS":
            provider_type = ProviderType.TEXT_TO_SPEECH
        elif mode == "IMAGE":
            provider_type = ProviderType.IMAGE_GENERATION
        else:
            return []
        
        providers = get_all_providers_by_type(provider_type)
        result = []
        for pm in providers:
            help_info = PROVIDER_HELP_INFO.get(pm.type, {})
            result.append({
                "type": pm.type,
                "display_name": pm.provider_display_name,
                "desc": help_info.get("desc", pm.desc or ""),
                "default_config": pm.default_config_tmpl or {},
                "api_key_url": help_info.get("api_key_url", ""),
                "doc_url": help_info.get("doc_url", "")
            })
        return result

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._init_left_panel(main_layout)
        self._init_right_panel(main_layout)
        
        self.edit_widget.setEnabled(False)
        self._refresh_provider_combo()
        self.update_theme()

    def _init_left_panel(self, parent_layout):
        self.left_panel = QWidget()
        self.left_panel.setObjectName("left_panel")
        self.left_panel.setFixedWidth(260)
            
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(16, 20, 16, 20)
        left_layout.setSpacing(12)

        self.pivot = SegmentedWidget(self.left_panel)
        self.pivot.addItem("LLM", "对话模型")
        self.pivot.addItem("TTS", "语音合成")
        self.pivot.addItem("IMAGE", "图像生成")
        self.pivot.setCurrentItem("LLM")
        self.pivot.currentItemChanged.connect(self.switch_mode)
        left_layout.addWidget(self.pivot)

        list_header = QHBoxLayout()
        list_header.addWidget(StrongBodyLabel("配置列表", self.left_panel))
        list_header.addStretch()
        left_layout.addLayout(list_header)

        self.model_list = ListWidget(self.left_panel)
        self.model_list.setObjectName("model_list")
        self.model_list.itemClicked.connect(self.on_model_selected)
        left_layout.addWidget(self.model_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.quick_add_btn = PushButton(FluentIcon.ADD_TO, "快速添加", self.left_panel)
        self.quick_add_btn.setFixedHeight(32)
        self.quick_add_btn.clicked.connect(self.quick_add_model)
        btn_layout.addWidget(self.quick_add_btn, 1)
        
        self.add_btn = PushButton(FluentIcon.ADD, "手动添加", self.left_panel)
        self.add_btn.setFixedHeight(32)
        self.add_btn.setToolTip("手动添加配置")
        self.add_btn.clicked.connect(self.create_new_model)
        btn_layout.addWidget(self.add_btn)
        
        left_layout.addLayout(btn_layout)

        parent_layout.addWidget(self.left_panel)

    def _init_right_panel(self, parent_layout):
        right_panel = ScrollArea(self)
        right_panel.setWidgetResizable(True)
        right_panel.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.edit_widget = QWidget()
        self.edit_widget.setObjectName("configEditWidget")
        right_layout = QVBoxLayout(self.edit_widget)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        self.page_title = TitleLabel("模型配置", self.edit_widget)
        header_layout.addWidget(self.page_title)
        header_layout.addStretch()
        
        self.status_label = CaptionLabel("", self.edit_widget)
        self.status_label.setStyleSheet("color: #0078d4;")
        header_layout.addWidget(self.status_label)
        
        right_layout.addLayout(header_layout)

        right_layout.addWidget(self._create_basic_card())
        right_layout.addWidget(self._create_auth_card())
        right_layout.addWidget(self._create_advanced_card())

        self._create_action_buttons(right_layout)
        right_layout.addStretch()

        right_panel.setWidget(self.edit_widget)
        parent_layout.addWidget(right_panel)

    def _create_basic_card(self) -> SettingCard:
        self.basic_card = SettingCard("基础配置", FluentIcon.SETTING, self)
        
        self.name_field = FormField(
            "配置名称", 
            LineEdit(self),
            "为这个配置起一个容易识别的名字",
            parent=self
        )
        self.name_field.widget.setPlaceholderText("例如: 我的 DeepSeek")
        self.basic_card.add_field(self.name_field)
        
        provider_widget = QWidget(self)
        provider_layout = QVBoxLayout(provider_widget)
        provider_layout.setContentsMargins(0, 0, 0, 0)
        provider_layout.setSpacing(6)
        
        self.provider_combo = ComboBox(provider_widget)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        self.provider_help_link = HyperlinkLabel(provider_widget)
        self.provider_help_link.setText("获取 API 密钥 →")
        self.provider_help_link.setVisible(False)
        provider_layout.addWidget(self.provider_help_link)
        
        self.provider_field = FormField(
            "AI 平台",
            provider_widget,
            "选择您要使用的 AI 服务商",
            parent=self
        )
        self.basic_card.add_field(self.provider_field)
        
        model_widget = QWidget(self)
        model_layout = QHBoxLayout(model_widget)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(8)
        
        self.model_id_input = LineEdit(model_widget)
        self.model_id_input.setPlaceholderText("例如: gpt-4, deepseek-chat")
        model_layout.addWidget(self.model_id_input, 1)
        
        self.fetch_models_btn = PushButton(FluentIcon.SEARCH, "搜索", model_widget)
        self.fetch_models_btn.setFixedHeight(32)
        self.fetch_models_btn.setToolTip("从平台获取可用模型列表")
        self.fetch_models_btn.clicked.connect(self.fetch_models_from_provider)
        model_layout.addWidget(self.fetch_models_btn)
        
        self.model_field = FormField(
            "模型名称",
            model_widget,
            "指定要使用的模型，点击右侧按钮可自动获取",
            parent=self
        )
        self.basic_card.add_field(self.model_field)
        
        voice_widget = QWidget(self)
        voice_layout = QHBoxLayout(voice_widget)
        voice_layout.setContentsMargins(0, 0, 0, 0)
        voice_layout.setSpacing(8)
        
        self.voice_input = LineEdit(voice_widget)
        self.voice_input.setPlaceholderText("例如: zh-CN-XiaoxiaoNeural")
        voice_layout.addWidget(self.voice_input, 1)
        
        self.fetch_voices_btn = PushButton(FluentIcon.SEARCH, "", voice_widget)
        self.fetch_voices_btn.setFixedSize(32, 32)
        self.fetch_voices_btn.setToolTip("获取可用语音列表")
        self.fetch_voices_btn.clicked.connect(self.fetch_voices_from_provider)
        voice_layout.addWidget(self.fetch_voices_btn)
        
        self.voice_field = FormField(
            "语音包",
            voice_widget,
            "选择 TTS 语音包名称",
            parent=self
        )
        self.basic_card.add_field(self.voice_field)
        
        return self.basic_card

    def _create_auth_card(self) -> SettingCard:
        self.auth_card = SettingCard("认证信息", FluentIcon.FINGERPRINT, self)
        
        self.api_key_field = FormField(
            "API 密钥",
            LineEdit(self),
            "从 AI 平台获取的访问密钥，用于验证身份",
            parent=self
        )
        self.api_key_field.widget.setEchoMode(QLineEdit.Password)
        self.api_key_field.widget.setPlaceholderText("sk-...")
        self.auth_card.add_field(self.api_key_field)
        
        return self.auth_card

    def _create_advanced_card(self) -> CollapsibleCard:
        self.advanced_card = CollapsibleCard("高级选项", FluentIcon.SETTING, collapsed=True, parent=self)
        
        self.base_url_field = FormField(
            "接口地址",
            LineEdit(self),
            "API 的基础地址，通常无需修改",
            parent=self
        )
        self.base_url_field.widget.setPlaceholderText("自动填充，通常无需修改")
        self.advanced_card.add_widget(self.base_url_field)
        
        self.proxy_field = FormField(
            "网络代理",
            LineEdit(self),
            "如需代理访问，填写代理地址",
            parent=self
        )
        self.proxy_field.widget.setPlaceholderText("例如: http://127.0.0.1:7890 (可选)")
        self.advanced_card.add_widget(self.proxy_field)
        
        options_widget = QWidget(self)
        options_layout = QHBoxLayout(options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(16)
        
        self.chk_visual = CheckBox("视觉模型", options_widget)
        self.chk_visual.setToolTip("勾选后，该模型将支持图片识别功能")
        options_layout.addWidget(self.chk_visual)
        
        options_layout.addStretch()
        self.advanced_card.add_widget(options_widget)
        
        return self.advanced_card

    def _create_action_buttons(self, layout: QVBoxLayout):
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存配置", self.edit_widget)
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self.save_model)
        btn_layout.addWidget(self.save_btn)
        
        self.use_btn = PushButton(FluentIcon.ACCEPT, "启用此配置", self.edit_widget)
        self.use_btn.setFixedHeight(36)
        self.use_btn.setToolTip("设为当前使用的配置")
        self.use_btn.clicked.connect(self.set_active_model_handler)
        btn_layout.addWidget(self.use_btn)
        
        btn_layout.addStretch()
        
        self.delete_btn = PushButton(FluentIcon.DELETE, "删除配置", self.edit_widget)
        # self.delete_btn.setFixedSize(36, 36)
        self.delete_btn.setToolTip("删除此配置")
        self.delete_btn.clicked.connect(self.delete_model)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)

    def _refresh_provider_combo(self):
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        
        providers = self._get_providers_for_mode(self.current_mode)
        
        self.provider_combo.addItem("自定义配置", userData="custom")
        for p in providers:
            self.provider_combo.addItem(p["display_name"], userData=p["type"])
        
        self.provider_combo.blockSignals(False)
        
        self._providers_cache = providers

    @property
    def name_input(self):
        return self.name_field.widget
    
    @property
    def api_key_input(self):
        return self.api_key_field.widget
    
    @property
    def base_url_input(self):
        return self.base_url_field.widget
    
    @property
    def proxy_input(self):
        return self.proxy_field.widget

    def switch_mode(self, item_key):
        self.current_mode = item_key
        self.create_new_model()
        self.edit_widget.setEnabled(False)
        self._refresh_provider_combo()
        self.load_models()
        self.update_form_visibility()
        
        mode_titles = {
            "LLM": "对话模型配置",
            "TTS": "语音合成配置", 
            "IMAGE": "图像生成配置"
        }
        self.page_title.setText(mode_titles.get(item_key, "模型配置"))

    def update_form_visibility(self):
        is_tts = (self.current_mode == "TTS")
        self.voice_field.setVisible(is_tts)
        self.fetch_voices_btn.setVisible(is_tts)
        
        is_llm = (self.current_mode == "LLM")
        self.chk_visual.setVisible(is_llm)
        
        self.fetch_models_btn.setVisible(is_llm or self.current_mode == "IMAGE")
        
        api_required = (self.current_mode != "TTS")
        if api_required:
            self.api_key_field.widget.setPlaceholderText("sk-...")
        else:
            self.api_key_field.widget.setPlaceholderText("sk-... (可选)")

    def load_models(self):
        self.model_list.clear()
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()
            
        for m in models:
            item = QListWidgetItem(m[1], self.model_list)
            item.setData(Qt.UserRole, m[0])
            self.model_list.addItem(item)
            
            is_active_idx = 7 if self.current_mode == "TTS" else 6
            if m[is_active_idx] == 1:
                self.model_list.setCurrentItem(item)
                self.on_model_selected(item)

    def on_model_selected(self, item):
        if not item: return
        self.edit_widget.setEnabled(True)
        model_id = item.data(Qt.UserRole)
        self.current_model_id = model_id
        self.status_label.setText("编辑中")
        
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
            self.name_input.setText(target[1])
            
            provider = target[2]
            provider_type = self._map_provider_name_to_type(provider)
            
            index = 0
            for i in range(self.provider_combo.count()):
                if self.provider_combo.itemData(i) == provider_type:
                    index = i
                    break
            
            self.provider_combo.setCurrentIndex(index)
            
            if self.current_mode == "IMAGE":
                self.base_url_input.setText(target[3])
                self.api_key_input.setText(target[4])
                self.model_id_input.setText(target[5])
            else:
                self.api_key_input.setText(target[3])
                self.base_url_input.setText(target[4])
                self.model_id_input.setText(target[5])
            
            if self.current_mode == "TTS":
                self.voice_input.setText(target[6])
                proxy = target[8] if len(target) > 8 else ''
                self.proxy_input.setText(proxy)
            elif self.current_mode == "LLM":
                if len(target) > 7:
                    self.chk_visual.setChecked(bool(target[7]))
                else:
                    self.chk_visual.setChecked(False)
                
                proxy = target[9] if len(target) > 9 else ''
                self.proxy_input.setText(proxy)
            elif self.current_mode == "IMAGE":
                proxy = target[7] if len(target) > 7 else ''
                self.proxy_input.setText(proxy)

    def _map_provider_name_to_type(self, provider_name: str) -> str:
        if not provider_name:
            return "custom"
        
        name_lower = provider_name.lower()
        
        if self.current_mode == "LLM":
            mapping = {
                "openai": "openai_chat_completion",
                "deepseek": "deepseek_chat_completion",
                "anthropic": "anthropic_chat_completion",
                "claude": "anthropic_chat_completion",
                "ollama": "ollama_chat_completion",
                "moonshot": "moonshot_chat_completion",
                "kimi": "moonshot_chat_completion",
                "gemini": "gemini_chat_completion",
                "google": "gemini_chat_completion",
                "groq": "groq_chat_completion",
                "zhipu": "zhipu_chat_completion",
            }
        elif self.current_mode == "TTS":
            mapping = {
                "edge": "edge_tts",
                "openai": "openai_tts",
                "siliconflow": "openai_tts",
            }
        elif self.current_mode == "IMAGE":
            mapping = {
                "openai": "openai_image",
                "dall-e": "openai_image",
                "siliconflow": "openai_image",
            }
        else:
            mapping = {}
        
        for key, value in mapping.items():
            if key in name_lower:
                return value
        
        return "custom"

    def create_new_model(self):
        self.model_list.clearSelection()
        self.edit_widget.setEnabled(True)
        self.current_model_id = None
        self.status_label.setText("新建配置")
        
        self.name_input.clear()
        self.provider_combo.setCurrentIndex(0)
        self.api_key_input.clear()
        self.base_url_input.clear()
        self.model_id_input.clear()
        self.voice_input.clear()
        self.proxy_input.clear()
        
        self.chk_visual.setChecked(False)
        self.advanced_card.set_collapsed(True)
        
        self.name_input.setFocus()

    def quick_add_model(self):
        providers = self._get_providers_for_mode(self.current_mode)
        
        dialog = QuickAddDialog(providers, self.current_mode, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_provider:
            provider = dialog.selected_provider
            
            name = dialog.config_name or provider["display_name"]
            self.name_input.setText(name)
            
            provider_type = provider["type"]
            for i in range(self.provider_combo.count()):
                if self.provider_combo.itemData(i) == provider_type:
                    self.provider_combo.setCurrentIndex(i)
                    break
            
            self.api_key_input.setText(dialog.api_key)
            
            default_config = provider.get("default_config", {})
            if "base_url" in default_config:
                self.base_url_input.setText(default_config["base_url"])
            if "model" in default_config:
                self.model_id_input.setText(default_config["model"])
            if "voice" in default_config:
                self.voice_input.setText(default_config["voice"])
            
            self.edit_widget.setEnabled(True)
            self.current_model_id = None
            self.status_label.setText("新建配置")
            
            InfoBar.success(
                "快速配置",
                f"已填充 {provider['display_name']} 的默认配置，请检查后保存",
                duration=3000,
                parent=self
            )

    def on_provider_changed(self, index):
        provider_type = self.provider_combo.currentData()
        
        if not provider_type or provider_type == "custom":
            self.provider_help_link.setVisible(False)
            return
        
        help_info = PROVIDER_HELP_INFO.get(provider_type, {})
        if help_info.get("api_key_url"):
            self.provider_help_link.setUrl(help_info["api_key_url"])
            self.provider_help_link.setVisible(True)
        else:
            self.provider_help_link.setVisible(False)
        
        metadata = get_provider_metadata(provider_type)
        if metadata and metadata.default_config_tmpl:
            default_config = metadata.default_config_tmpl
            
            if "base_url" in default_config:
                self.base_url_input.setText(default_config["base_url"])
            if "model" in default_config:
                self.model_id_input.setText(default_config["model"])
            if "voice" in default_config:
                self.voice_input.setText(default_config["voice"])

    def fetch_models_from_provider(self):
        provider_type = self.provider_combo.currentData()
        if not provider_type or provider_type == "custom":
            InfoBar.warning(
                "提示",
                "请先选择一个 AI 平台",
                duration=2000,
                parent=self
            )
            return
        
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        proxy = self.proxy_input.text().strip()
        
        if not base_url:
            InfoBar.warning(
                "提示",
                "请先填写接口地址，或选择一个服务商",
                duration=2000,
                parent=self
            )
            return
        
        metadata = get_provider_metadata(provider_type)
        if not metadata or not metadata.cls_type:
            InfoBar.error(
                "错误",
                "无法获取服务商信息",
                duration=2000,
                parent=self
            )
            return
        
        config = ProviderConfig(
            id="temp_fetch",
            name="temp",
            type=provider_type,
            provider_type="chat_completion",
            api_key=api_key,
            base_url=base_url,
            model="",
            proxy=proxy
        )
        
        self.fetch_models_btn.setEnabled(False)
        self.fetch_models_btn.setToolTip("获取中...")
        QApplication.processEvents()
        
        provider = None
        try:
            provider = metadata.cls_type(config)
            models = provider.get_models()
            
            if not models:
                InfoBar.warning(
                    "提示",
                    "未能获取到模型列表，请检查 API 密钥和接口地址是否正确",
                    duration=3000,
                    parent=self
                )
            else:
                dialog = ModelSelectDialog(models, "选择模型", self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_model:
                    self.model_id_input.setText(dialog.selected_model)
                    InfoBar.success(
                        "成功",
                        f"已选择模型: {dialog.selected_model}",
                        duration=2000,
                        parent=self
                    )
        except Exception as e:
            import traceback
            traceback.print_exc()
            InfoBar.error(
                "错误",
                f"获取模型列表失败: {e}",
                duration=3000,
                parent=self
            )
        finally:
            if provider:
                try:
                    provider.close()
                except:
                    pass
            self.fetch_models_btn.setEnabled(True)
            self.fetch_models_btn.setToolTip("从平台获取可用模型列表")
    
    def fetch_voices_from_provider(self):
        provider_type = self.provider_combo.currentData()
        if not provider_type or provider_type == "custom":
            InfoBar.warning(
                "提示",
                "请先选择一个语音服务商",
                duration=2000,
                parent=self
            )
            return
        
        metadata = get_provider_metadata(provider_type)
        if not metadata or not metadata.cls_type:
            InfoBar.error(
                "错误",
                "无法获取服务商信息",
                duration=2000,
                parent=self
            )
            return
        
        config = ProviderConfig(
            id="temp_fetch",
            name="temp",
            type=provider_type,
            provider_type="text_to_speech",
            api_key=self.api_key_input.text().strip(),
            base_url=self.base_url_input.text().strip(),
            model=self.model_id_input.text().strip(),
            proxy=self.proxy_input.text().strip()
        )
        
        self.fetch_voices_btn.setEnabled(False)
        self.fetch_voices_btn.setToolTip("获取中...")
        QApplication.processEvents()
        
        provider = None
        try:
            provider = metadata.cls_type(config)
            voices_data = provider.get_voices()
            voices = [v.get("id", v.get("name", str(v))) if isinstance(v, dict) else str(v) for v in voices_data]
            
            if not voices:
                InfoBar.warning(
                    "提示",
                    "未能获取到语音列表",
                    duration=3000,
                    parent=self
                )
            else:
                dialog = ModelSelectDialog(voices, "选择语音", self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_model:
                    self.voice_input.setText(dialog.selected_model)
                    InfoBar.success(
                        "成功",
                        f"已选择语音: {dialog.selected_model}",
                        duration=2000,
                        parent=self
                    )
        except Exception as e:
            import traceback
            traceback.print_exc()
            InfoBar.error(
                "错误",
                f"获取语音列表失败: {e}",
                duration=3000,
                parent=self
            )
        finally:
            if provider:
                try:
                    provider.close()
                except:
                    pass
            self.fetch_voices_btn.setEnabled(True)
            self.fetch_voices_btn.setToolTip("获取可用语音列表")

    def save_model(self):
        name = self.name_input.text().strip()
        if not name:
            name = "未命名配置"
            
        provider = self.provider_combo.currentData() or self.provider_combo.currentText()
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        model_name = self.model_id_input.text().strip()
        proxy = self.proxy_input.text().strip()
        
        if self.current_mode == "TTS":
            voice = self.voice_input.text().strip()
            if self.current_model_id:
                self.db.update_tts_model(self.current_model_id, name, provider, api_key, base_url, model_name, voice, proxy)
            else:
                self.current_model_id = self.db.add_tts_model(name, provider, api_key, base_url, model_name, voice, proxy)
        elif self.current_mode == "IMAGE":
            if self.current_model_id:
                self.db.update_image_model(self.current_model_id, name, provider, base_url, api_key, model_name, proxy)
            else:
                self.current_model_id = self.db.add_image_model(name, provider, base_url, api_key, model_name, proxy)
        else:
            is_visual = 1 if self.chk_visual.isChecked() else 0
            
            if self.current_model_id:
                self.db.update_model(self.current_model_id, name, provider, api_key, base_url, model_name, is_visual, 0, proxy)
            else:
                self.current_model_id = self.db.add_model(name, provider, api_key, base_url, model_name, is_visual, 0, proxy)
        
        self._reload_provider_manager()
        self._refresh_model_list_keep_selection()
        self.status_label.setText("已保存")
        
        InfoBar.success(
            "保存成功",
            f"配置 \"{name}\" 已保存",
            duration=2000,
            parent=self
        )

    def _reload_provider_manager(self):
        try:
            pm = ProviderManager.get_instance()
            pm.load_providers_from_db(self.db)
        except Exception as e:
            print(f"Warning: Failed to reload provider manager: {e}")

    def _refresh_model_list_keep_selection(self):
        saved_id = self.current_model_id
        self.model_list.clear()
        
        if self.current_mode == "TTS":
            models = self.db.get_tts_models()
        elif self.current_mode == "IMAGE":
            models = self.db.get_image_models()
        else:
            models = self.db.get_models()
            
        saved_item = None
        for m in models:
            item = QListWidgetItem(m[1], self.model_list)
            item.setData(Qt.UserRole, m[0])
            self.model_list.addItem(item)
            
            if m[0] == saved_id:
                saved_item = item
        
        if saved_item:
            self.model_list.setCurrentItem(saved_item)

    def delete_model(self):
        if not self.current_model_id:
            return
        
        name = self.name_input.text().strip() or "此配置"
        box = MessageBox("确认删除", f"确定要删除 \"{name}\" 吗？", self)
        box.yesButton.setText("删除")
        box.cancelButton.setText("取消")
        
        if not box.exec_():
            return
        
        if self.current_mode == "TTS":
            self.db.delete_tts_model(self.current_model_id)
        elif self.current_mode == "IMAGE":
            self.db.delete_image_model(self.current_model_id)
        else:
            self.db.delete_model(self.current_model_id)
        
        self.create_new_model()
        self.load_models()
        
        InfoBar.success(
            "已删除",
            f"配置 \"{name}\" 已删除",
            duration=2000,
            parent=self
        )

    def set_active_model_handler(self):
        if not self.current_model_id:
            return

        if self.current_mode == "TTS":
            self.db.set_active_tts_model(self.current_model_id)
            model_name = self.name_input.text().strip() or "未命名配置"
            InfoBar.success(
                "已启用",
                f"已将 \"{model_name}\" 设为默认语音配置",
                duration=2500,
                parent=self
            )
        elif self.current_mode == "IMAGE":
            self.db.set_active_image_model(self.current_model_id)
            model_name = self.name_input.text().strip() or "未命名配置"
            InfoBar.success(
                "已启用",
                f"已将 \"{model_name}\" 设为默认绘图配置",
                duration=2500,
                parent=self
            )
        else:
            self.db.set_active_model(self.current_model_id)
            model_name = self.name_input.text().strip() or "未命名配置"
            InfoBar.success(
                "已启用",
                f"已将 \"{model_name}\" 设为默认对话模型",
                duration=2500,
                parent=self
            )
        
        self._reload_provider_manager()
        self.load_models()

    def update_theme(self):
        pass
