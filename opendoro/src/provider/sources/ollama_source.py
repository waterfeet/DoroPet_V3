from typing import Optional, List, Dict, Generator
from .openai_source import ProviderOpenAI
from ..entities import ProviderConfig
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS


@register_provider_adapter(
    "ollama_chat_completion",
    "Ollama 本地模型",
    default_config_tmpl={
        "base_url": "http://localhost:11434/v1",
        "model": "llama3",
    },
    provider_display_name="Ollama",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderOllama(ProviderOpenAI):
    def __init__(self, config: ProviderConfig):
        if not config.base_url:
            config.base_url = "http://localhost:11434/v1"
        super().__init__(config)
    
    def supports_vision(self) -> bool:
        if self.config.is_visual:
            return True
        vision_models = ["llava", "bakllava", "moondream", "cogvlm"]
        return any(vm in self.model_name.lower() for vm in vision_models)
