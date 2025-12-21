"""Test the Bedrock Conversation initialization."""
import pytest
from unittest.mock import MagicMock

from custom_components.bedrock_conversation import HassServiceTool
from custom_components.bedrock_conversation.const import (
    DOMAIN,
    SERVICE_TOOL_NAME,
    DEFAULT_MODEL_ID,
)


def test_domain_constant():
    """Test domain constant."""
    assert DOMAIN == "bedrock_conversation"


def test_default_model():
    """Test default model."""
    assert "claude" in DEFAULT_MODEL_ID


def test_hass_service_tool_definition():
    """Test HassServiceTool definition."""
    # Create a mock hass object
    mock_hass = MagicMock()
    
    tool = HassServiceTool(mock_hass)
    assert tool.name == SERVICE_TOOL_NAME
    assert tool.description
    assert hasattr(tool, "parameters")
