from src.core.database import DatabaseManager, ChatDatabase, PersonaDatabase, CacheDatabase


class QuickChatDependencies:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if QuickChatDependencies._initialized:
            return

        self._db_manager = DatabaseManager()
        self._chat_db = self._db_manager.chat
        self._persona_db = self._db_manager.personas
        self._cache_db = self._db_manager.cache
        self._config_db = self._db_manager.config

        QuickChatDependencies._initialized = True

    @property
    def db_manager(self) -> DatabaseManager:
        return self._db_manager

    @property
    def chat_db(self):
        return self._chat_db

    @property
    def persona_db(self):
        return self._persona_db

    @property
    def cache_db(self):
        return self._cache_db

    @property
    def config_db(self):
        return self._config_db

    def get_active_model(self):
        return self._config_db.get_active_model()

    def get_active_tts_model(self):
        return self._config_db.get_active_tts_model()

    def reset(self):
        QuickChatDependencies._instance = None
        QuickChatDependencies._initialized = False


def get_quick_chat_deps() -> QuickChatDependencies:
    return QuickChatDependencies()
