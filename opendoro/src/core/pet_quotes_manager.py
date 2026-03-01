import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, STATUS_THRESHOLDS
)


class PetQuotesManager(QObject):
    quote_changed = pyqtSignal(str)
    status_description_changed = pyqtSignal(str)

    QUOTES_LIBRARY: Dict[str, Dict[str, List[str]]] = {
        ATTR_HUNGER: {
            "critical": [
                "肚子好饿...想吃饭...",
                "有没有吃的呀...饿死了...",
                "欧润吉...欧润吉...",
                "肚子咕噜咕噜叫...",
            ],
            "warning": [
                "有点饿了~",
                "想吃点零食~",
                "欧润吉！",
                "肚子有点空空的...",
            ],
            "good": [
                "吃饱饱~好满足！",
                "刚刚吃得好饱！",
                "欧润吉真好吃！",
                "肚子暖暖的~",
            ],
        },
        ATTR_MOOD: {
            "critical": [
                "呜呜...不开心...",
                "想找人说说话...",
                "有点难过...",
                "能不能陪我玩...",
            ],
            "warning": [
                "有点无聊...",
                "想玩~想玩~",
                "今天没什么精神...",
                "想出去走走...",
            ],
            "good": [
                "好开心！",
                "今天心情超好！",
                "啦啦啦~",
                "感觉棒极了！",
            ],
        },
        ATTR_CLEANLINESS: {
            "critical": [
                "身上好脏...",
                "想洗澡...",
                "黏糊糊的好难受...",
                "呜呜我好脏...",
            ],
            "warning": [
                "有点脏脏的~",
                "该洗澡啦~",
                "感觉不太清爽...",
                "想要擦擦...",
            ],
            "good": [
                "香喷喷的~",
                "刚刚洗好舒服！",
                "干干净净！",
                "清爽极了！",
            ],
        },
        ATTR_ENERGY: {
            "critical": [
                "好困...想睡觉...",
                "眼睛睁不开了...",
                "没力气了...",
                "让我睡一会...",
            ],
            "warning": [
                "有点累了~",
                "想休息一下~",
                "打哈欠...",
                "精神不太好...",
            ],
            "good": [
                "精力充沛！",
                "元气满满！",
                "今天很有精神！",
                "充满活力！",
            ],
        },
    }

    SPECIAL_QUOTES: Dict[str, List[str]] = {
        "all_good": [
            "感觉超级棒！什么都很好！",
            "今天是最棒的一天！",
            "幸福满满~",
            "什么都满意！",
        ],
        "all_critical": [
            "呜呜...什么都不好了...",
            "好难过...需要照顾...",
            "快来帮帮我...",
        ],
        "mixed": [
            "有开心的事，也有不开心的事...",
            "今天起起伏伏的...",
        ],
    }

    TIME_GREETINGS: Dict[str, Tuple[str, Tuple[int, int], List[str]]] = {
        "morning": (
            "早上好",
            (5, 11),
            [
                "新的一天开始啦！",
                "早安~今天也要开心哦！",
                "太阳出来啦~",
                "睡得好香！",
            ],
        ),
        "noon": (
            "中午好",
            (11, 14),
            [
                "中午啦~该吃饭了！",
                "太阳好大！",
                "午休时间到~",
            ],
        ),
        "afternoon": (
            "下午好",
            (14, 18),
            [
                "下午茶时间~",
                "今天过得怎么样？",
                "还有半天加油！",
            ],
        ),
        "evening": (
            "晚上好",
            (18, 22),
            [
                "天黑啦~",
                "晚上想做什么呢？",
                "今天辛苦了！",
            ],
        ),
        "night": (
            "夜深了",
            (22, 5),
            [
                "该睡觉啦~",
                "晚安~做个好梦！",
                "星星出来啦~",
                "嘘...大家都睡了...",
            ],
        ),
    }

    STATUS_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
        ATTR_HUNGER: {
            "critical": "饿得没力气了",
            "warning": "肚子有点饿",
            "good": "饱饱的",
        },
        ATTR_MOOD: {
            "critical": "情绪低落",
            "warning": "有点无聊",
            "good": "心情愉快",
        },
        ATTR_CLEANLINESS: {
            "critical": "需要洗澡",
            "warning": "有点脏了",
            "good": "干干净净",
        },
        ATTR_ENERGY: {
            "critical": "困得不行",
            "warning": "有点疲惫",
            "good": "精神饱满",
        },
    }

    PET_NAME = "Doro"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_quote = ""
        self._current_description = ""

    def get_status(self, value: float) -> str:
        if value < STATUS_THRESHOLDS["critical"]:
            return "critical"
        elif value < STATUS_THRESHOLDS["warning"]:
            return "warning"
        return "good"

    def get_time_period(self) -> str:
        hour = datetime.now().hour
        for period, (_, (start, end), _) in self.TIME_GREETINGS.items():
            if start <= end:
                if start <= hour < end:
                    return period
            else:
                if hour >= start or hour < end:
                    return period
        return "morning"

    def get_greeting(self) -> str:
        period = self.get_time_period()
        greeting_info = self.TIME_GREETINGS.get(period, self.TIME_GREETINGS["morning"])
        greeting_text = greeting_info[0]
        sub_quotes = greeting_info[2]
        sub_greeting = random.choice(sub_quotes)
        return f"{greeting_text}！{sub_greeting}"

    def get_mood_quote(self, attributes: Dict[str, float]) -> str:
        statuses = {
            name: self.get_status(value)
            for name, value in attributes.items()
        }

        critical_attrs = [name for name, status in statuses.items() if status == "critical"]
        warning_attrs = [name for name, status in statuses.items() if status == "warning"]
        good_attrs = [name for name, status in statuses.items() if status == "good"]

        if len(critical_attrs) >= 3:
            quotes = self.SPECIAL_QUOTES["all_critical"]
        elif len(good_attrs) == 4:
            quotes = self.SPECIAL_QUOTES["all_good"]
        elif critical_attrs:
            attr = random.choice(critical_attrs)
            quotes = self.QUOTES_LIBRARY[attr]["critical"]
        elif warning_attrs:
            attr = random.choice(warning_attrs)
            quotes = self.QUOTES_LIBRARY[attr]["warning"]
        else:
            attr = random.choice(list(attributes.keys()))
            quotes = self.QUOTES_LIBRARY[attr]["good"]

        quote = random.choice(quotes)
        self._current_quote = quote
        self.quote_changed.emit(quote)
        return quote

    def get_status_description(self, attributes: Dict[str, float]) -> str:
        descriptions = []
        priority_order = [ATTR_HUNGER, ATTR_ENERGY, ATTR_MOOD, ATTR_CLEANLINESS]

        for attr in priority_order:
            if attr in attributes:
                status = self.get_status(attributes[attr])
                desc = self.STATUS_DESCRIPTIONS[attr][status]
                if status == "critical":
                    descriptions.insert(0, desc)
                elif status == "warning":
                    descriptions.append(desc)

        if not descriptions:
            return "状态很好"

        if len(descriptions) == 1:
            result = descriptions[0]
        elif len(descriptions) == 2:
            result = f"{descriptions[0]}，{descriptions[1]}"
        else:
            result = f"{descriptions[0]}，还有点{descriptions[1]}"

        self._current_description = result
        self.status_description_changed.emit(result)
        return result

    def get_current_quote(self) -> str:
        return self._current_quote

    def get_current_description(self) -> str:
        return self._current_description

    def get_interaction_response(self, interaction_type: str) -> str:
        responses = {
            "feed": [
                "好吃！谢谢！",
                "欧润吉！最喜欢了！",
                "吃饱饱~",
                " yummy！",
            ],
            "play": [
                "好玩！再来！",
                "哈哈好开心！",
                "还要玩！",
                "太棒了！",
            ],
            "clean": [
                "香香的~",
                "洗得好舒服！",
                "干净啦！",
                "清爽！",
            ],
            "rest": [
                "睡个好觉~",
                "哈欠...晚安...",
                "休息一下~",
                "zzZ...",
            ],
        }
        quotes = responses.get(interaction_type, ["谢谢！"])
        return random.choice(quotes)

    def refresh_quote(self, attributes: Dict[str, float]) -> str:
        return self.get_mood_quote(attributes)
