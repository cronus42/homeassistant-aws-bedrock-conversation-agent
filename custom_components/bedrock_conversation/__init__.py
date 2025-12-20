"""The AWS Bedrock Conversation integration."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform, CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType
import voluptuous as vol

from .const import (
    DOMAIN,
    HOME_LLM_API_ID,
    SERVICE_TOOL_NAME,
    SERVICE_TOOL_ALLOWED_SERVICES,
    SERVICE_TOOL_ALLOWED_DOMAINS,
    ALLOWED_SERVICE_CALL_ARGUMENTS,
)
from .bedrock_client import BedrockClient, BedrockConfigEntry

_LOGGER = logging.getLogger(__name__)

PLATFORMS = (Platform.CONVERSATION,)


async def async_setup_entry(hass: HomeAssistant, entry: BedrockConfigEntry) -> bool:
    """Set up AWS Bedrock Conversation from a config entry."""
    
    # Register the Home Assistant Services API if not already registered
    if not any([x.id == HOME_LLM_API_ID for x in llm.async_get_apis(hass)]):
        llm.async_register_api(hass, BedrockServicesAPI(hass))
    
    # Store entry in hass data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry
    
    # Create the Bedrock client
    _LOGGER.debug("Creating AWS Bedrock client")
    entry.runtime_data = BedrockClient(hass, dict(entry.data), dict(entry.options))
    
    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup update listener
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    return True


async def _async_update_listener(hass: HomeAssistant, entry: BedrockConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BedrockConfigEntry) -> bool:
    """Unload AWS Bedrock Conversation."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


class HassServiceTool(llm.Tool):
    """Tool to execute Home Assistant services."""
    
    name: Final[str] = SERVICE_TOOL_NAME
    description: Final[str] = "Executes a Home Assistant service to control devices"
    
    parameters = vol.Schema({
        vol.Required('service'): str,
        vol.Required('target_device'): str,
        vol.Optional('rgb_color'): str,
        vol.Optional('brightness'): vol.Coerce(float),
        vol.Optional('temperature'): vol.Coerce(float),
        vol.Optional('humidity'): vol.Coerce(float),
        vol.Optional('fan_mode'): str,
        vol.Optional('hvac_mode'): str,
        vol.Optional('preset_mode'): str,
        vol.Optional('duration'): str,
        vol.Optional('item'): str,
    })
    
    ALLOWED_SERVICES: Final[list[str]] = SERVICE_TOOL_ALLOWED_SERVICES
    ALLOWED_DOMAINS: Final[list[str]] = SERVICE_TOOL_ALLOWED_DOMAINS
    
    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> JsonObjectType:
        """Call the tool."""
        try:
            domain, service = tuple(tool_input.tool_args["service"].split("."))
        except (ValueError, KeyError):
            return {"result": "error", "error": "invalid service format"}
        
        target_device = tool_input.tool_args.get("target_device")
        if not target_device:
            return {"result": "error", "error": "missing target_device"}
        
        if domain not in self.ALLOWED_DOMAINS or service not in self.ALLOWED_SERVICES:
            return {"result": "error", "error": f"service {domain}.{service} not allowed"}
        
        if domain == "script" and service not in ["reload", "turn_on", "turn_off", "toggle"]:
            return {"result": "error", "error": "script service not allowed"}
        
        service_data = {ATTR_ENTITY_ID: target_device}
        for attr in ALLOWED_SERVICE_CALL_ARGUMENTS:
            if attr in tool_input.tool_args:
                service_data[attr] = tool_input.tool_args[attr]
        
        try:
            await hass.services.async_call(
                domain,
                service,
                service_data=service_data,
                blocking=True,
            )
        except Exception as ex:
            _LOGGER.exception("Failed to execute service for model")
            return {"result": "error", "error": str(ex)}
        
        return {"result": "success"}


class BedrockServicesAPI(llm.API):
    """API to call Home Assistant services via tool calling."""
    
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API."""
        super().__init__(
            hass=hass,
            id=HOME_LLM_API_ID,
            name="Home Assistant Services (Bedrock)",
        )
    
    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """Return the instance of the API."""
        return llm.APIInstance(
            api=self,
            api_prompt="Call services in Home Assistant to control devices. Use the HassCallService tool.",
            llm_context=llm_context,
            tools=[HassServiceTool()],
        )
