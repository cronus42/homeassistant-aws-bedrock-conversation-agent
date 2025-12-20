"""Utility functions for AWS Bedrock Conversation."""
import logging
import webcolors
from typing import Any
from webcolors import CSS3

_LOGGER = logging.getLogger(__name__)

CSS3_NAME_TO_RGB = {
    name: webcolors.name_to_rgb(name, CSS3)
    for name in webcolors.names(CSS3)
}


def closest_color(requested_color: tuple[int, int, int]) -> str:
    """Find the closest CSS3 color name to the requested RGB color."""
    min_colors = {}
    
    for name, rgb in CSS3_NAME_TO_RGB.items():
        r_c, g_c, b_c = rgb
        rd = (r_c - requested_color[0]) ** 2
        gd = (g_c - requested_color[1]) ** 2
        bd = (b_c - requested_color[2]) ** 2
        min_colors[(rd + gd + bd)] = name
    
    return min_colors[min(min_colors.keys())]


def format_tool_call_for_bedrock(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Format a tool call in Bedrock's expected format."""
    return {
        "toolUseId": f"tool_{id(tool_input)}",
        "name": tool_name,
        "input": tool_input
    }


def parse_bedrock_tool_use(content_block: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    """Parse a tool use block from Bedrock response.
    
    Returns: (tool_use_id, tool_name, tool_input) or None
    """
    if content_block.get("type") != "tool_use":
        return None
    
    tool_use_id = content_block.get("toolUseId", "")
    tool_name = content_block.get("name", "")
    tool_input = content_block.get("input", {})
    
    return tool_use_id, tool_name, tool_input
