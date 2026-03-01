import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class PetFunManager(QObject):
    fun_event_triggered = pyqtSignal(str, str)
    game_result = pyqtSignal(str, str, int)
    random_talk_triggered = pyqtSignal(str)

    IDLE_TALKS = [
        "在发呆呢...",
        "今天天气真好~",
        "人去哪了？",
        "好无聊啊...",
        "有点困了...",
        "欧润吉...欧润吉...",
        "在思考人生...",
        "你在看什么？",
        "嘿嘿~",
        "想出去玩了！",
        "肚子好像有点饿...",
        "今天做了个好梦！",
        "有人吗？",
        "自己玩会儿~",
        "看着你工作好辛苦~",
    ]

    HAPPY_TALKS = [
        "好开心！",
        "今天心情超好！",
        "啦啦啦~",
        "感觉棒极了！",
        "想跳个舞！",
    ]

    TOUCH_RESPONSES = {
        "poke": [
            "哎呀！别戳！",
            "戳戳戳...痒！",
            "干嘛戳我~",
            "被发现了！",
            "哼，再戳就生气了！",
        ],
        "tickle": [
            "哈哈哈好痒！",
            "别挠了别挠了！",
            "哈哈哈救命！",
            "痒死我了！",
            "哈哈哈要笑死了！",
        ],
        "pet": [
            "舒服~",
            "摸摸头~",
            "嘿嘿喜欢~",
            "再来再来~",
            "被治愈了~",
        ],
        "pinch": [
            "痛痛痛！",
            "轻点嘛~",
            "呜呜好疼...",
            "生气了！",
            "不可以捏脸！",
        ],
    }

    RANDOM_EVENTS = [
        {
            "id": "find_coin",
            "name": "发现硬币",
            "description": "Doro在地上发现了一枚闪亮的硬币！",
            "mood_bonus": 5,
            "weight": 10,
        },
        {
            "id": "butterfly",
            "name": "蝴蝶来访",
            "description": "一只漂亮的蝴蝶飞过来了，Doro开心地追着看！",
            "mood_bonus": 10,
            "weight": 8,
        },
        {
            "id": "rainbow",
            "name": "看到彩虹",
            "description": "窗外出现了美丽的彩虹！好幸运！",
            "mood_bonus": 15,
            "weight": 3,
        },
        {
            "id": "snack",
            "name": "发现零食",
            "description": "Doro在角落发现了一包零食！",
            "hunger_bonus": 10,
            "mood_bonus": 8,
            "weight": 7,
        },
        {
            "id": "nap",
            "name": "小憩一会",
            "description": "Doro打了个盹，精神好多了~",
            "energy_bonus": 15,
            "weight": 12,
        },
        {
            "id": "sneeze",
            "name": "打喷嚏",
            "description": "阿嚏！Doro打了个大喷嚏！",
            "mood_bonus": 0,
            "weight": 15,
        },
        {
            "id": "dream",
            "name": "做了好梦",
            "description": "Doro做了个美梦，梦里全是欧润吉！",
            "mood_bonus": 12,
            "weight": 8,
        },
        {
            "id": "sing",
            "name": "哼起歌来",
            "description": "Doro心情不错，哼起了小曲~",
            "mood_bonus": 5,
            "weight": 12,
        },
        {
            "id": "stretch",
            "name": "伸懒腰",
            "description": "Doro伸了个大懒腰~",
            "energy_bonus": 5,
            "weight": 15,
        },
        {
            "id": "lucky_day",
            "name": "幸运时刻",
            "description": "今天是什么幸运日！Doro感觉特别开心！",
            "mood_bonus": 20,
            "energy_bonus": 10,
            "weight": 2,
        },
        {
            "id": "yummy_food",
            "name": "美食分享",
            "description": "有人分享了美味的食物给Doro！",
            "hunger_bonus": 15,
            "mood_bonus": 10,
            "weight": 5,
        },
        {
            "id": "bubble",
            "name": "吹泡泡",
            "description": "Doro吹了一串泡泡，看着它们飘走好开心~",
            "mood_bonus": 8,
            "weight": 10,
        },
        {
            "id": "sunbath",
            "name": "晒太阳",
            "description": "阳光暖暖的，Doro舒服地晒了会太阳~",
            "energy_bonus": 10,
            "mood_bonus": 5,
            "weight": 10,
        },
        {
            "id": "bad_dream",
            "name": "做了噩梦",
            "description": "呜呜...Doro做了个可怕的噩梦...",
            "mood_penalty": 10,
            "energy_penalty": 5,
            "weight": 6,
        },
        {
            "id": "trip",
            "name": "摔了一跤",
            "description": "Doro不小心摔了一跤！痛痛的...",
            "mood_penalty": 8,
            "energy_penalty": 5,
            "weight": 7,
        },
        {
            "id": "scared",
            "name": "被吓到了",
            "description": "突然的响声把Doro吓了一跳！",
            "mood_penalty": 5,
            "energy_penalty": 3,
            "weight": 8,
        },
        {
            "id": "stomachache",
            "name": "肚子疼",
            "description": "Doro肚子有点不舒服...",
            "hunger_penalty": 10,
            "mood_penalty": 8,
            "weight": 5,
        },
        {
            "id": "rain",
            "name": "下雨了",
            "description": "突然下起了雨，Doro被淋湿了...",
            "cleanliness_penalty": 15,
            "mood_penalty": 5,
            "weight": 6,
        },
        {
            "id": "lose_toy",
            "name": "玩具丢了",
            "description": "Doro最喜欢的玩具找不到了...",
            "mood_penalty": 12,
            "weight": 5,
        },
        {
            "id": "mosquito",
            "name": "蚊子叮咬",
            "description": "有只蚊子叮了Doro一下！好痒！",
            "mood_penalty": 6,
            "weight": 9,
        },
        {
            "id": "bored",
            "name": "无聊透顶",
            "description": "好无聊啊...什么都不想做...",
            "mood_penalty": 8,
            "energy_penalty": 5,
            "weight": 10,
        },
        {
            "id": "spicy",
            "name": "吃到辣椒",
            "description": "哇！好辣好辣！Doro不小心吃到了辣椒！",
            "hunger_penalty": 5,
            "mood_penalty": 5,
            "weight": 6,
        },
        {
            "id": "messy",
            "name": "弄脏了",
            "description": "Doro玩的时候把自己弄脏了...",
            "cleanliness_penalty": 20,
            "mood_penalty": 3,
            "weight": 8,
        },
        {
            "id": "forgetful",
            "name": "忘记事情",
            "description": "Doro想做什么来着...完全忘记了...",
            "mood_penalty": 4,
            "weight": 10,
        },
    ]

    ROCK_PAPER_SCISSORS = {
        "rock": {"emoji": "✊", "name": "石头", "beats": "scissors"},
        "paper": {"emoji": "✋", "name": "布", "beats": "rock"},
        "scissors": {"emoji": "✌️", "name": "剪刀", "beats": "paper"},
    }

    RPS_WIN_TALKS = [
        "耶！我赢了！",
        "厉害吧~",
        "再来再来！",
        "运气真好！",
    ]

    RPS_LOSE_TALKS = [
        "啊...输了...",
        "再来一次！",
        "让我赢一次嘛~",
        "你太厉害了！",
    ]

    RPS_DRAW_TALKS = [
        "平局！再来！",
        "心有灵犀~",
        "再来再来！",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        self._idle_interval = 120000
        self._game_callback: Optional[Callable] = None

    def start_idle_talk(self, interval_ms: int = 120000):
        self._idle_interval = interval_ms
        self._idle_timer.start(interval_ms)

    def stop_idle_talk(self):
        self._idle_timer.stop()

    def _on_idle_tick(self):
        if random.random() < 0.5:
            talk = random.choice(self.IDLE_TALKS)
            self.random_talk_triggered.emit(talk)
        
        self._idle_timer.start(int(self._idle_interval * (0.8 + random.random() * 0.4)))

    def get_touch_response(self, touch_type: str) -> Tuple[str, str]:
        responses = self.TOUCH_RESPONSES.get(touch_type, ["..."])
        return random.choice(responses), touch_type

    def get_random_event(self) -> Optional[Dict]:
        total_weight = sum(e["weight"] for e in self.RANDOM_EVENTS)
        r = random.uniform(0, total_weight)
        
        cumulative = 0
        for event in self.RANDOM_EVENTS:
            cumulative += event["weight"]
            if r <= cumulative:
                return event
        return None

    def trigger_random_event(self) -> Tuple[str, str, Dict[str, int]]:
        event = self.get_random_event()
        if not event:
            return "", "", {}
        
        bonuses = {}
        if "mood_bonus" in event:
            bonuses["mood"] = event["mood_bonus"]
        if "hunger_bonus" in event:
            bonuses["hunger"] = event["hunger_bonus"]
        if "energy_bonus" in event:
            bonuses["energy"] = event["energy_bonus"]
        if "cleanliness_bonus" in event:
            bonuses["cleanliness"] = event["cleanliness_bonus"]
        
        if "mood_penalty" in event:
            bonuses["mood"] = bonuses.get("mood", 0) - event["mood_penalty"]
        if "hunger_penalty" in event:
            bonuses["hunger"] = bonuses.get("hunger", 0) - event["hunger_penalty"]
        if "energy_penalty" in event:
            bonuses["energy"] = bonuses.get("energy", 0) - event["energy_penalty"]
        if "cleanliness_penalty" in event:
            bonuses["cleanliness"] = bonuses.get("cleanliness", 0) - event["cleanliness_penalty"]
        
        self.fun_event_triggered.emit(event["name"], event["description"])
        return event["name"], event["description"], bonuses

    def play_rock_paper_scissors(self, player_choice: str) -> Tuple[str, str, int]:
        choices = list(self.ROCK_PAPER_SCISSORS.keys())
        doro_choice = random.choice(choices)
        
        player = self.ROCK_PAPER_SCISSORS[player_choice]
        doro = self.ROCK_PAPER_SCISSORS[doro_choice]
        
        if player_choice == doro_choice:
            result = "draw"
            talk = random.choice(self.RPS_DRAW_TALKS)
        elif player["beats"] == doro_choice:
            result = "win"
            talk = random.choice(self.RPS_WIN_TALKS)
        else:
            result = "lose"
            talk = random.choice(self.RPS_LOSE_TALKS)
        
        result_text = "平局" if result == "draw" else ("你赢了！" if result == "win" else "Doro赢了！")
        message = f"Doro出了 {doro['emoji']} {doro['name']}！{result_text}\n{talk}"
        
        self.game_result.emit("rps", message, 1 if result == "win" else (0 if result == "draw" else -1))
        
        return message, doro_choice, 1 if result == "win" else (0 if result == "draw" else -1)

    def play_guess_number(self, player_guess: int, target: int = None, attempts: int = 1) -> Tuple[str, bool]:
        if target is None:
            target = random.randint(1, 10)
        
        if player_guess == target:
            talks = [
                f"对了！就是{target}！",
                f"猜对了！{target}！你好厉害！",
                f"没错！答案是{target}！",
            ]
            message = random.choice(talks)
            self.game_result.emit("guess", message, 1)
            return message, True
        elif player_guess < target:
            hint = "太小了！再大一点~"
        else:
            hint = "太大了！再小一点~"
        
        if attempts >= 3:
            message = f"没猜中呢~答案是{target}！再来一局吧！"
            self.game_result.emit("guess", message, -1)
            return message, True
        
        self.game_result.emit("guess", hint, 0)
        return hint, False

    _guess_target: int = 0
    _guess_attempts: int = 0

    def start_guess_number_game(self) -> int:
        self._guess_target = random.randint(1, 10)
        self._guess_attempts = 0
        return self._guess_target

    def make_guess(self, guess: int) -> Tuple[str, bool]:
        self._guess_attempts += 1
        return self.play_guess_number(guess, self._guess_target, self._guess_attempts)

    def get_random_fun_talk(self) -> str:
        talks = self.HAPPY_TALKS + [
            "想玩游戏吗？",
            "来互动吧~",
            "陪我玩嘛~",
            "今天有什么好玩的？",
        ]
        return random.choice(talks)
