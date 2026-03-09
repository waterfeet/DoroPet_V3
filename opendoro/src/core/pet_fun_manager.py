import random
import hashlib
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QSettings, QThread

from src.skills.weather.weather_tool import query_weather


class WeatherQueryWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, city_name=None, parent=None):
        super().__init__(parent)
        self.city_name = city_name

    def run(self):
        try:
            result = query_weather(self.city_name)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


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
        {"id": "find_coin", "name": "发现硬币", "description": "Doro在地上发现了一枚闪亮的硬币！", "mood_bonus": 5, "weight": 10},
        {"id": "butterfly", "name": "蝴蝶来访", "description": "一只漂亮的蝴蝶飞过来了，Doro开心地追着看！", "mood_bonus": 10, "weight": 8},
        {"id": "rainbow", "name": "看到彩虹", "description": "窗外出现了美丽的彩虹！好幸运！", "mood_bonus": 15, "weight": 3},
        {"id": "snack", "name": "发现零食", "description": "Doro在角落发现了一包零食！", "hunger_bonus": 10, "mood_bonus": 8, "weight": 7},
        {"id": "nap", "name": "小憩一会", "description": "Doro打了个盹，精神好多了~", "energy_bonus": 15, "weight": 12},
        {"id": "sneeze", "name": "打喷嚏", "description": "阿嚏！Doro打了个大喷嚏！", "mood_bonus": 0, "weight": 15},
        {"id": "dream", "name": "做了好梦", "description": "Doro做了个美梦，梦里全是欧润吉！", "mood_bonus": 12, "weight": 8},
        {"id": "sing", "name": "哼起歌来", "description": "Doro心情不错，哼起了小曲~", "mood_bonus": 5, "weight": 12},
        {"id": "stretch", "name": "伸懒腰", "description": "Doro伸了个大懒腰~", "energy_bonus": 5, "weight": 15},
        {"id": "lucky_day", "name": "幸运时刻", "description": "今天是什么幸运日！Doro感觉特别开心！", "mood_bonus": 20, "energy_bonus": 10, "weight": 2},
        {"id": "yummy_food", "name": "美食分享", "description": "有人分享了美味的食物给Doro！", "hunger_bonus": 15, "mood_bonus": 10, "weight": 5},
        {"id": "bubble", "name": "吹泡泡", "description": "Doro吹了一串泡泡，看着它们飘走好开心~", "mood_bonus": 8, "weight": 10},
        {"id": "sunbath", "name": "晒太阳", "description": "阳光暖暖的，Doro舒服地晒了会太阳~", "energy_bonus": 10, "mood_bonus": 5, "weight": 10},
        {"id": "bad_dream", "name": "做了噩梦", "description": "呜呜...Doro做了个可怕的噩梦...", "mood_penalty": 10, "energy_penalty": 5, "weight": 6},
        {"id": "trip", "name": "摔了一跤", "description": "Doro不小心摔了一跤！痛痛的...", "mood_penalty": 8, "energy_penalty": 5, "weight": 7},
        {"id": "scared", "name": "被吓到了", "description": "突然的响声把Doro吓了一跳！", "mood_penalty": 5, "energy_penalty": 3, "weight": 8},
        {"id": "stomachache", "name": "肚子疼", "description": "Doro肚子有点不舒服...", "hunger_penalty": 10, "mood_penalty": 8, "weight": 5},
        {"id": "rain", "name": "下雨了", "description": "突然下起了雨，Doro被淋湿了...", "cleanliness_penalty": 15, "mood_penalty": 5, "weight": 6},
        {"id": "lose_toy", "name": "玩具丢了", "description": "Doro最喜欢的玩具找不到了...", "mood_penalty": 12, "weight": 5},
        {"id": "mosquito", "name": "蚊子叮咬", "description": "有只蚊子叮了Doro一下！好痒！", "mood_penalty": 6, "weight": 9},
        {"id": "bored", "name": "无聊透顶", "description": "好无聊啊...什么都不想做...", "mood_penalty": 8, "energy_penalty": 5, "weight": 10},
        {"id": "spicy", "name": "吃到辣椒", "description": "哇！好辣好辣！Doro不小心吃到了辣椒！", "hunger_penalty": 5, "mood_penalty": 5, "weight": 6},
        {"id": "messy", "name": "弄脏了", "description": "Doro玩的时候把自己弄脏了...", "cleanliness_penalty": 20, "mood_penalty": 3, "weight": 8},
        {"id": "forgetful", "name": "忘记事情", "description": "Doro想做什么来着...完全忘记了...", "mood_penalty": 4, "weight": 10},
    ]

    FORTUNE_LEVELS = [
        {"level": 5, "name": "大吉", "emoji": "🌟✨🌟", "stars": "⭐⭐⭐⭐⭐", "weight": 5},
        {"level": 4, "name": "中吉", "emoji": "🌟🌟", "stars": "⭐⭐⭐⭐", "weight": 15},
        {"level": 3, "name": "小吉", "emoji": "🌟", "stars": "⭐⭐⭐", "weight": 30},
        {"level": 2, "name": "末吉", "emoji": "💫", "stars": "⭐⭐", "weight": 30},
        {"level": 1, "name": "凶", "emoji": "💨", "stars": "⭐", "weight": 20},
    ]

    FORTUNE_TEXTS = {
        5: ["今天运势爆棚！万事顺遂，心想事成！", "大吉大利的一天！做什么都会很顺利哦~", "超级幸运日！快去尝试新事物吧！", "今天是被幸运女神眷顾的一天！"],
        4: ["今天运势不错，适合做重要决定！", "运势上佳，贵人相助，诸事顺利~", "好运气正在向你招手！", "今天会有小惊喜等着你哦~"],
        3: ["今天运势平稳，保持好心情！", "小有运气，适合稳步前进~", "今天适合做些轻松愉快的事情！", "运势尚可，记得多笑笑哦~"],
        2: ["今天运势一般，小心谨慎为妙~", "运势平淡，适合低调行事~", "今天适合休息放松，不要勉强~", "运势欠佳，但保持乐观会有转机~"],
        1: ["今天运势较低，建议多休息~", "运势不太理想，小心行事哦~", "今天适合独处思考，避免冲突~", "运势低迷，但明天会更好的！"],
    }

    LUCKY_COLORS = ["红色", "橙色", "黄色", "绿色", "蓝色", "紫色", "粉色", "白色", "黑色", "金色", "银色"]
    LUCKY_NUMBERS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    LUCKY_DIRECTIONS = ["东方", "南方", "西方", "北方", "东南", "东北", "西南", "西北"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        self._idle_interval = 120000
        self._weather_callback: Optional[Callable] = None
        self._weather_worker: Optional[WeatherQueryWorker] = None

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

    def generate_daily_fortune(self) -> Dict:
        today = date.today()
        date_str = today.strftime("%Y年%m月%d日")
        
        seed_str = f"{today.year}-{today.month}-{today.day}"
        seed_hash = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
        random.seed(seed_hash)
        
        total_weight = sum(f["weight"] for f in self.FORTUNE_LEVELS)
        r = random.uniform(0, total_weight)
        
        cumulative = 0
        selected_fortune = self.FORTUNE_LEVELS[0]
        for fortune in self.FORTUNE_LEVELS:
            cumulative += fortune["weight"]
            if r <= cumulative:
                selected_fortune = fortune
                break
        
        fortune_texts = self.FORTUNE_TEXTS.get(selected_fortune["level"], ["运势一般"])
        fortune_text = random.choice(fortune_texts)
        
        lucky_color = random.choice(self.LUCKY_COLORS)
        lucky_number = random.choice(self.LUCKY_NUMBERS)
        lucky_direction = random.choice(self.LUCKY_DIRECTIONS)
        
        random.seed()
        
        return {
            "date": date_str,
            "level": selected_fortune["level"],
            "name": selected_fortune["name"],
            "emoji": selected_fortune["emoji"],
            "stars": selected_fortune["stars"],
            "text": fortune_text,
            "lucky_items": f"幸运色：{lucky_color} | 幸运数字：{lucky_number} | 幸运方位：{lucky_direction}",
        }

    def query_weather(self, callback: Callable):
        self._weather_callback = callback
        
        settings = QSettings("DoroPet", "Settings")
        city = settings.value("weather_city", "", type=str)
        
        if self._weather_worker and self._weather_worker.isRunning():
            self._weather_worker.quit()
        
        self._weather_worker = WeatherQueryWorker(city if city else None, self)
        self._weather_worker.finished.connect(self._on_weather_result)
        self._weather_worker.error.connect(self._on_weather_error)
        self._weather_worker.start()

    def _on_weather_result(self, result: dict):
        if self._weather_callback:
            success = result.get("success", False)
            weather_data = {
                "location": result.get("location", "未知位置"),
                "temperature": result.get("temperature", "--"),
                "icon": result.get("icon", "🌤️"),
                "description": result.get("description", "暂无天气信息"),
                "humidity": result.get("humidity", "--"),
                "wind_speed": result.get("wind_speed", "--"),
                "weather_desc": result.get("weather_desc", ""),
                "forecast": result.get("forecast", []),
            }
            if not success:
                weather_data["error"] = result.get("error", "查询失败")
            self._weather_callback(success, weather_data)

    def _on_weather_error(self, error_msg: str):
        if self._weather_callback:
            self._weather_callback(False, {
                "location": "未知位置",
                "temperature": "--",
                "icon": "❓",
                "description": f"天气查询出错: {error_msg}",
                "error": error_msg
            })

    def get_random_fun_talk(self) -> str:
        talks = self.HAPPY_TALKS + [
            "想玩游戏吗？",
            "来互动吧~",
            "陪我玩嘛~",
            "今天有什么好玩的？",
            "要不要看看天气？",
            "今天运势如何？",
        ]
        return random.choice(talks)
