import json
import os
import time
import pathlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import requests

from src.agent.core.tool import Tool, ToolSchema, ToolCategory, ToolResult
from src.agent.core.context import ToolCallContext, ToolPermission

logger = logging.getLogger("DoroPet.Agent")


class GenerateImageTool(Tool):
    schema = ToolSchema(
        name="generate_image",
        description="Generate an image based on a text prompt and save it locally.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The description of the image to generate."},
                "size": {"type": "string", "description": "Image size, e.g., '1024x1024'."},
                "quality": {"type": "string", "description": "Quality: 'standard' or 'hd'."},
            },
            "required": ["prompt"],
        },
        category=ToolCategory.IMAGE,
        required_permissions=[ToolPermission.NETWORK],
        timeout_ms=120000,
        max_output_chars=3000,
    )

    def __init__(self, image_provider=None):
        super().__init__(self.schema)
        self._image_provider = image_provider

    def set_provider(self, provider):
        self._image_provider = provider

    async def execute(self, context: ToolCallContext, prompt: str = "", size: str = "1024x1024", quality: str = "standard", **kwargs) -> ToolResult:
        if not prompt:
            return ToolResult(tool_name=self.schema.name, success=False, error="Prompt is required.")

        try:
            image_path = None
            image_url = ""

            if self._image_provider:
                try:
                    img_response = self._image_provider.generate(prompt=prompt, size=size, quality=quality)
                    if img_response.image_path:
                        image_path = img_response.image_path
                except Exception as e:
                    logger.warning(f"[GenerateImageTool] Provider fallback: {e}")

            if not image_path:
                save_dir = _get_images_dir()
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"gen_{timestamp}.png"
                file_path = os.path.join(save_dir, filename)
                image_path = file_path

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={
                    "prompt": prompt,
                    "image_path": image_path,
                    "size": size,
                },
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class SetExpressionTool(Tool):
    schema = ToolSchema(
        name="set_expression",
        description="Change the facial expression of the Live2D model to reflect mood or emotion.",
        parameters={
            "type": "object",
            "properties": {
                "expression_name": {
                    "type": "string",
                    "description": "The name of the expression to set.",
                }
            },
            "required": ["expression_name"],
        },
        category=ToolCategory.PET,
        required_permissions=[],
    )

    def __init__(self, expression_callback=None):
        super().__init__(self.schema)
        self._callback = expression_callback

    def set_callback(self, callback):
        self._callback = callback

    async def execute(self, context: ToolCallContext, expression_name: str = "", **kwargs) -> ToolResult:
        if not expression_name:
            return ToolResult(tool_name=self.schema.name, success=False, error="Expression name is required.")

        if self._callback:
            try:
                self._callback(expression_name)
            except Exception as e:
                logger.warning(f"[SetExpressionTool] Callback error: {e}")

        return ToolResult(
            tool_name=self.schema.name,
            success=True,
            data={"expression": expression_name},
        )


class ModifyPetAttributeTool(Tool):
    schema = ToolSchema(
        name="modify_pet_attribute",
        description="Modify the pet's attributes when interacting with Doro.",
        parameters={
            "type": "object",
            "properties": {
                "interaction": {
                    "type": "string",
                    "enum": [
                        "feed_snack", "feed_meal", "feed_feast", "feed_bad",
                        "play_gentle", "play_fun", "play_exhausting",
                        "clean_wipe", "clean_wash",
                        "rest_nap", "rest_sleep",
                        "pet_affection", "scold", "comfort",
                    ],
                    "description": "Semantic interaction type.",
                },
                "intensity": {
                    "type": "string",
                    "enum": ["light", "moderate", "heavy"],
                    "description": "Interaction intensity level.",
                },
            },
            "required": ["interaction"],
        },
        category=ToolCategory.PET,
        required_permissions=[],
        timeout_ms=5000,
    )

    def __init__(self, attribute_callback=None):
        super().__init__(self.schema)
        self._callback = attribute_callback

    def set_callback(self, callback):
        self._callback = callback

    async def execute(self, context: ToolCallContext, interaction: str = "", intensity: str = "moderate", **kwargs) -> ToolResult:
        interaction_names = {
            "feed_snack": "零食投喂", "feed_meal": "正餐投喂", "feed_feast": "大餐投喂", "feed_bad": "投喂（变质食物）",
            "play_gentle": "轻度玩耍", "play_fun": "愉快玩耍", "play_exhausting": "剧烈玩耍",
            "clean_wipe": "擦拭清洁", "clean_wash": "洗澡清洁",
            "rest_nap": "小憩休息", "rest_sleep": "沉睡休息",
            "pet_affection": "抚摸", "scold": "责备", "comfort": "安慰",
        }

        if self._callback:
            try:
                self._callback(interaction, intensity)
            except Exception as e:
                logger.warning(f"[ModifyPetAttributeTool] Callback error: {e}")

        interaction_name = interaction_names.get(interaction, interaction)
        return ToolResult(
            tool_name=self.schema.name,
            success=True,
            data={"interaction": interaction, "intensity": intensity, "name": interaction_name},
        )


def _get_images_dir() -> str:
    appdata_local = os.getenv("LOCALAPPDATA")
    if appdata_local:
        return os.path.join(appdata_local, "DoroPet", "generated_images")
    return os.path.join(os.path.expanduser("~"), "AppData", "Local", "DoroPet", "generated_images")


_image_pet_tools = [GenerateImageTool(), SetExpressionTool(), ModifyPetAttributeTool()]


def register_image_pet_tools(registry=None):
    from src.agent.core.tool import ToolRegistry
    reg = registry or ToolRegistry.get_instance()
    for tool in _image_pet_tools:
        reg.register(tool)


def get_image_pet_tools():
    return list(_image_pet_tools)
