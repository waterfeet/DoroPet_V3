import json
from typing import Optional, List, Dict, Generator, Any
from ..provider import LLMProvider
from ..entities import LLMResponse, ToolCall, ProviderConfig
from ..register import register_provider_adapter, LLM_CONFIG_FIELDS
from src.core.logger import logger

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    Anthropic = None


@register_provider_adapter(
    "anthropic_chat_completion",
    "Anthropic Claude API",
    default_config_tmpl={
        "base_url": "https://api.anthropic.com",
        "model": "claude-3-5-sonnet-20241022",
    },
    provider_display_name="Anthropic Claude",
    config_fields=LLM_CONFIG_FIELDS
)
class ProviderAnthropic(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def _create_client(self) -> Any:
        return Anthropic(api_key=self.config.api_key)
    
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
        
        system_prompt = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            else:
                chat_messages.append(msg)
        
        api_params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
        }
        
        if system_prompt:
            api_params["system"] = system_prompt
        if temperature is not None:
            api_params["temperature"] = temperature
        if tools:
            api_params["tools"] = self._convert_tools(tools)
        
        if self.supports_thinking():
            api_params["thinking"] = {"budget_tokens": kwargs.get("thinking_budget", 4096)}
        
        response = client.messages.create(**api_params)
        
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
        
        system_prompt = None
        chat_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            else:
                chat_messages.append(msg)
        
        api_params: Dict[str, Any] = {
            "model": self.model_name,
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
        }
        
        if system_prompt:
            api_params["system"] = system_prompt
        if temperature is not None:
            api_params["temperature"] = temperature
        if tools:
            api_params["tools"] = self._convert_tools(tools)
        
        if self.supports_thinking():
            api_params["thinking"] = {"budget_tokens": kwargs.get("thinking_budget", 4096)}
        
        with client.messages.stream(**api_params) as stream:
            for event in stream:
                parsed = self._parse_stream_event(event)
                if parsed:
                    yield parsed
    
    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {})
                })
        return anthropic_tools
    
    def _parse_response(self, response) -> LLMResponse:
        content = ""
        reasoning = ""
        tool_calls = []
        
        for block in response.content:
            if hasattr(block, 'text'):
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=json.dumps(block.input) if isinstance(block.input, dict) else str(block.input),
                    index=len(tool_calls)
                ))
        
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        
        return LLMResponse(
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "",
            model=response.model,
            usage=usage
        )
    
    def _parse_stream_event(self, event) -> Optional[LLMResponse]:
        if event.type == "content_block_delta":
            if hasattr(event.delta, 'text'):
                return LLMResponse(content=event.delta.text)
        elif event.type == "content_block_start":
            if hasattr(event.content_block, 'type'):
                if event.content_block.type == "tool_use":
                    return LLMResponse(
                        tool_calls=[ToolCall(
                            id=event.content_block.id,
                            name=event.content_block.name,
                            arguments="",
                            index=getattr(event, 'index', 0)
                        )]
                    )
        return None
