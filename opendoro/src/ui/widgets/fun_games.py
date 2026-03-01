from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QDialog, QStackedWidget

from qfluentwidgets import CardWidget, PushButton, PrimaryPushButton, SubtitleLabel, BodyLabel, InfoBar, InfoBarPosition


class RockPaperScissorsGame(CardWidget):
    game_finished = pyqtSignal(str, int)

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        title = SubtitleLabel("猜拳游戏", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = BodyLabel("选择你要出的手势：", self)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.rock_btn = PushButton("✊", self)
        self.rock_btn.setFixedSize(60, 50)
        self.rock_btn.clicked.connect(lambda: self._play("rock"))
        
        self.paper_btn = PushButton("✋", self)
        self.paper_btn.setFixedSize(60, 50)
        self.paper_btn.clicked.connect(lambda: self._play("paper"))
        
        self.scissors_btn = PushButton("✌️", self)
        self.scissors_btn.setFixedSize(60, 50)
        self.scissors_btn.clicked.connect(lambda: self._play("scissors"))
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.rock_btn)
        btn_layout.addWidget(self.paper_btn)
        btn_layout.addWidget(self.scissors_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        self.result_label = BodyLabel("", self)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.result_label)

    def _play(self, choice: str):
        if self.fun_manager:
            message, _, result = self.fun_manager.play_rock_paper_scissors(choice)
            self.result_label.setText(message)
            
            if result == 1:
                self.result_label.setStyleSheet("font-size: 14px; padding: 10px; color: #4caf50;")
            elif result == -1:
                self.result_label.setStyleSheet("font-size: 14px; padding: 10px; color: #f44336;")
            else:
                self.result_label.setStyleSheet("font-size: 14px; padding: 10px; color: #ff9800;")
            
            self.game_finished.emit(message, result)

    def reset(self):
        self.result_label.setText("")
        self.result_label.setStyleSheet("font-size: 14px; padding: 10px;")


class GuessNumberGame(CardWidget):
    game_finished = pyqtSignal(str, int)

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._target = 0
        self._attempts = 0
        self._init_ui()
        self._start_new_game()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        title = SubtitleLabel("猜数字", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = BodyLabel("猜一个1-10之间的数字：", self)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        self.spin_box = QSpinBox(self)
        self.spin_box.setRange(1, 10)
        self.spin_box.setFixedSize(80, 35)
        self.spin_box.setAlignment(Qt.AlignCenter)
        
        self.guess_btn = PrimaryPushButton("猜！", self)
        self.guess_btn.setFixedSize(70, 35)
        self.guess_btn.clicked.connect(self._make_guess)
        
        self.new_game_btn = PushButton("新游戏", self)
        self.new_game_btn.setFixedSize(70, 35)
        self.new_game_btn.clicked.connect(self._start_new_game)
        
        input_layout.addStretch()
        input_layout.addWidget(self.spin_box)
        input_layout.addWidget(self.guess_btn)
        input_layout.addWidget(self.new_game_btn)
        input_layout.addStretch()
        
        layout.addLayout(input_layout)
        
        self.result_label = BodyLabel("", self)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.result_label)
        
        self.attempts_label = BodyLabel("剩余机会：3", self)
        self.attempts_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.attempts_label)

    def _start_new_game(self):
        if self.fun_manager:
            self._target = self.fun_manager.start_guess_number_game()
        else:
            import random
            self._target = random.randint(1, 10)
        self._attempts = 0
        self.result_label.setText("")
        self.result_label.setStyleSheet("font-size: 14px; padding: 10px;")
        self.attempts_label.setText("剩余机会：3")
        self.guess_btn.setEnabled(True)

    def _make_guess(self):
        guess = self.spin_box.value()
        self._attempts += 1
        
        if self.fun_manager:
            message, finished = self.fun_manager.make_guess(guess)
        else:
            message, finished = f"猜了 {guess}", False
        
        remaining = 3 - self._attempts
        self.attempts_label.setText(f"剩余机会：{max(0, remaining)}")
        
        self.result_label.setText(message)
        
        if finished:
            if "对了" in message or "猜对" in message:
                self.result_label.setStyleSheet("font-size: 14px; padding: 10px; color: #4caf50;")
                self.game_finished.emit(message, 1)
            else:
                self.result_label.setStyleSheet("font-size: 14px; padding: 10px; color: #f44336;")
                self.game_finished.emit(message, -1)
            self.guess_btn.setEnabled(False)
        else:
            self.result_label.setStyleSheet("font-size: 14px; padding: 10px; color: #ff9800;")
            if remaining <= 0:
                self.guess_btn.setEnabled(False)


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

    def __init__(self, fun_manager, parent=None):
        super().__init__(parent)
        self.fun_manager = fun_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        title = SubtitleLabel("🎲 趣味互动", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.game_stack = QStackedWidget(self)
        
        self.main_menu = QWidget()
        menu_layout = QVBoxLayout(self.main_menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(8)
        
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        self.rps_btn = PushButton("✊ 猜拳", self)
        self.rps_btn.setFixedHeight(45)
        self.rps_btn.clicked.connect(lambda: self.game_stack.setCurrentIndex(1))
        
        self.guess_btn = PushButton("🔢 猜数字", self)
        self.guess_btn.setFixedHeight(45)
        self.guess_btn.clicked.connect(lambda: self.game_stack.setCurrentIndex(2))
        
        row1.addWidget(self.rps_btn)
        row1.addWidget(self.guess_btn)
        
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
        
        self.rps_game = RockPaperScissorsGame(self.fun_manager, self)
        rps_layout = QVBoxLayout(self.rps_game)
        back_btn = PushButton("← 返回", self.rps_game)
        back_btn.clicked.connect(lambda: self.game_stack.setCurrentIndex(0))
        rps_layout.insertWidget(0, back_btn)
        self.game_stack.addWidget(self.rps_game)
        
        self.guess_game = GuessNumberGame(self.fun_manager, self)
        guess_layout = QVBoxLayout(self.guess_game)
        back_btn2 = PushButton("← 返回", self.guess_game)
        back_btn2.clicked.connect(lambda: self.game_stack.setCurrentIndex(0))
        guess_layout.insertWidget(0, back_btn2)
        self.game_stack.addWidget(self.guess_game)
        
        layout.addWidget(self.game_stack)

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
