from typing import Optional, List, Dict, Generator
from .openai_source import ProviderOpenAI
from ..entities import ProviderConfig
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS


@register_provider_adapter(
    "moonshot_chat_completion",
    "Moonshot AI (Kimi) API",
    default_config_tmpl={
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    provider_display_name="Moonshot (Kimi)",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderMoonshot(ProviderOpenAI):
    def __init__(self, config: ProviderConfig):
        if not config.base_url:
            config.base_url = "https://api.moonshot.cn/v1"
        super().__init__(config)
    
    def supports_vision(self) -> bool:
        if self.config.is_visual:
            return True
        return "vision" in self.model_name.lower()
