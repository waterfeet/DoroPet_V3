import os
import tempfile
import wave
from typing import Optional, List, Dict
from ..provider import TTSProvider
from ..entities import TTSResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter, TTS_CONFIG_FIELDS
from src.core.logger import logger

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False
    genai = None
    types = None


@register_provider_adapter(
    "gemini_tts",
    "Google Gemini TTS",
    provider_type=ProviderType.TEXT_TO_SPEECH,
    default_config_tmpl={
        "model": "gemini-2.5-flash-preview-tts",
        "voice": "Kore",
    },
    provider_display_name="Gemini TTS",
    config_fields=TTS_CONFIG_FIELDS
)
class ProviderGeminiTTS(TTSProvider):
    DEFAULT_VOICES = [
        {"id": "Kore", "name": "Kore", "language": "en-US"},
        {"id": "Charon", "name": "Charon", "language": "en-US"},
        {"id": "Fenrir", "name": "Fenrir", "language": "en-US"},
        {"id": "Aoede", "name": "Aoede", "language": "en-US"},
        {"id": "Leda", "name": "Leda", "language": "en-US"},
        {"id": "Orus", "name": "Orus", "language": "en-US"},
        {"id": "Puck", "name": "Puck", "language": "en-US"},
        {"id": "Sulafat", "name": "Sulafat", "language": "en-US"},
        {"id": "Zephyr", "name": "Zephyr", "language": "en-US"},
        {"id": "Algenib", "name": "Algenib", "language": "en-US"},
        {"id": "Despina", "name": "Despina", "language": "en-US"},
        {"id": "Enceladus", "name": "Enceladus", "language": "en-US"},
        {"id": "Erinome", "name": "Erinome", "language": "en-US"},
        {"id": "Iapetus", "name": "Iapetus", "language": "en-US"},
        {"id": "Rasalgethi", "name": "Rasalgethi", "language": "en-US"},
        {"id": "Sadachbia", "name": "Sadachbia", "language": "en-US"},
        {"id": "Sadaltager", "name": "Sadaltager", "language": "en-US"},
        {"id": "Schedar", "name": "Schedar", "language": "en-US"},
        {"id": "Umbriel", "name": "Umbriel", "language": "en-US"},
        {"id": "Vindemiatrix", "name": "Vindemiatrix", "language": "en-US"},
        {"id": "Zubenelgenubi", "name": "Zubenelgenubi", "language": "en-US"},
        {"id": "Achernar", "name": "Achernar", "language": "en-US"},
        {"id": "Alnilam", "name": "Alnilam", "language": "en-US"},
        {"id": "Achird", "name": "Achird", "language": "en-US"},
        {"id": "Algieba", "name": "Algieba", "language": "en-US"},
        {"id": "Aldebaran", "name": "Aldebaran", "language": "en-US"},
        {"id": "Mira", "name": "Mira", "language": "en-US"},
        {"id": "Pulcherrima", "name": "Pulcherrima", "language": "en-US"},
        {"id": "Rasalhague", "name": "Rasalhague", "language": "en-US"},
        {"id": "Thuban", "name": "Thuban", "language": "en-US"},
    ]
    
    AVAILABLE_MODELS = [
        "gemini-2.5-flash-preview-tts",
        "gemini-2.5-pro-preview-tts",
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not HAS_GOOGLE_GENAI:
            raise ImportError("google-genai package not installed. Run: pip install google-genai")
        self._client = None
    
    def _get_provider_type(self):
        return ProviderType.TEXT_TO_SPEECH
    
    def get_client(self):
        if self._client is None:
            client_kwargs = {}
            if self.config.api_key:
                client_kwargs['api_key'] = self.config.api_key
            self._client = genai.Client(**client_kwargs)
        return self._client
    
    def _save_wave_file(self, filename: str, pcm_data: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2):
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> TTSResponse:
        client = self.get_client()
        
        voice_id = voice or self.config.voice or "Kore"
        model = self.model_name or "gemini-2.5-flash-preview-tts"
        
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_id,
                        )
                    )
                ),
            )
        )
        
        audio_data = None
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        audio_data = part.inline_data.data
                        break
        
        if not audio_data:
            raise ValueError("Gemini TTS 未返回有效的音频数据")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        self._save_wave_file(output_path, audio_data)
        
        return TTSResponse(
            audio_path=output_path,
            format="wav"
        )
    
    def get_voices(self) -> List[Dict]:
        return self.DEFAULT_VOICES
    
    def test(self) -> bool:
        try:
            self.synthesize("测试语音", "Kore")
            return True
        except Exception as e:
            logger.error(f"Gemini TTS test failed: {e}")
            return False
