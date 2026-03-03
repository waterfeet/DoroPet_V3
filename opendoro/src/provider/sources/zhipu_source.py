from typing import Optional, List, Dict, Generator, Any
from openai import OpenAI
import httpx

from .openai_source import ProviderOpenAI
from ..entities import LLMResponse, ToolCall, ProviderConfig
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS
from src.core.logger import logger

try:
    from zhipuai import ZhipuAI
    HAS_ZHIPU = True
except ImportError:
    HAS_ZHIPU = False
    ZhipuAI = None


@register_provider_adapter(
    "zhipu_chat_completion",
    "智谱 AI (GLM) API",
    default_config_tmpl={
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "glm-4-flash",
    },
    provider_display_name="智谱 AI",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderZhipu(ProviderOpenAI):
    ZHIPU_MODELS = [
        "glm-4.7-flash"
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._zhipu_client = None
        if HAS_ZHIPU:
            self._zhipu_client = ZhipuAI(api_key=self.config.api_key)
    
    def _create_client(self) -> OpenAI:
        http_client_kwargs = {
            "timeout": self.config.timeout
        }
        if self.config.proxy:
            http_client_kwargs["proxy"] = self.config.proxy
        
        self._http_client = httpx.Client(**http_client_kwargs)
        return OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            http_client=self._http_client
        )
    
    def get_client(self):
        if HAS_ZHIPU and self._zhipu_client:
            return self._zhipu_client
        return super().get_client()
    
    def get_models(self) -> List[str]:
        try:
            client = super().get_client()
            models = client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            logger.warning(f"Failed to get models from API: {e}")
            return self.ZHIPU_MODELS
    
    def supports_vision(self) -> bool:
        if self.config.is_visual:
            return True
        vision_models = ["glm-4v", "glm-4v-plus"]
        return any(vm in self.model_name.lower() for vm in vision_models)
