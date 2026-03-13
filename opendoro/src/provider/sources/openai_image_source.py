import os
import base64
import tempfile
from typing import Optional, List, Dict
from openai import OpenAI
import httpx

from ..provider import ImageProvider
from ..entities import ImageResponse, ProviderConfig, ProviderType
from ..register import register_provider_adapter, IMAGE_CONFIG_FIELDS
from src.core.logger import logger


@register_provider_adapter(
    "openai_image",
    "OpenAI 兼容图像生成 API",
    provider_type=ProviderType.IMAGE_GENERATION,
    default_config_tmpl={
        "base_url": "https://api.openai.com/v1",
        "model": "dall-e-3",
    },
    provider_display_name="DALL-E / Stable Diffusion",
    config_fields=IMAGE_CONFIG_FIELDS
)
class ProviderOpenAIImage(ImageProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._http_client = None
    
    def _get_provider_type(self):
        from ..entities import ProviderType
        return ProviderType.IMAGE_GENERATION
    
    def get_client(self) -> OpenAI:
        if self._client is None:
            self._http_client = httpx.Client(timeout=self.config.timeout)
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                http_client=self._http_client
            )
        return self._client
    
    def close(self):
        if self._http_client:
            try:
                self._http_client.close()
            except:
                pass
        super().close()
    
    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs
    ) -> ImageResponse:
        client = self.get_client()
        model = self.model_name or "dall-e-3"
        
        response_format = kwargs.get("response_format", "url")
        
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=n,
                response_format=response_format
            )
            
            if response.data:
                image_data = response.data[0]
                image_url = image_data.url if hasattr(image_data, 'url') else ""
                revised_prompt = image_data.revised_prompt if hasattr(image_data, 'revised_prompt') else ""
                
                image_path = ""
                if response_format == "b64_json" and hasattr(image_data, 'b64_json'):
                    image_path = self._save_base64_image(image_data.b64_json)
                elif image_url:
                    image_path = self._download_image(image_url)
                
                return ImageResponse(
                    image_path=image_path,
                    image_url=image_url,
                    revised_prompt=revised_prompt,
                    format="png"
                )
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
        
        return ImageResponse()
    
    def _save_base64_image(self, b64_data: str) -> str:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        image_data = base64.b64decode(b64_data)
        with open(output_path, "wb") as f:
            f.write(image_data)
        
        return output_path
    
    def _download_image(self, url: str) -> str:
        import urllib.request
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        urllib.request.urlretrieve(url, output_path)
        return output_path
    
    def get_supported_sizes(self) -> List[str]:
        model = self.model_name.lower() if self.model_name else ""
        
        if "dall-e-3" in model:
            return ["1024x1024", "1792x1024", "1024x1792"]
        elif "dall-e-2" in model:
            return ["256x256", "512x512", "1024x1024"]
        else:
            return ["1024x1024", "512x512", "256x256"]
    
    def get_supported_qualities(self) -> List[str]:
        model = self.model_name.lower() if self.model_name else ""
        
        if "dall-e-3" in model:
            return ["standard", "hd"]
        else:
            return ["standard"]
    
    def test(self) -> bool:
        try:
            self.generate("A simple test image", size="256x256" if "dall-e-2" in (self.model_name or "").lower() else "1024x1024")
            return True
        except Exception as e:
            logger.error(f"Image generation test failed: {e}")
            return False
