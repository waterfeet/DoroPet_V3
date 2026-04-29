from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, QSettings
from qfluentwidgets import (ScrollArea, CheckBox, Slider, TitleLabel,
                            StrongBodyLabel, CaptionLabel, PushButton, FluentIcon,
                            isDarkTheme, LineEdit, Pivot, CardWidget, BodyLabel,
                            ComboBox, SpinBox, InfoBar, TransparentToolButton)
from src.core.logger import logger


class SettingCard(CardWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        self.title_label = StrongBodyLabel(title, self)
        layout.addWidget(self.title_label)
        
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        layout.addWidget(self.content_widget)
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class GeneralSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        card = SettingCard("常规设置", self)
        
        self.check_autorun = CheckBox("开机自动启动", self)
        self.check_hide_pet_on_startup = CheckBox("启动时隐藏桌宠 (仅显示主界面)", self)
        self.check_mouse_interact = CheckBox("启用鼠标交互 (取消勾选以锁定)", self)
        self.check_mouse_interact.setChecked(True)
        
        card.addWidget(self.check_autorun)
        card.addWidget(self.check_hide_pet_on_startup)
        card.addWidget(self.check_mouse_interact)
        
        layout.addWidget(card)
        
        self._setup_cache_management(layout)
        
        shortcut_card = SettingCard("快捷方式", self)
        
        shortcut_info_layout = QHBoxLayout()
        shortcut_info_label = BodyLabel("在桌面创建 DoroPet 快捷方式", self)
        shortcut_info_layout.addWidget(shortcut_info_label)
        shortcut_info_layout.addStretch()
        shortcut_card.addLayout(shortcut_info_layout)
        
        self.btn_create_shortcut = PushButton(FluentIcon.SHARE, "创建桌面快捷方式", self)
        self.btn_create_shortcut.setFixedWidth(160)
        
        btn_shortcut_layout = QHBoxLayout()
        btn_shortcut_layout.addStretch()
        btn_shortcut_layout.addWidget(self.btn_create_shortcut)
        shortcut_card.addLayout(btn_shortcut_layout)
        
        layout.addWidget(shortcut_card)
        layout.addStretch()
        
        self.btn_create_shortcut.clicked.connect(self._create_desktop_shortcut)
        self._refresh_all_cache_sizes()

    def _setup_cache_management(self, parent_layout):
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QFrame, QSizePolicy
        from qfluentwidgets import PushButton, FluentIcon, InfoBar
        from src.core.cache_manager import get_cache_manager
        
        self._cache_manager = get_cache_manager()
        self._cache_labels = {}
        self._cache_buttons = {}
        
        cache_card = SettingCard("缓存管理", self)
        
        safe_cache_label = StrongBodyLabel("安全缓存（可随时清除）", self)
        cache_card.addWidget(safe_cache_label)
        
        safe_caches = [
            ("tts", "TTS 语音缓存", "AI 语音合成的音频缓存", "🔊"),
            ("image", "网络图片缓存", "聊天中加载的网络图片缓存", "🖼️"),
            ("temp_images", "临时图片", "Base64 编码的临时图片文件", "📄"),
            ("musicdl", "musicdl 临时输出", "音乐搜索产生的临时文件", "🎵"),
            ("old_logs", "旧日志文件", "超过 7 天的日志文件", "📝"),
        ]
        
        for cache_key, cache_name, description, icon in safe_caches:
            self._add_cache_row(cache_card, cache_key, cache_name, description, icon, is_safe=True)
        
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        cache_card.addWidget(separator)
        
        warning_cache_label = StrongBodyLabel("⚠️ 谨慎清除（会丢失用户数据）", self)
        cache_card.addWidget(warning_cache_label)
        
        warning_caches = [
            ("music_downloads", "音乐下载", "已下载的音乐文件（清除后需重新下载）", "⚠️"),
        ]
        
        for cache_key, cache_name, description, icon in warning_caches:
            self._add_cache_row(cache_card, cache_key, cache_name, description, icon, is_safe=False)
        
        separator2 = QFrame(self)
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        cache_card.addWidget(separator2)
        
        total_layout = QHBoxLayout()
        total_label = StrongBodyLabel("📊 总缓存大小:", self)
        total_layout.addWidget(total_label)
        
        self._total_cache_label = CaptionLabel("0 MB", self)
        self._total_cache_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        total_layout.addWidget(self._total_cache_label)
        total_layout.addStretch()
        cache_card.addLayout(total_layout)
        
        clear_all_layout = QHBoxLayout()
        clear_all_layout.addStretch()
        
        self.btn_clear_all_safe = PushButton(FluentIcon.DELETE, "一键清除安全缓存", self)
        self.btn_clear_all_safe.setFixedWidth(160)
        self.btn_clear_all_safe.clicked.connect(self._clear_all_safe_caches)
        clear_all_layout.addWidget(self.btn_clear_all_safe)
        
        cache_card.addLayout(clear_all_layout)
        
        parent_layout.addWidget(cache_card)

    def _add_cache_row(self, parent_card, cache_key: str, cache_name: str, description: str, icon: str, is_safe: bool):
        row_layout = QHBoxLayout()
        row_layout.setSpacing(8)
        
        icon_label = CaptionLabel(icon, self)
        icon_label.setFixedWidth(20)
        row_layout.addWidget(icon_label)
        
        name_label = BodyLabel(cache_name, self)
        name_label.setFixedWidth(120)
        row_layout.addWidget(name_label)
        
        size_label = CaptionLabel("0 MB", self)
        size_label.setFixedWidth(80)
        self._cache_labels[cache_key] = size_label
        row_layout.addWidget(size_label)
        
        btn = PushButton("清除", self)
        btn.setFixedSize(60, 28)
        btn.clicked.connect(lambda checked, k=cache_key: self._clear_cache(k))
        self._cache_buttons[cache_key] = btn
        row_layout.addWidget(btn)
        
        row_layout.addStretch()
        parent_card.addLayout(row_layout)
        
        desc_label = CaptionLabel(description, self)
        desc_label.setStyleSheet("color: gray; margin-left: 28px;")
        parent_card.addWidget(desc_label)

    def _refresh_all_cache_sizes(self):
        from PyQt5.QtCore import QTimer
        
        all_info = self._cache_manager.get_all_cache_info()
        
        for info in all_info:
            cache_key = self._get_cache_key_from_name(info.name)
            if cache_key in self._cache_labels:
                self._cache_labels[cache_key].setText(info.size_display)
        
        self._total_cache_label.setText(self._cache_manager.get_total_size_display())

    def _get_cache_key_from_name(self, name: str) -> str:
        mapping = {
            "TTS 语音缓存": "tts",
            "网络图片缓存": "image",
            "临时图片": "temp_images",
            "musicdl 临时输出": "musicdl",
            "旧日志文件": "old_logs",
            "音乐下载": "music_downloads",
        }
        return mapping.get(name, "")

    def _clear_cache(self, cache_key: str):
        clear_methods = {
            "tts": self._cache_manager.clear_tts_cache,
            "image": self._cache_manager.clear_image_cache,
            "temp_images": self._cache_manager.clear_temp_images_cache,
            "musicdl": self._cache_manager.clear_musicdl_cache,
            "old_logs": self._cache_manager.clear_old_logs,
            "music_downloads": self._cache_manager.clear_music_downloads,
        }
        
        method = clear_methods.get(cache_key)
        if not method:
            return
        
        try:
            deleted, freed = method()
            freed_mb = freed / (1024 * 1024)
            
            if deleted > 0:
                InfoBar.success(
                    "缓存已清除",
                    f"已删除 {deleted} 个文件，释放 {freed_mb:.2f} MB",
                    duration=2000
                )
            else:
                InfoBar.warning(
                    "缓存为空",
                    "没有需要清除的缓存文件",
                    duration=2000
                )
        except Exception as e:
            InfoBar.error(
                "清除失败",
                f"清除缓存时出错: {str(e)}",
                duration=2000
            )
        
        self._refresh_all_cache_sizes()

    def _clear_all_safe_caches(self):
        try:
            deleted, freed = self._cache_manager.clear_all_safe_caches()
            freed_mb = freed / (1024 * 1024)
            
            if deleted > 0:
                InfoBar.success(
                    "缓存已清除",
                    f"已删除 {deleted} 个文件，释放 {freed_mb:.2f} MB",
                    duration=2000
                )
            else:
                InfoBar.warning(
                    "缓存为空",
                    "没有需要清除的缓存文件",
                    duration=2000
                )
        except Exception as e:
            InfoBar.error(
                "清除失败",
                f"清除缓存时出错: {str(e)}",
                duration=2000
            )
        
        self._refresh_all_cache_sizes()

    def refresh_cache_sizes(self):
        self._refresh_all_cache_sizes()
    
    def _create_desktop_shortcut(self):
        from src.core.shortcut_utils import create_desktop_shortcut
        
        success, message = create_desktop_shortcut(replace_existing=False)
        if success:
            InfoBar.success(
                "创建成功",
                message,
                duration=3000
            )
        else:
            InfoBar.error(
                "创建失败",
                message,
                duration=3000
            )


class DisplaySettingsPage(QWidget):
    ASPECT_RATIOS = [
        ("1:1 (正方形)", 1.0),
        ("4:3 (标准)", 4.0 / 3.0),
        ("3:4 (竖屏)", 3.0 / 4.0),
        ("16:9 (宽屏)", 16.0 / 9.0),
        ("9:16 (竖屏宽屏)", 9.0 / 16.0),
        ("16:10", 16.0 / 10.0),
        ("10:16 (竖屏)", 10.0 / 16.0),
        ("自定义", -1),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        card = SettingCard("显示设置", self)
        self.sliders = {}
        
        self.check_show_pet_status = CheckBox("显示宠物属性栏", self)
        self.check_show_pet_status.setChecked(True)
        card.addWidget(self.check_show_pet_status)
        
        self.add_slider_option(card, "模型缩放", 20, 150, 100, "%")
        self.add_slider_option(card, "窗口透明度", 10, 100, 100, "%")
        self.add_slider_option(card, "气泡显示时长", 1000, 10000, 3000, " ms")
        
        layout.addWidget(card)
        
        aspect_card = SettingCard("Live2D 窗口比例", self)
        
        aspect_label = StrongBodyLabel("选择窗口宽高比", self)
        aspect_card.addWidget(aspect_label)
        
        aspect_h_layout = QHBoxLayout()
        self.aspect_combo = ComboBox(self)
        self.aspect_combo.addItems([ratio[0] for ratio in self.ASPECT_RATIOS])
        self.aspect_combo.setCurrentIndex(0)
        self.aspect_combo.setFixedWidth(150)
        self.aspect_combo.currentIndexChanged.connect(self._on_aspect_preset_changed)
        aspect_h_layout.addWidget(self.aspect_combo)
        aspect_h_layout.addStretch()
        aspect_card.addLayout(aspect_h_layout)
        
        custom_layout = QHBoxLayout()
        custom_label = BodyLabel("自定义比例:", self)
        custom_layout.addWidget(custom_label)
        
        self.width_spin = SpinBox(self)
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(550)
        self.width_spin.setFixedWidth(130)
        self.width_spin.setEnabled(False)
        custom_layout.addWidget(self.width_spin)
        
        x_label = BodyLabel("×", self)
        custom_layout.addWidget(x_label)
        
        self.height_spin = SpinBox(self)
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(500)
        self.height_spin.setFixedWidth(130)
        self.height_spin.setEnabled(False)
        custom_layout.addWidget(self.height_spin)
        
        custom_layout.addStretch()
        aspect_card.addLayout(custom_layout)
        
        self.width_spin.valueChanged.connect(self._on_custom_size_changed)
        self.height_spin.valueChanged.connect(self._on_custom_size_changed)
        
        apply_btn = PushButton(FluentIcon.ACCEPT, "应用比例", self)
        apply_btn.clicked.connect(self._apply_aspect_ratio)
        aspect_card.addWidget(apply_btn)
        
        layout.addWidget(aspect_card)
        
        monitor_card = SettingCard("系统监控", self)

        self.check_system_monitor = CheckBox("启用系统监控 (CPU/内存),占用过高让doro提示,低配置建议调高阈值", self)
        self.check_system_monitor.setChecked(True)
        monitor_card.addWidget(self.check_system_monitor)

        self.add_slider_option(monitor_card, "CPU 告警阈值", 50, 100, 70, "%")
        self.add_slider_option(monitor_card, "内存告警阈值", 50, 100, 80, "%")

        layout.addWidget(monitor_card)

        font_card = SettingCard("字体大小", self)

        font_label = StrongBodyLabel("选择字体大小", self)
        font_card.addWidget(font_label)

        font_h_layout = QHBoxLayout()
        font_h_layout.setSpacing(8)

        self.font_buttons = {}
        font_options = [
            ("小", 90),
            ("中", 100),
            ("大", 115),
            ("特大", 135),
        ]

        for text, value in font_options:
            btn = PushButton(text, self)
            btn.setFixedSize(60, 32)
            btn.setCursor(Qt.PointingHandCursor)
            self.font_buttons[value] = btn
            font_h_layout.addWidget(btn)

        font_h_layout.addStretch()

        for value, btn in self.font_buttons.items():
            btn.clicked.connect(lambda checked, v=value: self._on_font_button_clicked(v))

        font_card.addLayout(font_h_layout)

        layout.addWidget(font_card)
        layout.addStretch()

        self._update_font_buttons_style(100)

    def _on_font_button_clicked(self, value):
        settings_interface = self._find_settings_interface()
        if settings_interface:
            settings_interface._on_font_size_clicked(value)

    def _find_settings_interface(self):
        widget = self.parent()
        while widget:
            if isinstance(widget, SettingsInterface):
                return widget
            widget = widget.parent()
        return None

    def _update_font_buttons_style(self, selected_value):
        is_dark = isDarkTheme()
        font_sizes = {90: 12, 100: 14, 115: 16, 135: 18}
        for value, btn in self.font_buttons.items():
            font_size = font_sizes.get(value, 14)
            if value == selected_value:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(0, 120, 212, 0.2);
                        border: 1px solid rgba(0, 120, 212, 0.5);
                        border-radius: 4px;
                        color: #0078d4;
                        font-weight: bold;
                        font-size: {font_size}px;
                    }}
                """ if not is_dark else f"""
                    QPushButton {{
                        background-color: rgba(96, 165, 250, 0.2);
                        border: 1px solid rgba(96, 165, 250, 0.5);
                        border-radius: 4px;
                        color: #60a5fa;
                        font-weight: bold;
                        font-size: {font_size}px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 4px;
                        color: #333333;
                        font-size: {font_size}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(0, 0, 0, 0.05);
                    }}
                """ if not is_dark else f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 4px;
                        color: #e0e0e0;
                        font-size: {font_size}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.05);
                    }}
                """)

    def _init_font_buttons_style(self, saved_value=100):
        if saved_value not in self.font_buttons:
            saved_value = 100
        self._update_font_buttons_style(saved_value)

    def _on_aspect_preset_changed(self, index):
        is_custom = self.ASPECT_RATIOS[index][1] < 0
        self.width_spin.setEnabled(is_custom)
        self.height_spin.setEnabled(is_custom)
    
    def _on_custom_size_changed(self):
        pass
    
    def _apply_aspect_ratio(self):
        pass
    
    def get_current_aspect_ratio(self):
        index = self.aspect_combo.currentIndex()
        ratio = self.ASPECT_RATIOS[index][1]
        
        if ratio < 0:
            return self.width_spin.value(), self.height_spin.value()
        else:
            base_size = 500
            width = int(base_size * ratio) if ratio >= 1 else base_size
            height = int(base_size / ratio) if ratio < 1 else base_size
            if ratio >= 1:
                height = int(width / ratio)
            else:
                width = int(height * ratio)
            return width, height
    
    def set_custom_size(self, width, height):
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
    
    def add_slider_option(self, parent_card, text, min_val, max_val, default_val, unit_suffix=""):
        parent_card.addWidget(StrongBodyLabel(text, self))
        
        h_layout = QHBoxLayout()
        slider = Slider(Qt.Horizontal, self)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        val_label = CaptionLabel(f"{default_val}{unit_suffix}", self)
        val_label.setFixedWidth(150)
        
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}{unit_suffix}"))
        
        h_layout.addWidget(slider)
        h_layout.addWidget(val_label)
        parent_card.addLayout(h_layout)
        
        self.sliders[text] = slider


class SoundSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        card = SettingCard("声音设置", self)
        self.sliders = {}
        
        self.add_slider_option(card, "TTS 音量", 0, 100, 80, "%")
        
        layout.addWidget(card)
        layout.addStretch()
    
    def add_slider_option(self, parent_card, text, min_val, max_val, default_val, unit_suffix=""):
        parent_card.addWidget(StrongBodyLabel(text, self))
        
        h_layout = QHBoxLayout()
        slider = Slider(Qt.Horizontal, self)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        val_label = CaptionLabel(f"{default_val}{unit_suffix}", self)
        val_label.setFixedWidth(60)
        
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}{unit_suffix}"))
        
        h_layout.addWidget(slider)
        h_layout.addWidget(val_label)
        parent_card.addLayout(h_layout)
        
        self.sliders[text] = slider


class AISettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        card = SettingCard("AI 设置", self)
        self.sliders = {}
        
        self.check_inject_time = CheckBox("在上下文注入当前时间", self)
        self.check_expression_response = CheckBox("开启表情响应 (AI自动控制表情)", self)
        
        card.addWidget(self.check_inject_time)
        card.addWidget(self.check_expression_response)
        
        card.addWidget(StrongBodyLabel("LLM 最大输出长度", self))
        
        h_layout = QHBoxLayout()
        slider = Slider(Qt.Horizontal, self)
        slider.setRange(1024, 32768)
        slider.setValue(8192)
        
        val_label = CaptionLabel("8192 tokens", self)
        val_label.setFixedWidth(80)
        
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v} tokens"))
        
        h_layout.addWidget(slider)
        h_layout.addWidget(val_label)
        card.addLayout(h_layout)
        
        self.sliders["LLM 最大输出长度"] = slider
        
        hint = CaptionLabel("(值越大，AI可生成的内容越长。代码/页面生成建议≥16384)", self)
        hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card.addWidget(hint)
        
        layout.addWidget(card)
        layout.addStretch()


class SettingsInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setObjectName("settingsView")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingsInterface")
        
        self.live2d_widget = None
        self.settings = QSettings("DoroPet", "Settings")
        
        main_layout = QVBoxLayout(self.view)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)
        
        title = TitleLabel("软件设置", self.view)
        main_layout.addWidget(title)
        
        self.pivot = Pivot(self.view)
        self.pivot.setFixedHeight(40)
        main_layout.addWidget(self.pivot)
        
        self.stacked_widget = QStackedWidget(self.view)
        main_layout.addWidget(self.stacked_widget)
        
        self.general_page = GeneralSettingsPage(self)
        self.display_page = DisplaySettingsPage(self)
        self.sound_page = SoundSettingsPage(self)
        self.ai_page = AISettingsPage(self)
        
        self.stacked_widget.addWidget(self.general_page)
        self.stacked_widget.addWidget(self.display_page)
        self.stacked_widget.addWidget(self.sound_page)
        self.stacked_widget.addWidget(self.ai_page)
        
        self.pivot.addItem(routeKey="general", text="⚙️ 常规", 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.general_page))
        self.pivot.addItem(routeKey="display", text="🖥️ 显示", 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.display_page))
        self.pivot.addItem(routeKey="sound", text="🔊 声音", 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.sound_page))
        self.pivot.addItem(routeKey="ai", text="🤖 AI", 
                          onClick=lambda: self.stacked_widget.setCurrentWidget(self.ai_page))
        
        self.pivot.setCurrentItem("general")
        
        self.connect_signals()
        self.load_settings()

    def connect_signals(self):
        self.general_page.check_autorun.stateChanged.connect(self.on_autorun_changed)
        self.general_page.check_hide_pet_on_startup.stateChanged.connect(self.on_hide_pet_on_startup_changed)
        self.general_page.check_mouse_interact.stateChanged.connect(self.on_mouse_interact_changed)
        
        self.display_page.check_show_pet_status.stateChanged.connect(self.on_show_pet_status_changed)
        self.display_page.sliders["模型缩放"].valueChanged.connect(self.on_scale_changed)
        self.display_page.sliders["窗口透明度"].valueChanged.connect(self.on_window_opacity_changed)
        self.display_page.sliders["气泡显示时长"].valueChanged.connect(self.on_bubble_duration_changed)
        self.display_page.aspect_combo.currentIndexChanged.connect(self.on_aspect_ratio_changed)
        self.display_page.width_spin.valueChanged.connect(self.on_custom_aspect_changed)
        self.display_page.height_spin.valueChanged.connect(self.on_custom_aspect_changed)
        
        self.display_page.check_system_monitor.stateChanged.connect(self.on_system_monitor_changed)
        self.display_page.sliders["CPU 告警阈值"].valueChanged.connect(self.on_cpu_threshold_changed)
        self.display_page.sliders["内存告警阈值"].valueChanged.connect(self.on_mem_threshold_changed)

        self.sound_page.sliders["TTS 音量"].valueChanged.connect(self.on_volume_changed)
        
        self.ai_page.check_inject_time.stateChanged.connect(self.on_inject_time_changed)
        self.ai_page.check_expression_response.stateChanged.connect(self.on_expression_response_changed)
        self.ai_page.sliders["LLM 最大输出长度"].valueChanged.connect(self.on_max_tokens_changed)

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        self.on_scale_changed(self.display_page.sliders["模型缩放"].value())
        self.on_mouse_interact_changed(self.general_page.check_mouse_interact.isChecked())

    def update_theme(self):
        pass

    def on_scale_changed(self, value):
        scale = value / 100.0
        if self.live2d_widget:
            width, height = self.display_page.get_current_aspect_ratio()
            new_w = int(width * scale)
            new_h = int(height * scale)
            self.live2d_widget.resize(new_w, new_h)
        self.settings.setValue("scale", value)

    def on_window_opacity_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.model_opacity = value
            self.live2d_widget.set_model_opacity(value / 100.0)
        self.settings.setValue("window_opacity", value)

    def on_bubble_duration_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.default_bubble_duration = value
        self.settings.setValue("bubble_duration", value)

    def on_volume_changed(self, value):
        try:
            chat_interface = self.window().chat_interface
            if hasattr(chat_interface, 'tts_manager') and chat_interface.tts_manager:
                tts = chat_interface.tts_manager
                if hasattr(tts, 'player') and tts.player:
                    tts.player.setVolume(value)
        except Exception as e:
            logger.warning(f"Error setting volume: {e}")
        self.settings.setValue("volume", value)

    def on_mouse_interact_changed(self, checked):
        is_locked = not checked
        if self.live2d_widget:
            self.live2d_widget.set_locked(is_locked, silent=True)
        self.settings.setValue("mouse_interact", checked)

    def on_show_pet_status_changed(self, checked):
        if self.live2d_widget and hasattr(self.live2d_widget, 'status_overlay'):
            self.live2d_widget.status_overlay.set_visible_by_setting(checked)
        self.settings.setValue("show_pet_status", checked)

    def on_system_monitor_changed(self, checked):
        if self.live2d_widget:
            self.live2d_widget.set_system_monitor_enabled(checked)
        self.settings.setValue("system_monitor_enabled", checked)

    def on_cpu_threshold_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.cpu_threshold = value
        self.settings.setValue("cpu_threshold", value)

    def on_mem_threshold_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.mem_threshold = value
        self.settings.setValue("mem_threshold", value)

    def _on_font_size_clicked(self, value):
        font_scale = value / 100.0
        self.settings.setValue("font_scale", font_scale)
        self.display_page._update_font_buttons_style(value)
        main_window = self.window()
        if main_window and hasattr(main_window, 'load_stylesheet'):
            from qfluentwidgets import isDarkTheme
            if isDarkTheme():
                from src.resource_utils import resource_path
                main_window.load_stylesheet(resource_path("themes/dark.qss"))
            else:
                from src.resource_utils import resource_path
                main_window.load_stylesheet(resource_path("themes/light.qss"))

    def on_aspect_ratio_changed(self, index):
        is_custom = self.display_page.ASPECT_RATIOS[index][1] < 0
        self.display_page.width_spin.setEnabled(is_custom)
        self.display_page.height_spin.setEnabled(is_custom)
        
        if not is_custom:
            self._apply_aspect_ratio()
        
        self.settings.setValue("aspect_ratio_index", index)
    
    def on_custom_aspect_changed(self):
        if self.display_page.aspect_combo.currentIndex() == len(self.display_page.ASPECT_RATIOS) - 1:
            width = self.display_page.width_spin.value()
            height = self.display_page.height_spin.value()
            self.settings.setValue("custom_aspect_width", width)
            self.settings.setValue("custom_aspect_height", height)
    
    def _apply_aspect_ratio(self):
        if not self.live2d_widget:
            return
        
        width, height = self.display_page.get_current_aspect_ratio()
        scale = self.display_page.sliders["模型缩放"].value() / 100.0
        
        final_width = int(width * scale)
        final_height = int(height * scale)
        
        self.live2d_widget.resize(final_width, final_height)
        
        if hasattr(self.live2d_widget, 'flash_border'):
            self.live2d_widget.flash_border()
        
        self.settings.setValue("window_width", final_width)
        self.settings.setValue("window_height", final_height)
        
        if self.display_page.aspect_combo.currentIndex() == len(self.display_page.ASPECT_RATIOS) - 1:
            self.settings.setValue("custom_aspect_width", width)
            self.settings.setValue("custom_aspect_height", height)

    def on_inject_time_changed(self, checked):
        self.settings.setValue("inject_time", checked)

    def on_expression_response_changed(self, checked):
        self.settings.setValue("enable_expression_response", checked)

    def on_max_tokens_changed(self, value):
        self.settings.setValue("llm_max_tokens", value)

    def on_autorun_changed(self, checked):
        import sys
        import os
        import winreg
        
        app_name = "DoroPet"
        exe_path = os.path.abspath(sys.argv[0])
        
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE)
            if checked:
                winreg.SetValueEx(registry_key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(registry_key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(registry_key)
            self.settings.setValue("autorun", checked)
            logger.info(f"Autorun set to {checked}")
        except Exception as e:
            logger.warning(f"Autorun error: {e}")

    def on_hide_pet_on_startup_changed(self, checked):
        self.settings.setValue("hide_pet_on_startup", checked)

    def load_settings(self):
        scale = self.settings.value("scale", 100, type=int)
        bubble_duration = self.settings.value("bubble_duration", 3000, type=int)
        volume = self.settings.value("volume", 80, type=int)
        mouse_interact = self.settings.value("mouse_interact", True, type=bool)
        autorun = self.settings.value("autorun", False, type=bool)
        hide_pet_on_startup = self.settings.value("hide_pet_on_startup", False, type=bool)
        inject_time = self.settings.value("inject_time", False, type=bool)
        expression_response = self.settings.value("enable_expression_response", True, type=bool)
        llm_max_tokens = self.settings.value("llm_max_tokens", 8192, type=int)
        show_pet_status = self.settings.value("show_pet_status", True, type=bool)
        system_monitor_enabled = self.settings.value("system_monitor_enabled", True, type=bool)
        cpu_threshold = self.settings.value("cpu_threshold", 70, type=int)
        mem_threshold = self.settings.value("mem_threshold", 80, type=int)
        
        aspect_ratio_index = self.settings.value("aspect_ratio_index", 0, type=int)
        custom_aspect_width = self.settings.value("custom_aspect_width", 550, type=int)
        custom_aspect_height = self.settings.value("custom_aspect_height", 500, type=int)
        
        self.general_page.check_autorun.setChecked(autorun)
        self.general_page.check_hide_pet_on_startup.setChecked(hide_pet_on_startup)
        self.general_page.check_mouse_interact.setChecked(mouse_interact)
        
        self.display_page.check_show_pet_status.setChecked(show_pet_status)
        self.display_page.sliders["模型缩放"].setValue(scale)
        window_opacity = self.settings.value("window_opacity", 100, type=int)
        self.display_page.sliders["窗口透明度"].setValue(window_opacity)
        self.display_page.sliders["气泡显示时长"].setValue(bubble_duration)
        self.display_page.check_system_monitor.setChecked(system_monitor_enabled)
        self.display_page.sliders["CPU 告警阈值"].setValue(cpu_threshold)
        self.display_page.sliders["内存告警阈值"].setValue(mem_threshold)
        
        self.display_page.aspect_combo.setCurrentIndex(aspect_ratio_index)
        self.display_page.width_spin.setValue(custom_aspect_width)
        self.display_page.height_spin.setValue(custom_aspect_height)
        
        self.sound_page.sliders["TTS 音量"].setValue(volume)
        
        self.ai_page.check_inject_time.setChecked(inject_time)
        self.ai_page.check_expression_response.setChecked(expression_response)
        self.ai_page.sliders["LLM 最大输出长度"].setValue(llm_max_tokens)

        self._init_font_buttons_style()

    def _init_font_buttons_style(self):
        saved_scale = self.settings.value("font_scale", 1.0, type=float)
        saved_value = int(saved_scale * 100)
        self.display_page._init_font_buttons_style(saved_value)
