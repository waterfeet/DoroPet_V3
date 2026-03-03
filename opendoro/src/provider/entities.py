import enum
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict


class ProviderType(enum.Enum):
    CHAT_COMPLETION = "chat_completion"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    IMAGE_GENERATION = "image_generation"
    EMBEDDING = "embedding"


@dataclass
class ProviderMeta:
    id: str
    model: Optional[str] = None
    type: str = ""
    provider_type: ProviderType = ProviderType.CHAT_COMPLETION


@dataclass
class ProviderMetaData(ProviderMeta):
    desc: str = ""
    cls_type: Any = None
    default_config_tmpl: Optional[Dict] = None
    provider_display_name: Optional[str] = None
    icon: Optional[str] = None
    config_fields: Optional[List[Dict]] = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str
    index: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments
            }
        }


@dataclass
class ToolResult:
    tool_call_id: str
    content: str
    status: str = "success"


@dataclass
class LLMResponse:
    content: str = ""
    reasoning: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    model: str = ""
    usage: Optional[Dict] = None
    
    def is_tool_call(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class TTSResponse:
    audio_path: str = ""
    audio_data: Optional[bytes] = None
    duration: float = 0.0
    format: str = "mp3"


@dataclass
class ImageResponse:
    image_path: str = ""
    image_url: str = ""
    revised_prompt: str = ""
    format: str = "png"


@dataclass
class STTResponse:
    text: str = ""
    language: str = ""
    duration: float = 0.0


@dataclass  
class ProviderConfig:
    id: str
    name: str
    type: str
    provider_type: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    voice: str = ""
    is_active: bool = False
    is_visual: bool = False
    is_thinking: bool = False
    timeout: int = 120
    proxy: str = ""
    extra_config: Dict = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProviderConfig':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            type=data.get('type', ''),
            provider_type=data.get('provider_type', 'chat_completion'),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model=data.get('model', data.get('model_name', '')),
            voice=data.get('voice', ''),
            is_active=data.get('is_active', False),
            is_visual=data.get('is_visual', False),
            is_thinking=data.get('is_thinking', False),
            timeout=data.get('timeout', 120),
            proxy=data.get('proxy', ''),
            extra_config=data.get('extra_config', {})
        )
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'provider_type': self.provider_type,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'model': self.model,
            'model_name': self.model,
            'voice': self.voice,
            'is_active': self.is_active,
            'is_visual': self.is_visual,
            'is_thinking': self.is_thinking,
            'timeout': self.timeout,
            'proxy': self.proxy,
            'extra_config': self.extra_config
        }
