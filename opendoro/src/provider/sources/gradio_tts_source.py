import os
import tempfile
from typing import Optional, List, Dict
from ..provider import TTSProvider
from ..entities import TTSResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter
from src.core.logger import logger

try:
    from gradio_client import Client
    HAS_GRADIO_CLIENT = True
except ImportError:
    HAS_GRADIO_CLIENT = False
    Client = None


GRADIO_TTS_CONFIG_FIELDS = [
    {"name": "name", "label": "配置名称", "type": "text", "required": True, "placeholder": "例如: 本地Gradio TTS"},
    {"name": "base_url", "label": "Gradio服务地址", "type": "text", "required": True, "placeholder": "例如: http://localhost:7860"},
    {"name": "voice", "label": "语音包", "type": "text", "required": False, "placeholder": "语音包名称"},
    {"name": "api_name", "label": "API端点名称", "type": "text", "required": False, "placeholder": "例如: /tts (默认为/predict)"},
    {"name": "speed", "label": "语速", "type": "text", "required": False, "placeholder": "例如: 1.0"},
]


@register_provider_adapter(
    "gradio_tts",
    "Gradio TTS (本地API)",
    provider_type=ProviderType.TEXT_TO_SPEECH,
    default_config_tmpl={
        "base_url": "http://localhost:7860",
        "voice": "",
        "api_name": "/predict",
        "speed": "1.0",
    },
    provider_display_name="Gradio TTS",
    config_fields=GRADIO_TTS_CONFIG_FIELDS
)
class ProviderGradioTTS(TTSProvider):
    DEFAULT_VOICES = [
        {"id": "default", "name": "默认语音", "language": "auto"},
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not HAS_GRADIO_CLIENT:
            raise ImportError("gradio_client package not installed. Run: pip install gradio_client")
        self._client = None
        self._api_info = None

    def _get_provider_type(self):
        return ProviderType.TEXT_TO_SPEECH

    def _get_client(self):
        if self._client is None:
            base_url = self.config.base_url or "http://localhost:7860"
            self._client = Client(base_url)
        return self._client

    def _discover_api(self) -> Dict:
        if self._api_info is not None:
            return self._api_info
        
        try:
            client = self._get_client()
            api_info = client.view_api(return_format="dict")
            self._api_info = api_info
            return api_info
        except Exception as e:
            logger.warning(f"Failed to discover Gradio API: {e}")
            return {}

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> TTSResponse:
        client = self._get_client()
        
        voice_id = voice or self.config.voice or ""
        api_name = self.config.api_name or "/predict"
        
        try:
            api_info = self._discover_api()
            named_endpoints = api_info.get("named_endpoints", {})
            
            if api_name in named_endpoints:
                endpoint_info = named_endpoints[api_name]
                parameters = endpoint_info.get("parameters", [])
                
                args = []
                kwargs_dict = {}
                
                for param in parameters:
                    param_name = param.get("parameter_name", "")
                    param_type = param.get("type", "")
                    
                    if "text" in param_type.lower() or "string" in param_type.lower():
                        kwargs_dict[param_name] = text
                    elif "voice" in param_name.lower():
                        kwargs_dict[param_name] = voice_id if voice_id else "default"
                    elif "speed" in param_name.lower() or "rate" in param_name.lower():
                        kwargs_dict[param_name] = speed
                    elif "audio" in param_type.lower():
                        continue
                
                if kwargs_dict:
                    result = client.predict(**kwargs_dict, api_name=api_name)
                else:
                    result = client.predict(text, api_name=api_name)
            else:
                result = client.predict(text, api_name=api_name)
            
            if isinstance(result, str):
                if os.path.exists(result):
                    return TTSResponse(
                        audio_path=result,
                        format=self._detect_format(result)
                    )
                else:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        tmp_file.write(result.encode() if isinstance(result, bytes) else result)
                        return TTSResponse(
                            audio_path=tmp_file.name,
                            format="wav"
                        )
            
            elif isinstance(result, tuple):
                audio_path = None
                for item in result:
                    if isinstance(item, str) and os.path.exists(item):
                        audio_path = item
                        break
                
                if audio_path:
                    return TTSResponse(
                        audio_path=audio_path,
                        format=self._detect_format(audio_path)
                    )
            
            elif isinstance(result, bytes):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(result)
                    return TTSResponse(
                        audio_path=tmp_file.name,
                        format="wav"
                    )
            
            raise ValueError(f"Unexpected result type from Gradio TTS: {type(result)}")
            
        except Exception as e:
            logger.error(f"Gradio TTS synthesis failed: {e}")
            raise

    def _detect_format(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".mp3", ".wav", ".ogg", ".flac", ".aac"]:
            return ext[1:]
        return "wav"

    def get_voices(self) -> List[Dict]:
        try:
            api_info = self._discover_api()
            named_endpoints = api_info.get("named_endpoints", {})
            api_name = self.config.api_name or "/predict"
            
            if api_name in named_endpoints:
                endpoint_info = named_endpoints[api_name]
                parameters = endpoint_info.get("parameters", [])
                
                for param in parameters:
                    param_name = param.get("parameter_name", "").lower()
                    if "voice" in param_name:
                        choices = param.get("choices", [])
                        if choices:
                            return [{"id": c, "name": c, "language": "auto"} for c in choices]
        except Exception as e:
            logger.warning(f"Failed to get voices from Gradio API: {e}")
        
        return self.DEFAULT_VOICES

    def test(self) -> bool:
        try:
            result = self.synthesize("测试")
            if result.audio_path and os.path.exists(result.audio_path):
                return True
            return False
        except Exception as e:
            logger.error(f"Gradio TTS test failed: {e}")
            return False

    def close(self):
        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._client = None
