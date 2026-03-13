from typing import List, Dict, Optional, Any, Callable
from .entities import ProviderType, ProviderMetaData


provider_registry: List[ProviderMetaData] = []
provider_cls_map: Dict[str, ProviderMetaData] = {}


def register_provider_adapter(
    provider_type_name: str,
    desc: str,
    provider_type: ProviderType = ProviderType.CHAT_COMPLETION,
    default_config_tmpl: Optional[Dict] = None,
    provider_display_name: Optional[str] = None,
    icon: Optional[str] = None,
    config_fields: Optional[List[Dict]] = None
) -> Callable:
    def decorator(cls):
        if provider_type_name in provider_cls_map:
            raise ValueError(f"Provider {provider_type_name} already registered")
        
        if default_config_tmpl:
            default_config_tmpl.setdefault("type", provider_type_name)
            default_config_tmpl.setdefault("enable", False)
            default_config_tmpl.setdefault("id", provider_type_name)
        
        pm = ProviderMetaData(
            id="default",
            model=None,
            type=provider_type_name,
            desc=desc,
            provider_type=provider_type,
            cls_type=cls,
            default_config_tmpl=default_config_tmpl,
            provider_display_name=provider_display_name or provider_type_name,
            icon=icon,
            config_fields=config_fields
        )
        provider_registry.append(pm)
        provider_cls_map[provider_type_name] = pm
        
        return cls
    
    return decorator


def get_provider_metadata(provider_type: str) -> Optional[ProviderMetaData]:
    return provider_cls_map.get(provider_type)


def get_all_providers_by_type(p_type: ProviderType) -> List[ProviderMetaData]:
    return [pm for pm in provider_registry if pm.provider_type == p_type]


def get_provider_display_name(provider_type: str) -> str:
    pm = provider_cls_map.get(provider_type)
    return pm.provider_display_name if pm else provider_type


def get_provider_config_fields(provider_type: str) -> List[Dict]:
    pm = provider_cls_map.get(provider_type)
    if pm and pm.config_fields:
        return pm.config_fields
    return []


LLM_CONFIG_FIELDS = [
    {"name": "name", "label": "配置名称", "type": "text", "required": True, "placeholder": "例如: 我的 GPT-4"},
    {"name": "api_key", "label": "API Key", "type": "password", "required": True, "placeholder": "sk-..."},
    {"name": "base_url", "label": "Base URL", "type": "text", "required": True, "placeholder": "API 基础地址"},
    {"name": "model", "label": "模型 ID", "type": "text", "required": True, "placeholder": "例如: gpt-4"},
    {"name": "is_visual", "label": "视觉模型", "type": "checkbox", "default": False},
    {"name": "is_thinking", "label": "思考模型", "type": "checkbox", "default": False},
]

TTS_CONFIG_FIELDS = [
    {"name": "name", "label": "配置名称", "type": "text", "required": True, "placeholder": "例如: 我的 TTS"},
    {"name": "api_key", "label": "API Key", "type": "password", "required": False, "placeholder": "sk-..."},
    {"name": "base_url", "label": "Base URL", "type": "text", "required": False, "placeholder": "API 基础地址"},
    {"name": "model", "label": "模型 ID", "type": "text", "required": False, "placeholder": "例如: tts-1"},
    {"name": "voice", "label": "语音包", "type": "text", "required": True, "placeholder": "例如: alloy"},
]

IMAGE_CONFIG_FIELDS = [
    {"name": "name", "label": "配置名称", "type": "text", "required": True, "placeholder": "例如: DALL-E 3"},
    {"name": "api_key", "label": "API Key", "type": "password", "required": True, "placeholder": "sk-..."},
    {"name": "base_url", "label": "Base URL", "type": "text", "required": True, "placeholder": "API 基础地址"},
    {"name": "model", "label": "模型 ID", "type": "text", "required": True, "placeholder": "例如: dall-e-3"},
]
