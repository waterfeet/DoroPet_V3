from typing import Optional, List, Dict, Generator
from .openai_source import ProviderOpenAI
from ..entities import ProviderConfig
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS


@register_provider_adapter(
    "gemini_chat_completion",
    "Google Gemini API (OpenAI 兼容)",
    default_config_tmpl={
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
    },
    provider_display_name="Google Gemini",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderGemini(ProviderOpenAI):
    def __init__(self, config: ProviderConfig):
        if not config.base_url:
            config.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        super().__init__(config)
    
    def supports_vision(self) -> bool:
        if self.config.is_visual:
            return True
        return True
    
    def supports_thinking(self) -> bool:
        if self.config.is_thinking:
            return True
        return "thinking" in self.model_name.lower()
