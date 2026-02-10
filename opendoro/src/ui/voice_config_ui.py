from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from qfluentwidgets import (ScrollArea, LineEdit, StrongBodyLabel, 
                            TitleLabel, PushButton, FluentIcon, 
                            BodyLabel, PrimaryPushButton, SwitchButton, 
                            CardWidget, IconWidget, HyperlinkButton, InfoBar, InfoBarPosition, isDarkTheme)

class VoiceConfigInterface(QWidget):
    settingsChanged = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("VoiceConfigInterface")
        
        self.init_ui()
        self.load_settings()
        self.update_theme()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 36, 36, 36)
        main_layout.setSpacing(20)

        # Title
        main_layout.addWidget(TitleLabel("语音识别配置", self))

        # --- Enable Switch ---
        self.enable_card = CardWidget(self)
        enable_layout = QHBoxLayout(self.enable_card)
        enable_layout.setContentsMargins(20, 10, 20, 10)
        
        icon_widget = IconWidget(FluentIcon.MICROPHONE, self.enable_card)
        icon_widget.setFixedSize(24, 24)
        enable_layout.addWidget(icon_widget)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.addWidget(StrongBodyLabel("启用语音助手", self.enable_card))
        text_layout.addWidget(BodyLabel("开启后将在聊天界面显示语音交互按钮", self.enable_card))
        enable_layout.addLayout(text_layout)
        enable_layout.addStretch()
        
        self.enable_switch = SwitchButton(self.enable_card)
        self.enable_switch.setOnText("开启")
        self.enable_switch.setOffText("关闭")
        enable_layout.addWidget(self.enable_switch)
        
        main_layout.addWidget(self.enable_card)

        # --- Settings Area ---
        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.settings_widget = QWidget()
        form_layout = QVBoxLayout(self.settings_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(15)

        # 1. Wake Word
        form_layout.addWidget(StrongBodyLabel("唤醒词", self.settings_widget))
        self.wake_word_input = LineEdit(self.settings_widget)
        self.wake_word_input.setPlaceholderText("例如: Hey Doro")
        form_layout.addWidget(self.wake_word_input)
        form_layout.addWidget(BodyLabel("提示: 修改唤醒词可能需要对应的模型支持 (当前仅支持 'Hey Doro' 或自定义训练模型)", self.settings_widget))

        # 2. Model Paths
        form_layout.addWidget(StrongBodyLabel("KWS 模型路径 (唤醒词检测)", self.settings_widget))
        kws_layout = QHBoxLayout()
        self.kws_input = LineEdit(self.settings_widget)
        self.kws_btn = PushButton(FluentIcon.FOLDER, "选择", self.settings_widget)
        self.kws_btn.clicked.connect(lambda: self.select_folder(self.kws_input))
        kws_layout.addWidget(self.kws_input)
        kws_layout.addWidget(self.kws_btn)
        form_layout.addLayout(kws_layout)

        form_layout.addWidget(StrongBodyLabel("ASR 模型路径 (语音转文字)", self.settings_widget))
        asr_layout = QHBoxLayout()
        self.asr_input = LineEdit(self.settings_widget)
        self.asr_btn = PushButton(FluentIcon.FOLDER, "选择", self.settings_widget)
        self.asr_btn.clicked.connect(lambda: self.select_folder(self.asr_input))
        asr_layout.addWidget(self.asr_input)
        asr_layout.addWidget(self.asr_btn)
        form_layout.addLayout(asr_layout)

        # Download Link
        link_layout = QHBoxLayout()
        link_layout.addWidget(BodyLabel("需要下载更多模型？", self.settings_widget))
        self.link_btn = HyperlinkButton("https://github.com/k2-fsa/sherpa-onnx/releases", "前往 Sherpa-ONNX 模型仓库", self.settings_widget)
        self.link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/k2-fsa/sherpa-onnx/releases")))
        link_layout.addWidget(self.link_btn)
        link_layout.addStretch()
        form_layout.addLayout(link_layout)

        form_layout.addStretch()
        
        scroll.setWidget(self.settings_widget)
        main_layout.addWidget(scroll)

        # --- Save Button ---
        btn_layout = QHBoxLayout()
        self.save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存配置", self)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)

    def load_settings(self):
        settings = self.db.get_voice_settings()
        if settings:
            # is_enabled, wake_word, kws_path, asr_path
            self.enable_switch.setChecked(bool(settings[0]))
            self.wake_word_input.setText(settings[1])
            self.kws_input.setText(settings[2])
            self.asr_input.setText(settings[3])

    def save_settings(self):
        is_enabled = 1 if self.enable_switch.isChecked() else 0
        wake_word = self.wake_word_input.text().strip()
        kws_path = self.kws_input.text().strip()
        asr_path = self.asr_input.text().strip()
        
        self.db.update_voice_settings(is_enabled, wake_word, kws_path, asr_path)
        
        # Show success message
        InfoBar.success(
            title='保存成功',
            content="语音配置已更新 (重启语音助手生效)",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self
        )
        
        self.settingsChanged.emit()

    def select_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "选择模型目录")
        if folder:
            line_edit.setText(folder)

    def update_theme(self):
        if isDarkTheme():
            self.setStyleSheet("background-color: #272727; color: white;")
            self.settings_widget.setStyleSheet("background-color: transparent;")
            
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
                QLineEdit:focus { border: 1px solid #4cc2ff; background-color: #333333; }
            """
        else:
            self.setStyleSheet("background-color: #f9f9f9; color: black;")
            self.settings_widget.setStyleSheet("background-color: transparent;")
            
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
            
        self.wake_word_input.setStyleSheet(input_style)
        self.kws_input.setStyleSheet(input_style)
        self.asr_input.setStyleSheet(input_style)
