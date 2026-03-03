import os
import tempfile
from typing import Optional, List, Dict
from openai import OpenAI
import httpx

from ..provider import TTSProvider
from ..entities import TTSResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter, TTS_CONFIG_FIELDS
from src.core.logger import logger


@register_provider_adapter(
    "openai_tts",
    "OpenAI 兼容 TTS API",
    provider_type=ProviderType.TEXT_TO_SPEECH,
    default_config_tmpl={
        "base_url": "https://api.openai.com/v1",
        "model": "tts-1",
        "voice": "alloy",
    },
    provider_display_name="OpenAI TTS",
    config_fields=TTS_CONFIG_FIELDS
)
class ProviderOpenAITTS(TTSProvider):
    DEFAULT_VOICES = [
        {"id": "alloy", "name": "Alloy", "language": "en"},
        {"id": "echo", "name": "Echo", "language": "en"},
        {"id": "fable", "name": "Fable", "language": "en"},
        {"id": "onyx", "name": "Onyx", "language": "en"},
        {"id": "nova", "name": "Nova", "language": "en"},
        {"id": "shimmer", "name": "Shimmer", "language": "en"},
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._http_client = None
    
    def _get_provider_type(self):
        from ..entities import ProviderType
        return ProviderType.TEXT_TO_SPEECH
    
    def get_client(self) -> OpenAI:
        if self._client is None:
            self._http_client = httpx.Client(timeout=self.config.timeout)
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                http_client=self._http_client
            )
        return self._client
    
    def close(self):
        if self._http_client:
            try:
                self._http_client.close()
            except:
                pass
        super().close()
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> TTSResponse:
        client = self.get_client()
        
        voice_id = voice or self.config.voice or "alloy"
        model = self.model_name or "tts-1"
        response_format = kwargs.get("response_format", "mp3")
        
        response = client.audio.speech.create(
            model=model,
            voice=voice_id,
            input=text,
            speed=speed,
            response_format=response_format
        )
        
        with tempfile.NamedTemporaryFile(suffix=f".{response_format}", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        response.stream_to_file(output_path)
        
        return TTSResponse(
            audio_path=output_path,
            format=response_format
        )
    
    def get_voices(self) -> List[Dict]:
        return self.DEFAULT_VOICES
    
    def test(self) -> bool:
        try:
            self.synthesize("测试语音", "alloy")
            return True
        except Exception as e:
            logger.error(f"OpenAI TTS test failed: {e}")
            return False
