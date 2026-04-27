import logging
from typing import Dict, Set, Optional, List, Callable

logger = logging.getLogger("DoroPet.Agent")


class SkillEnabledState:
    _instance: Optional["SkillEnabledState"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if SkillEnabledState._initialized:
            return
        SkillEnabledState._initialized = True
        self._states: Dict[str, bool] = {}
        self._listeners: List[Callable] = []

    @classmethod
    def get_instance(cls) -> "SkillEnabledState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_from_settings(self):
        try:
            from PyQt5.QtCore import QSettings
            settings = QSettings("DoroPet", "Settings")
            for key in settings.allKeys():
                if key.startswith("skill_") and key.endswith("_enabled"):
                    skill_name = key[len("skill_"):-len("_enabled")]
                    self._states[skill_name] = settings.value(key, True, type=bool)
            logger.info(f"[SkillState] Loaded {len(self._states)} skill states from settings")
        except ImportError:
            pass

    def save_to_settings(self, skill_name: str, enabled: bool):
        self._states[skill_name] = enabled
        try:
            from PyQt5.QtCore import QSettings
            settings = QSettings("DoroPet", "Settings")
            settings.setValue(f"skill_{skill_name}_enabled", enabled)
            settings.sync()
        except ImportError:
            pass
        self._notify_listeners()

    def is_enabled(self, skill_name: str) -> bool:
        if skill_name not in self._states:
            return True
        return self._states[skill_name]

    def set_enabled(self, skill_name: str, enabled: bool):
        self.save_to_settings(skill_name, enabled)

    def get_enabled_skill_names(self, all_skill_names: List[str]) -> List[str]:
        return [name for name in all_skill_names if self.is_enabled(name)]

    def get_disabled_skill_names(self, all_skill_names: List[str]) -> List[str]:
        return [name for name in all_skill_names if not self.is_enabled(name)]

    def get_all_states(self) -> Dict[str, bool]:
        return dict(self._states)

    def add_listener(self, callback: Callable):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for cb in self._listeners:
            try:
                cb()
            except Exception as e:
                logger.error(f"[SkillState] Listener error: {e}")


class SkillCategory:
    SEARCH = "搜索"
    DOCUMENT = "文档"
    CODE = "代码"
    DESIGN = "设计"
    UTILITY = "工具"
    CHAT = "聊天"
    DEPLOY = "部署"
    UNCATEGORIZED = "未分类"

    _CATEGORY_MAP: Dict[str, str] = {}

    @classmethod
    def categorize(cls, skill_name: str, description: str = "") -> str:
        if skill_name in cls._CATEGORY_MAP:
            return cls._CATEGORY_MAP[skill_name]

        name_lower = skill_name.lower()
        desc_lower = description.lower()

        if any(kw in name_lower or kw in desc_lower for kw in ("search", "baidu", "bing", "热搜", "trending", "fetch")):
            return cls.SEARCH
        if any(kw in name_lower or kw in desc_lower for kw in ("docx", "pptx", "pdf", "excel", "xlsx", "word", "文档")):
            return cls.DOCUMENT
        if any(kw in name_lower or kw in desc_lower for kw in ("code", "python", "script", "run", "编程", "代码")):
            return cls.CODE
        if any(kw in name_lower or kw in desc_lower for kw in ("design", "frontend", "react", "ui", "css", "设计", "前端")):
            return cls.DESIGN
        if any(kw in name_lower or kw in desc_lower for kw in ("deploy", "vercel", "部署")):
            return cls.DEPLOY
        if any(kw in name_lower or kw in desc_lower for kw in ("chat", "bot", "onebot", "qq", "聊天")):
            return cls.CHAT
        if any(kw in name_lower or kw in desc_lower for kw in ("weather", "天气", "web-fetch")):
            return cls.UTILITY

        return cls.UNCATEGORIZED

    @classmethod
    def set_category(cls, skill_name: str, category: str):
        cls._CATEGORY_MAP[skill_name] = category

    @classmethod
    def load_categories(cls):
        try:
            from PyQt5.QtCore import QSettings
            settings = QSettings("DoroPet", "SkillCategories")
            for key in settings.allKeys():
                cls._CATEGORY_MAP[key] = settings.value(key, cls.UNCATEGORIZED)
        except ImportError:
            pass

    @classmethod
    def save_category(cls, skill_name: str, category: str):
        cls._CATEGORY_MAP[skill_name] = category
        try:
            from PyQt5.QtCore import QSettings
            settings = QSettings("DoroPet", "SkillCategories")
            settings.setValue(skill_name, category)
            settings.sync()
        except ImportError:
            pass

    @classmethod
    def get_all_categories(cls) -> List[str]:
        return [cls.SEARCH, cls.DOCUMENT, cls.CODE, cls.DESIGN, cls.UTILITY, cls.CHAT, cls.DEPLOY, cls.UNCATEGORIZED]

    @classmethod
    def get_category_icon(cls, category: str) -> str:
        icons = {
            cls.SEARCH: "🔍",
            cls.DOCUMENT: "📄",
            cls.CODE: "💻",
            cls.DESIGN: "🎨",
            cls.UTILITY: "🔧",
            cls.CHAT: "💬",
            cls.DEPLOY: "🚀",
            cls.UNCATEGORIZED: "📦",
        }
        return icons.get(category, "📦")


SkillCategory.load_categories()
