import os
import tempfile
from typing import Optional, List, Dict
from ..provider import TTSProvider
from ..entities import TTSResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter, TTS_CONFIG_FIELDS
from src.core.logger import logger

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    edge_tts = None


@register_provider_adapter(
    "edge_tts",
    "Microsoft Edge TTS (免费)",
    provider_type=ProviderType.TEXT_TO_SPEECH,
    default_config_tmpl={
        "voice": "zh-CN-XiaoxiaoNeural",
    },
    provider_display_name="Edge TTS",
    config_fields=TTS_CONFIG_FIELDS
)
class ProviderEdgeTTS(TTSProvider):
    DEFAULT_VOICES = [
        {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女)", "language": "zh-CN"},
        {"id": "zh-CN-YunxiNeural", "name": "云希 (男)", "language": "zh-CN"},
        {"id": "zh-CN-YunjianNeural", "name": "云健 (男)", "language": "zh-CN"},
        {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 (女)", "language": "zh-CN"},
        {"id": "zh-CN-YunyangNeural", "name": "云扬 (男)", "language": "zh-CN"},
        {"id": "zh-CN-XiaochenNeural", "name": "晓辰 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaohanNeural", "name": "晓涵 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaomengNeural", "name": "晓梦 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaomoNeural", "name": "晓墨 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaoruiNeural", "name": "晓睿 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaoshuangNeural", "name": "晓双 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaoxuanNeural", "name": "晓萱 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaoyanNeural", "name": "晓颜 (女)", "language": "zh-CN"},
        {"id": "zh-CN-XiaoyouNeural", "name": "晓悠 (女)", "language": "zh-CN"},
        {"id": "en-US-JennyNeural", "name": "Jenny (Female)", "language": "en-US"},
        {"id": "en-US-GuyNeural", "name": "Guy (Male)", "language": "en-US"},
        {"id": "ja-JP-NanamiNeural", "name": "七海 (女)", "language": "ja-JP"},
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not HAS_EDGE_TTS:
            raise ImportError("edge-tts package not installed. Run: pip install edge-tts")
    
    def _get_provider_type(self):
        from ..entities import ProviderType
        return ProviderType.TEXT_TO_SPEECH
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> TTSResponse:
        voice_id = voice or self.config.voice or "zh-CN-XiaoxiaoNeural"
        
        communicate = edge_tts.Communicate(text, voice_id, rate=f"+{int((speed - 1) * 100)}%")
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(communicate.save(output_path))
        finally:
            loop.close()
        
        return TTSResponse(
            audio_path=output_path,
            format="mp3"
        )
    
    def get_voices(self) -> List[Dict]:
        return self.DEFAULT_VOICES
    
    def test(self) -> bool:
        try:
            self.synthesize("测试语音", "zh-CN-XiaoxiaoNeural")
            return True
        except Exception as e:
            logger.error(f"Edge TTS test failed: {e}")
            return False
