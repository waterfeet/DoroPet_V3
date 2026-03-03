from typing import Optional, List, Dict, Generator, Any
from .openai_source import ProviderOpenAI
from ..entities import ProviderConfig, LLMResponse
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS


@register_provider_adapter(
    "deepseek_chat_completion",
    "DeepSeek API (深度求索)",
    default_config_tmpl={
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    provider_display_name="DeepSeek",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderDeepSeek(ProviderOpenAI):
    def __init__(self, config: ProviderConfig):
        if not config.base_url:
            config.base_url = "https://api.deepseek.com"
        super().__init__(config)
    
    def supports_thinking(self) -> bool:
        return self.config.is_thinking or "reasoner" in self.model_name.lower()
    
    def chat_completion(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        client = self.get_client()
        
        api_params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }
        
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        if temperature is not None:
            api_params["temperature"] = temperature
        if tools:
            api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice
        
        response = client.chat.completions.create(**api_params)
        
        return self._parse_response(response)
    
    def chat_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[LLMResponse, None, None]:
        client = self.get_client()
        
        api_params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
        }
        
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        if temperature is not None:
            api_params["temperature"] = temperature
        if tools:
            api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice
        
        response = client.chat.completions.create(**api_params)
        
        for chunk in response:
            parsed = self._parse_stream_chunk(chunk)
            if parsed:
                yield parsed
