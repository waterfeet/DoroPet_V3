import os
import tempfile
from typing import Optional, List, Dict
from ..provider import TTSProvider
from ..entities import TTSResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter, TTS_CONFIG_FIELDS
from src.core.logger import logger

try:
    import dashscope
    from dashscope import MultiModalConversation
    HAS_DASHSCOPE = True
except ImportError:
    HAS_DASHSCOPE = False
    dashscope = None


@register_provider_adapter(
    "qwen_tts",
    "阿里云千问 TTS (Qwen3-TTS)",
    provider_type=ProviderType.TEXT_TO_SPEECH,
    default_config_tmpl={
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "model": "qwen3-tts-flash",
        "voice": "Cherry",
    },
    provider_display_name="千问 TTS",
    config_fields=TTS_CONFIG_FIELDS
)
class ProviderQwenTTS(TTSProvider):
    DEFAULT_VOICES = [
        {"id": "Cherry", "name": "芊悦 - 阳光积极、亲切自然小姐姐 (女)", "language": "zh"},
        {"id": "Serena", "name": "苏瑶 - 温柔小姐姐 (女)", "language": "zh"},
        {"id": "Ethan", "name": "晨煦 - 阳光温暖活力朝气 (男)", "language": "zh"},
        {"id": "Chelsie", "name": "千雪 - 二次元虚拟女友 (女)", "language": "zh"},
        {"id": "Momo", "name": "茉兔 - 撒娇搞怪 (女)", "language": "zh"},
        {"id": "Vivian", "name": "十三 - 拽拽的可爱小暴躁 (女)", "language": "zh"},
        {"id": "Moon", "name": "月白 - 率性帅气 (男)", "language": "zh"},
        {"id": "Maia", "name": "四月 - 知性与温柔 (女)", "language": "zh"},
        {"id": "Kai", "name": "凯 - 耳朵的SPA (男)", "language": "zh"},
        {"id": "Nofish", "name": "不吃鱼 - 不会翘舌音的设计师 (男)", "language": "zh"},
        {"id": "Bella", "name": "萌宝 - 小萝莉 (女)", "language": "zh"},
        {"id": "Jennifer", "name": "詹妮弗 - 品牌级美语女声 (女)", "language": "en"},
        {"id": "Ryan", "name": "甜茶 - 节奏拉满戏感炸裂 (男)", "language": "zh"},
        {"id": "Katerina", "name": "卡捷琳娜 - 御姐音色 (女)", "language": "zh"},
        {"id": "Aiden", "name": "艾登 - 精通厨艺的美语大男孩 (男)", "language": "en"},
        {"id": "Eldric Sage", "name": "沧明子 - 沉稳睿智的老者 (男)", "language": "zh"},
        {"id": "Mia", "name": "乖小妹 - 温顺乖巧 (女)", "language": "zh"},
        {"id": "Mochi", "name": "沙小弥 - 聪明伶俐的小大人 (男)", "language": "zh"},
        {"id": "Bellona", "name": "燕铮莺 - 声音洪亮吐字清晰 (女)", "language": "zh"},
        {"id": "Vincent", "name": "田叔 - 沙哑烟嗓 (男)", "language": "zh"},
        {"id": "Bunny", "name": "萌小姬 - 萌属性爆棚 (女)", "language": "zh"},
        {"id": "Neil", "name": "阿闻 - 专业新闻主持人 (男)", "language": "zh"},
        {"id": "Elias", "name": "墨讲师 - 学科严谨讲师 (女)", "language": "zh"},
        {"id": "Arthur", "name": "徐大爷 - 质朴嗓音 (男)", "language": "zh"},
        {"id": "Nini", "name": "邻家妹妹 - 软黏嗓音 (女)", "language": "zh"},
        {"id": "Ebona", "name": "诡婆婆 - 神秘低语 (女)", "language": "zh"},
        {"id": "Seren", "name": "小婉 - 助眠舒缓 (女)", "language": "zh"},
        {"id": "Pip", "name": "顽屁小孩 - 调皮捣蛋 (男)", "language": "zh"},
        {"id": "Stella", "name": "少女阿月 - 甜到发腻 (女)", "language": "zh"},
        {"id": "Bodega", "name": "博德加 - 热情西班牙大叔 (男)", "language": "es"},
        {"id": "Sonrisa", "name": "索尼莎 - 热情开朗拉美大姐 (女)", "language": "es"},
        {"id": "Alek", "name": "阿列克 - 战斗民族 (男)", "language": "ru"},
        {"id": "Dolce", "name": "多尔切 - 慵懒意大利大叔 (男)", "language": "it"},
        {"id": "Sohee", "name": "素熙 - 温柔开朗韩国欧尼 (女)", "language": "ko"},
        {"id": "Ono Anna", "name": "小野杏 - 鬼灵精怪青梅竹马 (女)", "language": "ja"},
        {"id": "Lenn", "name": "莱恩 - 理性叛逆德国青年 (男)", "language": "de"},
        {"id": "Emilien", "name": "埃米尔安 - 浪漫法国大哥哥 (男)", "language": "fr"},
        {"id": "Andre", "name": "安德雷 - 声音磁性沉稳 (男)", "language": "zh"},
        {"id": "Radio Gol", "name": "拉迪奥·戈尔 - 足球诗人 (男)", "language": "zh"},
        {"id": "Jada", "name": "阿珍 - 风风火火沪上阿姐 (女/上海话)", "language": "zh-sh"},
        {"id": "Dylan", "name": "晓东 - 北京胡同少年 (男/北京话)", "language": "zh-bj"},
        {"id": "Li", "name": "老李 - 耐心瑜伽老师 (男/南京话)", "language": "zh-nj"},
        {"id": "Marcus", "name": "秦川 - 老陕味道 (男/陕西话)", "language": "zh-sx"},
        {"id": "Roy", "name": "阿杰 - 诙谐直爽台湾哥仔 (男/闽南语)", "language": "zh-mn"},
        {"id": "Peter", "name": "李彼得 - 天津相声捧哏 (男/天津话)", "language": "zh-tj"},
        {"id": "Sunny", "name": "晴儿 - 甜到心里的川妹子 (女/四川话)", "language": "zh-sc"},
        {"id": "Eric", "name": "程川 - 跳脱市井四川成都男子 (男/四川话)", "language": "zh-sc"},
        {"id": "Rocky", "name": "阿强 - 幽默风趣 (男/粤语)", "language": "yue"},
        {"id": "Kiki", "name": "阿清 - 甜美港妹闺蜜 (女/粤语)", "language": "yue"},
    ]
    
    REGION_BASE_URLS = {
        "beijing": "https://dashscope.aliyuncs.com/api/v1",
        "singapore": "https://dashscope-intl.aliyuncs.com/api/v1",
        "virginia": "https://dashscope-us.aliyuncs.com/api/v1",
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not HAS_DASHSCOPE:
            raise ImportError("dashscope package not installed. Run: pip install dashscope")
        self._setup_base_url()
    
    def _setup_base_url(self):
        base_url = self.config.base_url
        if base_url:
            dashscope.base_http_api_url = base_url
    
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
        voice_id = voice or self.config.voice or "Cherry"
        model = self.model_name or "qwen3-tts-flash"
        
        api_key = self.config.api_key or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请配置阿里云百炼 API Key 或设置环境变量 DASHSCOPE_API_KEY")
        
        instructions = kwargs.get("instructions", None)
        optimize_instructions = kwargs.get("optimize_instructions", False)
        
        call_params = {
            "model": model,
            "api_key": api_key,
            "text": text,
            "voice": voice_id,
        }
        
        if instructions:
            call_params["instructions"] = instructions
            call_params["optimize_instructions"] = optimize_instructions
        
        response = MultiModalConversation.call(**call_params)
        
        if response.status_code != 200:
            error_msg = response.message if hasattr(response, 'message') else str(response)
            raise Exception(f"Qwen TTS API 错误: {error_msg}")
        
        output_path = None
        
        if hasattr(response, 'output') and response.output:
            output = response.output
            if hasattr(output, 'audio') and output.audio:
                audio_info = output.audio
                if hasattr(audio_info, 'url') and audio_info.url:
                    import requests
                    audio_response = requests.get(audio_info.url)
                    if audio_response.status_code == 200:
                        audio_data = audio_response.content
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                            tmp_file.write(audio_data)
                            output_path = tmp_file.name
        
        if output_path is None:
            raise Exception("Qwen TTS 未返回有效的音频数据")
        
        return TTSResponse(
            audio_path=output_path,
            format="wav"
        )
    
    def get_voices(self) -> List[Dict]:
        return self.DEFAULT_VOICES
    
    def test(self) -> bool:
        try:
            self.synthesize("测试语音", "Cherry")
            return True
        except Exception as e:
            logger.error(f"Qwen TTS test failed: {e}")
            return False
