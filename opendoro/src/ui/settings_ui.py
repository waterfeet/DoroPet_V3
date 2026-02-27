from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from PyQt5.QtCore import Qt, QSettings
from qfluentwidgets import (ScrollArea, CheckBox, Slider, TitleLabel, 
                            StrongBodyLabel, CaptionLabel, PushButton, FluentIcon, 
                            isDarkTheme, LineEdit, Pivot, CardWidget, BodyLabel)
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
        layout.addStretch()


class DisplaySettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        card = SettingCard("显示设置", self)
        self.sliders = {}
        
        self.add_slider_option(card, "模型缩放", 20, 150, 100, "%")
        self.add_slider_option(card, "气泡显示时长", 1000, 10000, 3000, " ms")
        
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
        
        self.display_page.sliders["模型缩放"].valueChanged.connect(self.on_scale_changed)
        self.display_page.sliders["气泡显示时长"].valueChanged.connect(self.on_bubble_duration_changed)
        
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
            base_w, base_h = 550, 500
            new_w = int(base_w * scale)
            new_h = int(base_h * scale)
            self.live2d_widget.resize(new_w, new_h)
        self.settings.setValue("scale", value)

    def on_bubble_duration_changed(self, value):
        if self.live2d_widget:
            self.live2d_widget.default_bubble_duration = value
        self.settings.setValue("bubble_duration", value)

    def on_volume_changed(self, value):
        try:
            chat_interface = self.window().chat_interface
            if hasattr(chat_interface, 'tts_manager'):
                chat_interface.tts_manager.player.setVolume(value)
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
        self.settings.setValue("volume", value)

    def on_mouse_interact_changed(self, checked):
        is_locked = not checked
        if self.live2d_widget:
            self.live2d_widget.set_locked(is_locked, silent=True)
        self.settings.setValue("mouse_interact", checked)

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
            logger.error(f"Autorun error: {e}")

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
        
        self.general_page.check_autorun.setChecked(autorun)
        self.general_page.check_hide_pet_on_startup.setChecked(hide_pet_on_startup)
        self.general_page.check_mouse_interact.setChecked(mouse_interact)
        
        self.display_page.sliders["模型缩放"].setValue(scale)
        self.display_page.sliders["气泡显示时长"].setValue(bubble_duration)
        
        self.sound_page.sliders["TTS 音量"].setValue(volume)
        
        self.ai_page.check_inject_time.setChecked(inject_time)
        self.ai_page.check_expression_response.setChecked(expression_response)
        self.ai_page.sliders["LLM 最大输出长度"].setValue(llm_max_tokens)
