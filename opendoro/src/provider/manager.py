import copy
import os
from typing import Optional, List, Dict, Any, Type
from .entities import ProviderType, ProviderConfig, LLMResponse
from .provider import AbstractProvider, LLMProvider, TTSProvider, STTProvider, ImageProvider
from .register import provider_cls_map, get_provider_metadata
from src.core.logger import logger


class ProviderManager:
    _instance = None
    
    def __init__(self):
        if ProviderManager._instance is not None:
            raise RuntimeError("Use get_instance() to get ProviderManager instance")
        
        self._llm_providers: Dict[str, LLMProvider] = {}
        self._tts_providers: Dict[str, TTSProvider] = {}
        self._stt_providers: Dict[str, STTProvider] = {}
        self._image_providers: Dict[str, ImageProvider] = {}
        
        self._active_llm: Optional[str] = None
        self._active_tts: Optional[str] = None
        self._active_stt: Optional[str] = None
        self._active_image: Optional[str] = None
        
        ProviderManager._instance = self
    
    @classmethod
    def get_instance(cls) -> 'ProviderManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        if cls._instance is not None:
            for provider in list(cls._instance._llm_providers.values()):
                provider.close()
            for provider in list(cls._instance._tts_providers.values()):
                provider.close()
            for provider in list(cls._instance._stt_providers.values()):
                provider.close()
            for provider in list(cls._instance._image_providers.values()):
                provider.close()
            cls._instance = None
    
    def load_provider(self, config: Dict) -> Optional[AbstractProvider]:
        provider_type = config.get('type', '')
        provider_id = config.get('id', '')
        expected_category = config.get('provider_type', 'chat_completion')
        
        if not provider_type or not provider_id:
            logger.warning(f"Invalid provider config: missing type or id")
            return None
        
        metadata = get_provider_metadata(provider_type)
        if metadata is None:
            self._dynamic_import_provider(provider_type)
            metadata = get_provider_metadata(provider_type)
        
        if metadata is None:
            logger.warning(f"Provider type '{provider_type}' not found in registry")
            return None
        
        if not self._validate_provider_type(metadata.provider_type, expected_category):
            logger.warning(f"Provider type mismatch: expected {expected_category}, got {metadata.provider_type}")
            return None
        
        provider_config = ProviderConfig.from_dict(config)
        
        try:
            provider_cls: Type[AbstractProvider] = metadata.cls_type
            provider = provider_cls(provider_config)
            
            match metadata.provider_type:
                case ProviderType.CHAT_COMPLETION:
                    self._llm_providers[provider_id] = provider
                    if config.get('is_active', False):
                        self._active_llm = provider_id
                    logger.info(f"Loaded LLM provider: {provider_id} ({provider_type})")
                    
                case ProviderType.TEXT_TO_SPEECH:
                    self._tts_providers[provider_id] = provider
                    if config.get('is_active', False):
                        self._active_tts = provider_id
                    logger.info(f"Loaded TTS provider: {provider_id} ({provider_type})")
                    
                case ProviderType.SPEECH_TO_TEXT:
                    self._stt_providers[provider_id] = provider
                    if config.get('is_active', False):
                        self._active_stt = provider_id
                    logger.info(f"Loaded STT provider: {provider_id} ({provider_type})")
                    
                case ProviderType.IMAGE_GENERATION:
                    self._image_providers[provider_id] = provider
                    if config.get('is_active', False):
                        self._active_image = provider_id
                    logger.info(f"Loaded Image provider: {provider_id} ({provider_type})")
            
            return provider
            
        except Exception as e:
            logger.error(f"Failed to load provider {provider_id}: {e}")
            return None
    
    def _validate_provider_type(self, actual_type: ProviderType, expected_category: str) -> bool:
        category_map = {
            'chat_completion': ProviderType.CHAT_COMPLETION,
            'text_to_speech': ProviderType.TEXT_TO_SPEECH,
            'speech_to_text': ProviderType.SPEECH_TO_TEXT,
            'image_generation': ProviderType.IMAGE_GENERATION,
        }
        expected_type = category_map.get(expected_category)
        return expected_type is not None and actual_type == expected_type
    
    def load_providers_from_db(self, db) -> None:
        self._llm_providers.clear()
        self._tts_providers.clear()
        self._stt_providers.clear()
        self._image_providers.clear()
        self._active_llm = None
        self._active_tts = None
        self._active_stt = None
        self._active_image = None
        
        llm_models = db.get_models()
        for model in llm_models:
            config = self._db_row_to_config(model, 'llm')
            self.load_provider(config)
        
        tts_models = db.get_tts_models()
        for model in tts_models:
            config = self._db_row_to_config(model, 'tts')
            self.load_provider(config)
        
        image_models = db.get_image_models()
        for model in image_models:
            config = self._db_row_to_config(model, 'image')
            self.load_provider(config)
        
        logger.info(f"Loaded {len(self._llm_providers)} LLM, {len(self._tts_providers)} TTS, {len(self._image_providers)} Image providers")
    
    def _db_row_to_config(self, row: tuple, provider_cat: str) -> Dict:
        if provider_cat == 'llm':
            return {
                'id': str(row[0]),
                'name': row[1],
                'type': self._provider_name_to_type(row[2], 'llm'),
                'provider_type': 'chat_completion',
                'api_key': row[3],
                'base_url': row[4],
                'model': row[5],
                'is_active': bool(row[6]),
                'is_visual': bool(row[7]) if len(row) > 7 else False,
                'is_thinking': bool(row[8]) if len(row) > 8 else False,
                'proxy': row[9] if len(row) > 9 else '',
            }
        elif provider_cat == 'tts':
            return {
                'id': str(row[0]),
                'name': row[1],
                'type': self._provider_name_to_type(row[2], 'tts'),
                'provider_type': 'text_to_speech',
                'api_key': row[3],
                'base_url': row[4],
                'model': row[5],
                'voice': row[6] if len(row) > 6 else '',
                'is_active': bool(row[7]) if len(row) > 7 else False,
                'proxy': row[8] if len(row) > 8 else '',
            }
        elif provider_cat == 'image':
            return {
                'id': str(row[0]),
                'name': row[1],
                'type': self._provider_name_to_type(row[2], 'image'),
                'provider_type': 'image_generation',
                'base_url': row[3],
                'api_key': row[4],
                'model': row[5],
                'is_active': bool(row[6]) if len(row) > 6 else False,
                'proxy': row[7] if len(row) > 7 else '',
            }
        return {}
    
    def _provider_name_to_type(self, name: str, category: str) -> str:
        name_lower = (name or '').lower().strip()
        
        if category == 'llm':
            type_map = {
                'openai': 'openai_chat_completion',
                'deepseek': 'deepseek_chat_completion',
                'anthropic': 'anthropic_chat_completion',
                'claude': 'anthropic_chat_completion',
                'ollama': 'ollama_chat_completion',
                'moonshot': 'moonshot_chat_completion',
                'kimi': 'moonshot_chat_completion',
                'gemini': 'gemini_chat_completion',
                'google': 'gemini_chat_completion',
                'groq': 'groq_chat_completion',
                'zhipu': 'zhipu_chat_completion',
                '智谱': 'zhipu_chat_completion',
                'siliconflow': 'openai_chat_completion',
                'custom': 'openai_chat_completion',
            }
            default_type = 'openai_chat_completion'
        elif category == 'tts':
            type_map = {
                'edge': 'edge_tts',
                'openai': 'openai_tts',
                'siliconflow': 'openai_tts',
                'fishaudio': 'openai_tts',
                'gemini': 'gemini_tts',
                'custom': 'openai_tts',
            }
            default_type = 'edge_tts'
        elif category == 'image':
            type_map = {
                'openai': 'openai_image',
                'dall-e': 'openai_image',
                'siliconflow': 'openai_image',
                'stability': 'openai_image',
                'gitee': 'openai_image',
                'custom': 'openai_image',
            }
            default_type = 'openai_image'
        else:
            return 'openai_chat_completion'
        
        for key, value in type_map.items():
            if key in name_lower:
                return value
        
        logger.debug(f"Provider name '{name}' not matched for category '{category}', using default: {default_type}")
        return default_type
    
    def _dynamic_import_provider(self, provider_type: str) -> None:
        try:
            if provider_type == 'openai_chat_completion':
                from .sources.openai_source import ProviderOpenAI
            elif provider_type == 'deepseek_chat_completion':
                from .sources.deepseek_source import ProviderDeepSeek
            elif provider_type == 'anthropic_chat_completion':
                from .sources.anthropic_source import ProviderAnthropic
            elif provider_type == 'ollama_chat_completion':
                from .sources.ollama_source import ProviderOllama
            elif provider_type == 'moonshot_chat_completion':
                from .sources.moonshot_source import ProviderMoonshot
            elif provider_type == 'gemini_chat_completion':
                from .sources.gemini_source import ProviderGemini
            elif provider_type == 'groq_chat_completion':
                from .sources.groq_source import ProviderGroq
            elif provider_type == 'zhipu_chat_completion':
                from .sources.zhipu_source import ProviderZhipu
            elif provider_type == 'edge_tts':
                from .sources.edge_tts_source import ProviderEdgeTTS
            elif provider_type == 'openai_tts':
                from .sources.openai_tts_source import ProviderOpenAITTS
            elif provider_type == 'gemini_tts':
                from .sources.gemini_tts_source import ProviderGeminiTTS
            elif provider_type == 'openai_image':
                from .sources.openai_image_source import ProviderOpenAIImage
        except ImportError as e:
            logger.warning(f"Failed to import provider {provider_type}: {e}")
    
    def get_llm_provider_by_model(self, model: str) -> Optional[LLMProvider]:
        for provider_id, provider in self._llm_providers.items():
            if provider.meta().model == model:
                return provider
        return None
    
    def get_llm_provider(self, provider_id: Optional[str] = None) -> Optional[LLMProvider]:
        if provider_id:
            return self._llm_providers.get(provider_id)
        if self._active_llm:
            return self._llm_providers.get(self._active_llm)
        if self._llm_providers:
            return list(self._llm_providers.values())[0]
        return None
    
    def get_tts_provider(self, provider_id: Optional[str] = None) -> Optional[TTSProvider]:
        if provider_id:
            return self._tts_providers.get(provider_id)
        if self._active_tts:
            return self._tts_providers.get(self._active_tts)
        if self._tts_providers:
            return list(self._tts_providers.values())[0]
        return None
    
    def get_image_provider(self, provider_id: Optional[str] = None) -> Optional[ImageProvider]:
        if provider_id:
            return self._image_providers.get(provider_id)
        if self._active_image:
            return self._image_providers.get(self._active_image)
        if self._image_providers:
            return list(self._image_providers.values())[0]
        return None
    
    def get_stt_provider(self, provider_id: Optional[str] = None) -> Optional[STTProvider]:
        if provider_id:
            return self._stt_providers.get(provider_id)
        if self._active_stt:
            return self._stt_providers.get(self._active_stt)
        if self._stt_providers:
            return list(self._stt_providers.values())[0]
        return None
    
    def set_active_llm(self, provider_id: str) -> bool:
        if provider_id in self._llm_providers:
            self._active_llm = provider_id
            return True
        return False
    
    def set_active_tts(self, provider_id: str) -> bool:
        if provider_id in self._tts_providers:
            self._active_tts = provider_id
            return True
        return False
    
    def set_active_image(self, provider_id: str) -> bool:
        if provider_id in self._image_providers:
            self._active_image = provider_id
            return True
        return False
    
    def unload_provider(self, provider_id: str) -> bool:
        unloaded = False
        
        if provider_id in self._llm_providers:
            self._llm_providers[provider_id].close()
            del self._llm_providers[provider_id]
            if self._active_llm == provider_id:
                self._active_llm = None
            unloaded = True
            
        if provider_id in self._tts_providers:
            self._tts_providers[provider_id].close()
            del self._tts_providers[provider_id]
            if self._active_tts == provider_id:
                self._active_tts = None
            unloaded = True
            
        if provider_id in self._stt_providers:
            self._stt_providers[provider_id].close()
            del self._stt_providers[provider_id]
            if self._active_stt == provider_id:
                self._active_stt = None
            unloaded = True
            
        if provider_id in self._image_providers:
            self._image_providers[provider_id].close()
            del self._image_providers[provider_id]
            if self._active_image == provider_id:
                self._active_image = None
            unloaded = True
        
        return unloaded
    
    def reload_provider(self, config: Dict) -> Optional[AbstractProvider]:
        provider_id = config.get('id', '')
        if provider_id:
            self.unload_provider(provider_id)
        return self.load_provider(config)
    
    def get_all_llm_providers(self) -> Dict[str, LLMProvider]:
        return self._llm_providers.copy()
    
    def get_all_tts_providers(self) -> Dict[str, TTSProvider]:
        return self._tts_providers.copy()
    
    def get_all_image_providers(self) -> Dict[str, ImageProvider]:
        return self._image_providers.copy()
    
    def get_active_llm_id(self) -> Optional[str]:
        return self._active_llm
    
    def get_active_tts_id(self) -> Optional[str]:
        return self._active_tts
    
    def get_active_image_id(self) -> Optional[str]:
        return self._active_image
    
    def get_available_llm_types(self) -> List[str]:
        return [pm.type for pm in provider_cls_map.values() 
                if pm.provider_type == ProviderType.CHAT_COMPLETION]
    
    def get_available_tts_types(self) -> List[str]:
        return [pm.type for pm in provider_cls_map.values() 
                if pm.provider_type == ProviderType.TEXT_TO_SPEECH]
    
    def get_available_image_types(self) -> List[str]:
        return [pm.type for pm in provider_cls_map.values() 
                if pm.provider_type == ProviderType.IMAGE_GENERATION]
