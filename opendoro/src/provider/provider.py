import abc
from typing import Optional, List, Dict, Any, Generator, AsyncGenerator, Callable
from .entities import (
    ProviderType, ProviderMeta, LLMResponse, TTSResponse, 
    ImageResponse, STTResponse, ProviderConfig, ToolCall, ToolResult
)


class AbstractProvider(abc.ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.model_name = config.model
        self._client = None
        
    def set_model(self, model_name: str) -> None:
        self.model_name = model_name
        
    def get_model(self) -> str:
        return self.model_name
    
    def meta(self) -> ProviderMeta:
        return ProviderMeta(
            id=self.config.id,
            model=self.model_name,
            type=self.config.type,
            provider_type=self._get_provider_type()
        )
    
    @abc.abstractmethod
    def _get_provider_type(self) -> ProviderType:
        pass
    
    def test(self) -> bool:
        return True
    
    def get_current_key(self) -> str:
        return self.config.api_key
    
    def get_base_url(self) -> str:
        return self.config.base_url
    
    def close(self):
        if self._client and hasattr(self._client, 'close'):
            self._client.close()


class LLMProvider(AbstractProvider):
    @abc.abstractmethod
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.CHAT_COMPLETION
    
    def get_client(self):
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    @abc.abstractmethod
    def _create_client(self):
        pass
    
    @abc.abstractmethod
    def chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        pass
    
    @abc.abstractmethod
    def chat_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[LLMResponse, None, None]:
        pass
    
    def get_models(self) -> List[str]:
        return []
    
    def supports_vision(self) -> bool:
        return self.config.is_visual
    
    def supports_thinking(self) -> bool:
        return self.config.is_thinking


class TTSProvider(AbstractProvider):
    @abc.abstractmethod
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.TEXT_TO_SPEECH
    
    @abc.abstractmethod
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> TTSResponse:
        pass
    
    def synthesize_stream(
        self,
        text_queue,
        audio_queue,
        voice: Optional[str] = None,
        **kwargs
    ):
        pass
    
    def supports_stream(self) -> bool:
        return False
    
    def get_voices(self) -> List[Dict]:
        return []


class STTProvider(AbstractProvider):
    @abc.abstractmethod
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.SPEECH_TO_TEXT
    
    @abc.abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> STTResponse:
        pass


class ImageProvider(AbstractProvider):
    @abc.abstractmethod
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.IMAGE_GENERATION
    
    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs
    ) -> ImageResponse:
        pass
    
    def get_supported_sizes(self) -> List[str]:
        return ["1024x1024", "512x512", "256x256"]
    
    def get_supported_qualities(self) -> List[str]:
        return ["standard", "hd"]
