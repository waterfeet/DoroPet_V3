from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QSettings
from qfluentwidgets import (ScrollArea, CheckBox, Slider, TitleLabel, 
                            StrongBodyLabel, CaptionLabel, PushButton, FluentIcon, isDarkTheme, LineEdit)
from src.core.logger import logger

class SettingsInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("SettingsInterface")
        
        self.live2d_widget = None
        self.settings = QSettings("DoroPet", "Settings")
        
        layout = QVBoxLayout(self.view)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("软件设置", self.view)
        layout.addWidget(title)
        
        # --- 1. 常规设置 ---
        layout.addWidget(StrongBodyLabel("常规", self.view))
        
        # 开机自启
        self.check_autorun = CheckBox("开机自动启动", self.view)
        self.check_autorun.stateChanged.connect(self.on_autorun_changed)
        layout.addWidget(self.check_autorun)
        
        # 鼠标交互 (锁定)
        self.check_mouse_interact = CheckBox("启用鼠标交互 (取消勾选以锁定)", self.view)
        self.check_mouse_interact.setChecked(True) # Default true
        self.check_mouse_interact.stateChanged.connect(self.on_mouse_interact_changed)
        layout.addWidget(self.check_mouse_interact)
        
        layout.addSpacing(10)
        
        # --- 2. 显示设置 ---
        layout.addWidget(StrongBodyLabel("显示", self.view))
        
        # 缩放
        self.add_slider_option(layout, "模型缩放", 20, 150, 100, self.on_scale_changed, "%")
        
        # 气泡持续时间
        self.add_slider_option(layout, "气泡显示时长", 1000, 10000, 3000, self.on_bubble_duration_changed, " ms")
        
        layout.addSpacing(10)
        
        # --- 3. 声音设置 ---
        layout.addWidget(StrongBodyLabel("声音", self.view))
        
        # 音量
        self.add_slider_option(layout, "TTS 音量", 0, 100, 80, self.on_volume_changed, "%")
        
        layout.addSpacing(10)
        
        layout.addStretch()
        
        # 加载设置
        self.load_settings()
        
        # 初始化主题
        self.update_theme()

    def update_theme(self):
        if isDarkTheme():
            self.view.setStyleSheet("background-color: #272727; color: white;")
            self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        else:
            self.view.setStyleSheet("background-color: #f9f9f9; color: black;")
            self.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

    def add_slider_option(self, parent_layout, text, min_val, max_val, default_val, callback, unit_suffix=""):
        parent_layout.addWidget(StrongBodyLabel(text, self.view))
        
        h_layout = QHBoxLayout()
        slider = Slider(Qt.Horizontal, self.view)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        
        val_label = CaptionLabel(f"{default_val}{unit_suffix}", self.view)
        val_label.setFixedWidth(60) # Fixed width for alignment
        
        slider.valueChanged.connect(lambda v: val_label.setText(f"{v}{unit_suffix}"))
        slider.valueChanged.connect(callback)
        
        h_layout.addWidget(slider)
        h_layout.addWidget(val_label)
        parent_layout.addLayout(h_layout)
        
        # Store reference if needed for loading settings, e.g. using a dict
        if not hasattr(self, 'sliders'):
            self.sliders = {}
        self.sliders[text] = slider

    def set_live2d_widget(self, widget):
        self.live2d_widget = widget
        # Apply current settings to the widget
        self.on_scale_changed(self.sliders["模型缩放"].value())
        self.on_mouse_interact_changed(self.check_mouse_interact.isChecked())
        # Bubble duration is handled by reading the value when needed or setting a property

    def on_scale_changed(self, value):
        scale = value / 100.0
        if self.live2d_widget:
            # We need a way to set scale in Live2DWidget. 
            # Currently it uses wheel event to resize window.
            # We can resize the window based on initial size?
            # Or just simulate a resize.
            # Live2DWidget.resize() resizes the widget.
            # Let's assume a base size, e.g. 500x500 (implied in resize(550, 500) in context menu)
            base_w, base_h = 550, 500
            new_w = int(base_w * scale)
            new_h = int(base_h * scale)
            self.live2d_widget.resize(new_w, new_h)
        self.settings.setValue("scale", value)

    def on_bubble_duration_changed(self, value):
        # This might need to be stored in Live2DWidget or just global config
        # Currently Live2DWidget.talk uses a duration param.
        # We can update a default_duration attribute in Live2DWidget if we add it.
        if self.live2d_widget:
            self.live2d_widget.default_bubble_duration = value
        self.settings.setValue("bubble_duration", value)

    def on_volume_changed(self, value):
        # Access TTSManager from MainWindow -> ChatInterface
        try:
            chat_interface = self.window().chat_interface
            if hasattr(chat_interface, 'tts_manager'):
                chat_interface.tts_manager.player.setVolume(value)
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
        self.settings.setValue("volume", value)

    def on_mouse_interact_changed(self, checked):
        # Checked = Enabled -> Locked = False
        # Unchecked = Disabled -> Locked = True
        is_locked = not checked
        if self.live2d_widget:
            self.live2d_widget.set_locked(is_locked)
        self.settings.setValue("mouse_interact", checked)

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

    def load_settings(self):
        # Defaults
        scale = self.settings.value("scale", 100, type=int)
        bubble_duration = self.settings.value("bubble_duration", 3000, type=int)
        volume = self.settings.value("volume", 80, type=int)
        mouse_interact = self.settings.value("mouse_interact", True, type=bool)
        autorun = self.settings.value("autorun", False, type=bool)
        
        if "模型缩放" in self.sliders: self.sliders["模型缩放"].setValue(scale)
        if "气泡显示时长" in self.sliders: self.sliders["气泡显示时长"].setValue(bubble_duration)
        if "TTS 音量" in self.sliders: self.sliders["TTS 音量"].setValue(volume)
        self.check_mouse_interact.setChecked(mouse_interact)
        self.check_autorun.setChecked(autorun)
