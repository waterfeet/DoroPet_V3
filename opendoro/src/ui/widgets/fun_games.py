from datetime import datetime, date
import random
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, SubtitleLabel, BodyLabel,
    TransparentToolButton, FluentIcon
)


class FortuneWidget(CardWidget):
    fortune_generated = pyqtSignal(str)

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title = SubtitleLabel("🔮 今日运势", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.fortune_display = QWidget(self)
        fortune_layout = QVBoxLayout(self.fortune_display)
        fortune_layout.setContentsMargins(0, 0, 0, 0)
        fortune_layout.setSpacing(8)

        self.date_label = BodyLabel("", self)
        self.date_label.setObjectName("fortuneDateLabel")
        self.date_label.setAlignment(Qt.AlignCenter)
        fortune_layout.addWidget(self.date_label)

        self.lucky_label = BodyLabel("", self)
        self.lucky_label.setObjectName("fortuneLuckyLabel")
        self.lucky_label.setAlignment(Qt.AlignCenter)
        fortune_layout.addWidget(self.lucky_label)

        self.fortune_stars = BodyLabel("", self)
        self.fortune_stars.setObjectName("fortuneStarsLabel")
        self.fortune_stars.setAlignment(Qt.AlignCenter)
        fortune_layout.addWidget(self.fortune_stars)

        self.fortune_text = BodyLabel("", self)
        self.fortune_text.setObjectName("fortuneTextLabel")
        self.fortune_text.setAlignment(Qt.AlignCenter)
        self.fortune_text.setWordWrap(True)
        fortune_layout.addWidget(self.fortune_text)

        self.lucky_items = BodyLabel("", self)
        self.lucky_items.setObjectName("fortuneLuckyItemsLabel")
        self.lucky_items.setAlignment(Qt.AlignCenter)
        self.lucky_items.setWordWrap(True)
        fortune_layout.addWidget(self.lucky_items)

        layout.addWidget(self.fortune_display)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.refresh_btn = PrimaryPushButton("🔄 刷新运势", self)
        self.refresh_btn.setFixedHeight(35)
        self.refresh_btn.clicked.connect(self._generate_fortune)

        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self._generate_fortune()

    def _generate_fortune(self):
        if self.fun_manager:
            fortune_data = self.fun_manager.generate_daily_fortune()

            self.date_label.setText(fortune_data.get("date", ""))
            self.lucky_label.setText(fortune_data.get("emoji", "🌟"))
            self.fortune_stars.setText(fortune_data.get("stars", "⭐⭐⭐"))
            self.fortune_text.setText(fortune_data.get("text", ""))
            self.lucky_items.setText(fortune_data.get("lucky_items", ""))

            self.fortune_generated.emit(fortune_data.get("text", ""))


class WeatherWidget(CardWidget):
    weather_received = pyqtSignal(str)
    weather_error = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._is_loading = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.back_btn = TransparentToolButton(FluentIcon.LEFT_ARROW, self)
        self.back_btn.setFixedSize(16, 16)
        self.back_btn.setIconSize(self.back_btn.size())
        self.back_btn.setToolTip("返回")
        self.back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.back_btn)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        title = SubtitleLabel("🌤️ 天气查询", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = BodyLabel("点击下方按钮查询实时天气", self)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        self.weather_display = QWidget(self)
        weather_layout = QVBoxLayout(self.weather_display)
        weather_layout.setContentsMargins(0, 0, 0, 0)
        weather_layout.setSpacing(8)

        self.location_label = BodyLabel("", self)
        self.location_label.setObjectName("weatherLocationLabel")
        self.location_label.setAlignment(Qt.AlignCenter)
        weather_layout.addWidget(self.location_label)

        self.temp_label = BodyLabel("", self)
        self.temp_label.setObjectName("weatherTempLabel")
        self.temp_label.setAlignment(Qt.AlignCenter)
        weather_layout.addWidget(self.temp_label)

        self.weather_icon = BodyLabel("", self)
        self.weather_icon.setObjectName("weatherIconLabel")
        self.weather_icon.setAlignment(Qt.AlignCenter)
        weather_layout.addWidget(self.weather_icon)

        self.weather_desc = BodyLabel("", self)
        self.weather_desc.setObjectName("weatherDescLabel")
        self.weather_desc.setAlignment(Qt.AlignCenter)
        self.weather_desc.setWordWrap(True)
        weather_layout.addWidget(self.weather_desc)

        self.weather_display.hide()
        layout.addWidget(self.weather_display)

        self.loading_label = BodyLabel("🔍 正在查询天气...", self)
        self.loading_label.setObjectName("weatherLoadingLabel")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.query_btn = PrimaryPushButton("🔍 查询天气", self)
        self.query_btn.setFixedHeight(35)
        self.query_btn.clicked.connect(self._query_weather)

        btn_layout.addStretch()
        btn_layout.addWidget(self.query_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def _query_weather(self):
        if self._is_loading:
            return

        self._is_loading = True
        self.query_btn.setEnabled(False)
        self.weather_display.hide()
        self.loading_label.show()

        if self.fun_manager:
            self.fun_manager.query_weather(self._on_weather_result)

    def _on_weather_result(self, success: bool, data: dict):
        self._is_loading = False
        self.query_btn.setEnabled(True)
        self.loading_label.hide()

        if success and data:
            self.location_label.setText(f"📍 {data.get('location', '未知位置')}")
            self.temp_label.setText(data.get('temperature', '--'))
            self.weather_icon.setText(data.get('icon', '🌤️'))
            self.weather_desc.setText(data.get('description', '暂无天气信息'))
            self.weather_display.show()

            weather_text = f"{data.get('location', '')} {data.get('temperature', '')} {data.get('description', '')}"
            self.weather_received.emit(weather_text)
        else:
            error_msg = data.get('error', '查询失败，请稍后重试') if data else '查询失败'
            self.weather_desc.setText(error_msg)
            self.weather_icon.setText("😕")
            self.weather_display.show()
            self.weather_error.emit(error_msg)


class FortunePageWidget(CardWidget):
    fortune_generated = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.back_btn = TransparentToolButton(FluentIcon.LEFT_ARROW, self)
        self.back_btn.setFixedSize(16, 16)
        self.back_btn.setIconSize(self.back_btn.size())
        self.back_btn.setToolTip("返回")
        self.back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.back_btn)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        title = SubtitleLabel("🔮 今日运势", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.fortune_display = QWidget(self)
        fortune_layout = QVBoxLayout(self.fortune_display)
        fortune_layout.setContentsMargins(0, 0, 0, 0)
        fortune_layout.setSpacing(8)

        self.date_label = BodyLabel("", self)
        self.date_label.setObjectName("fortuneDateLabel")
        self.date_label.setAlignment(Qt.AlignCenter)
        fortune_layout.addWidget(self.date_label)

        self.lucky_label = BodyLabel("", self)
        self.lucky_label.setObjectName("fortuneLuckyLabel")
        self.lucky_label.setAlignment(Qt.AlignCenter)
        fortune_layout.addWidget(self.lucky_label)

        self.fortune_stars = BodyLabel("", self)
        self.fortune_stars.setObjectName("fortuneStarsLabel")
        self.fortune_stars.setAlignment(Qt.AlignCenter)
        fortune_layout.addWidget(self.fortune_stars)

        self.fortune_text = BodyLabel("", self)
        self.fortune_text.setObjectName("fortuneTextLabel")
        self.fortune_text.setAlignment(Qt.AlignCenter)
        self.fortune_text.setWordWrap(True)
        fortune_layout.addWidget(self.fortune_text)

        self.lucky_items = BodyLabel("", self)
        self.lucky_items.setObjectName("fortuneLuckyItemsLabel")
        self.lucky_items.setAlignment(Qt.AlignCenter)
        self.lucky_items.setWordWrap(True)
        fortune_layout.addWidget(self.lucky_items)

        layout.addWidget(self.fortune_display)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.refresh_btn = PrimaryPushButton("🔄 刷新运势", self)
        self.refresh_btn.setFixedHeight(35)
        self.refresh_btn.clicked.connect(self._generate_fortune)

        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self._generate_fortune()

    def _generate_fortune(self):
        if self.fun_manager:
            fortune_data = self.fun_manager.generate_daily_fortune()

            self.date_label.setText(fortune_data.get("date", ""))
            self.lucky_label.setText(fortune_data.get("emoji", "🌟"))
            self.fortune_stars.setText(fortune_data.get("stars", "⭐⭐⭐"))
            self.fortune_text.setText(fortune_data.get("text", ""))
            self.lucky_items.setText(fortune_data.get("lucky_items", ""))

            self.fortune_generated.emit(fortune_data.get("text", ""))


class TouchInteractionCard(CardWidget):
    interaction_triggered = pyqtSignal(str, str)

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = SubtitleLabel("趣味互动", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btn_grid = QHBoxLayout()
        btn_grid.setSpacing(8)

        interactions = [
            ("👆", "戳一戳", "poke"),
            ("🤚", "挠痒痒", "tickle"),
            ("👋", "摸摸头", "pet"),
            ("🤏", "捏脸脸", "pinch"),
        ]

        self.buttons = {}
        for emoji, text, action in interactions:
            btn = PushButton(f"{emoji} {text}", self)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, a=action: self._do_interaction(a))
            btn_grid.addWidget(btn)
            self.buttons[action] = btn

        layout.addLayout(btn_grid)

    def _do_interaction(self, action: str):
        if self.fun_manager:
            response, _ = self.fun_manager.get_touch_response(action)
            self.interaction_triggered.emit(action, response)


class FunInteractionPanel(CardWidget):
    fun_event_triggered = pyqtSignal(str)
    event_bonuses_ready = pyqtSignal(dict)
    event_with_type = pyqtSignal(str, bool)
    weather_query_requested = pyqtSignal()

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title = SubtitleLabel("✨ 趣味互动", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.game_stack = QStackedWidget(self)

        self.main_menu = QWidget()
        menu_layout = QVBoxLayout(self.main_menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.weather_btn = PushButton("🌤️ 天气查询", self)
        self.weather_btn.setFixedHeight(45)
        self.weather_btn.clicked.connect(lambda: self.game_stack.setCurrentIndex(1))

        self.fortune_btn = PushButton("🔮 今日运势", self)
        self.fortune_btn.setFixedHeight(45)
        self.fortune_btn.clicked.connect(lambda: self.game_stack.setCurrentIndex(2))

        row1.addWidget(self.weather_btn)
        row1.addWidget(self.fortune_btn)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.event_btn = PushButton("🎁 随机事件", self)
        self.event_btn.setFixedHeight(45)
        self.event_btn.clicked.connect(self._trigger_event)

        self.fun_btn = PushButton("💬 随机说话", self)
        self.fun_btn.setFixedHeight(45)
        self.fun_btn.clicked.connect(self._random_talk)

        row2.addWidget(self.event_btn)
        row2.addWidget(self.fun_btn)

        menu_layout.addLayout(row1)
        menu_layout.addLayout(row2)

        self.game_stack.addWidget(self.main_menu)

        self.weather_widget = WeatherWidget(self.fun_manager, self)
        self.weather_widget.back_requested.connect(lambda: self.game_stack.setCurrentIndex(0))
        self.weather_widget.weather_received.connect(self._on_weather_received)
        self.game_stack.addWidget(self.weather_widget)

        self.fortune_widget = FortunePageWidget(self.fun_manager, self)
        self.fortune_widget.back_requested.connect(lambda: self.game_stack.setCurrentIndex(0))
        self.fortune_widget.fortune_generated.connect(self._on_fortune_generated)
        self.game_stack.addWidget(self.fortune_widget)

        layout.addWidget(self.game_stack)

    def _on_weather_received(self, weather_text: str):
        self.fun_event_triggered.emit(f"天气查询：{weather_text}")

    def _on_fortune_generated(self, fortune_text: str):
        self.fun_event_triggered.emit(f"今日运势：{fortune_text}")

    def _trigger_event(self):
        if self.fun_manager:
            name, desc, bonuses = self.fun_manager.trigger_random_event()
            self.fun_event_triggered.emit(desc)
            if bonuses:
                self.event_bonuses_ready.emit(bonuses)
                total = sum(bonuses.values())
                is_positive = total >= 0
                self.event_with_type.emit(desc, is_positive)

    def _random_talk(self):
        if self.fun_manager:
            talk = self.fun_manager.get_random_fun_talk()
            self.fun_event_triggered.emit(talk)

    def back_to_menu(self):
        self.game_stack.setCurrentIndex(0)

    def update_theme(self, is_dark: bool):
        pass
