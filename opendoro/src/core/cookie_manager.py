import os
import json
from typing import Dict, Optional
from src.core.logger import logger


class CookieManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CookieManager()
        return cls._instance

    def __init__(self):
        self._cookies: Dict[str, Dict] = {}
        self._cookie_dir = os.path.join(
            os.environ.get('LOCALAPPDATA', os.getcwd()),
            'DoroPet',
            'cookies'
        )
        self._load_cookies()

    def _get_cookie_file(self, platform: str) -> str:
        return os.path.join(self._cookie_dir, f"{platform.lower()}_cookies.json")

    def _load_cookies(self):
        os.makedirs(self._cookie_dir, exist_ok=True)
        
        platforms = ['netease', 'qq', 'kugou', 'kuwo', 'migu']
        for platform in platforms:
            cookie_file = self._get_cookie_file(platform)
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        self._cookies[platform] = json.load(f)
                    logger.info(f"[CookieManager] Loaded cookies for {platform}")
                except Exception as e:
                    logger.warning(f"[CookieManager] Failed to load cookies for {platform}: {e}")

    def _save_cookies(self, platform: str):
        if platform not in self._cookies:
            return
        
        os.makedirs(self._cookie_dir, exist_ok=True)
        cookie_file = self._get_cookie_file(platform)
        try:
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(self._cookies[platform], f, indent=2, ensure_ascii=False)
            logger.info(f"[CookieManager] Saved cookies for {platform}")
        except Exception as e:
            logger.error(f"[CookieManager] Failed to save cookies for {platform}: {e}")

    def set_cookies(self, platform: str, cookies: Dict):
        self._cookies[platform.lower()] = cookies
        self._save_cookies(platform.lower())

    def get_cookies(self, platform: str) -> Dict:
        return self._cookies.get(platform.lower(), {})

    def has_cookies(self, platform: str) -> bool:
        return bool(self._cookies.get(platform.lower()))

    def clear_cookies(self, platform: str):
        if platform.lower() in self._cookies:
            del self._cookies[platform.lower()]
        
        cookie_file = self._get_cookie_file(platform.lower())
        if os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
                logger.info(f"[CookieManager] Cleared cookies for {platform}")
            except Exception as e:
                logger.error(f"[CookieManager] Failed to clear cookies for {platform}: {e}")

    def get_all_cookies(self) -> Dict[str, Dict]:
        return self._cookies.copy()

    @staticmethod
    def parse_browser_cookies(cookie_str: str) -> Dict:
        result = {}
        for line in cookie_str.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 7:
                name = parts[5]
                value = parts[6]
                if name and value:
                    result[name] = value
        return result

    @staticmethod
    def parse_netscape_cookies(cookie_str: str) -> Dict:
        result = {}
        for line in cookie_str.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('cookie'):
                continue
            parts = line.split('\t')
            if len(parts) >= 7:
                name = parts[5]
                value = parts[6]
                if name and value:
                    result[name] = value
        return result
