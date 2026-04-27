import logging
from typing import Optional, List

from src.agent.tools.filesystem_tools import register_file_system_tools, _file_system_tools
from src.agent.tools.search_tools import register_search_tools, _search_tools
from src.agent.tools.image_pet_tools import register_image_pet_tools, _image_pet_tools
from src.agent.tools.code_executor import register_code_executor_tools, _code_executor_tools

logger = logging.getLogger("DoroPet.Agent")


def register_all_tools(registry=None):
    from src.agent.core.tool import ToolRegistry
    reg = registry or ToolRegistry.get_instance()

    register_file_system_tools(reg)
    register_search_tools(reg)
    register_image_pet_tools(reg)
    register_code_executor_tools(reg)

    logger.info(f"[AgentTools] Registered {len(reg.list_tool_names())} tools")


def get_all_tools() -> List:
    return list(_file_system_tools) + list(_search_tools) + list(_image_pet_tools) + list(_code_executor_tools)
