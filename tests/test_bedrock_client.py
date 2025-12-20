"""Tests for Bedrock client components."""
import pytest

from custom_components.bedrock_conversation.bedrock_client import DeviceInfo


def test_device_info_dataclass():
    """Test DeviceInfo dataclass creation."""
    device = DeviceInfo(
        entity_id="light.living_room",
        name="Living Room Light",
        state="on",
        area_id="area_living_room",
        area_name="Living Room",
        attributes=["80%", "blue"]
    )
    
    assert device.entity_id == "light.living_room"
    assert device.name == "Living Room Light"
    assert device.state == "on"
    assert device.area_name == "Living Room"
    assert "80%" in device.attributes
    assert "blue" in device.attributes
