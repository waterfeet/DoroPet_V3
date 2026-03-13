from typing import Optional, List, Dict, Generator
from .openai_source import ProviderOpenAI
from ..entities import ProviderConfig
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS


@register_provider_adapter(
    "groq_chat_completion",
    "Groq API (高速推理)",
    default_config_tmpl={
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-70b-versatile",
    },
    provider_display_name="Groq",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderGroq(ProviderOpenAI):
    def __init__(self: ProviderConfig, config):
        if not config.base_url:
            config.base_url = "https://api.groq.com/openai/v1"
        super().__init__(config)
