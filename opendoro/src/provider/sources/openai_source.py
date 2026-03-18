import json
from typing import Optional, List, Dict, Generator, Any
from openai import OpenAI
import httpx

from ..provider import LLMProvider
from ..entities import LLMResponse, ToolCall, ProviderConfig, ProviderType
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS
from src.core.logger import logger


@register_provider_adapter(
    "openai_chat_completion",
    "OpenAI 兼容 API (支持所有 OpenAI 格式的服务)",
    default_config_tmpl={
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    provider_display_name="OpenAI 兼容",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderOpenAI(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._http_client = None
    
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.CHAT_COMPLETION
    
    def _create_client(self) -> OpenAI:
        http_client_kwargs = {
            "timeout": self.config.timeout
        }
        
        if self.config.proxy:
            http_client_kwargs["proxy"] = self.config.proxy
        
        self._http_client = httpx.Client(**http_client_kwargs)
        
        api_key = self.config.api_key
        if not api_key or api_key.strip() == "":
            if "ollama" in self.config.base_url.lower() or "localhost:11434" in self.config.base_url:
                api_key = "ollama"
                logger.info(f"[ProviderOpenAI] Using placeholder API key for Ollama")
        
        return OpenAI(
            api_key=api_key,
            base_url=self.config.base_url,
            http_client=self._http_client
        )
    
    def close(self):
        if self._http_client:
            try:
                self._http_client.close()
            except:
                pass
        super().close()
    
    def chat(
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
            "stream": False,
        }
        
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        if temperature is not None:
            api_params["temperature"] = temperature
        if tools:
            api_params["tools"] = tools
            if tool_choice:
                api_params["tool_choice"] = tool_choice
        
        if self.supports_thinking():
            api_params["thinking"] = {"budget_tokens": kwargs.get("thinking_budget", 4096)}
        
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
        
        if self.supports_thinking():
            api_params["thinking"] = {"budget_tokens": kwargs.get("thinking_budget", 4096)}
        
        response = client.chat.completions.create(**api_params)
        
        for chunk in response:
            parsed = self._parse_stream_chunk(chunk)
            if parsed:
                yield parsed
    
    def _parse_response(self, response) -> LLMResponse:
        choice = response.choices[0]
        
        content = choice.message.content or ""
        reasoning = ""
        tool_calls = []
        
        if hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
            reasoning = choice.message.reasoning_content
        
        if choice.message.tool_calls:
            for idx, tc in enumerate(choice.message.tool_calls):
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                    index=idx
                ))
        
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        return LLMResponse(
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            model=response.model,
            usage=usage
        )
    
    def _parse_stream_chunk(self, chunk) -> Optional[LLMResponse]:
        if not chunk.choices:
            return None
        
        choice = chunk.choices[0]
        delta = choice.delta
        
        content = ""
        reasoning = ""
        tool_calls = []
        
        if delta.content:
            content = delta.content
        
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            reasoning = delta.reasoning_content
        
        if delta.tool_calls:
            for tc in delta.tool_calls:
                tool_call = ToolCall(
                    id=tc.id or "",
                    name=tc.function.name if tc.function and tc.function.name else "",
                    arguments=tc.function.arguments if tc.function and tc.function.arguments else "",
                    index=tc.index if hasattr(tc, 'index') else 0
                )
                tool_calls.append(tool_call)
        
        return LLMResponse(
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "",
            model=getattr(chunk, 'model', ''),
        )
    
    def get_models(self) -> List[str]:
        try:
            client = self.get_client()
            models = client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            logger.warning(f"Failed to get models: {e}")
            return []
