"""AWS Bedrock Conversation integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.exceptions import HomeAssistantError
import voluptuous as vol
import logging

# Essential imports
from .const import (
    DOMAIN, 
    HOME_LLM_API_ID,
    SERVICE_TOOL_NAME,
    SERVICE_TOOL_ALLOWED_DOMAINS,
    SERVICE_TOOL_ALLOWED_SERVICES,
)
from .bedrock_client import BedrockClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]

# Allowed arguments for service calls
ALLOWED_SERVICE_CALL_ARGUMENTS = [
    "brightness",
    "brightness_pct",
    "rgb_color",
    "temperature",
    "hvac_mode",
    "target_temp_high",
    "target_temp_low",
    "fan_mode",
    "preset_mode",
    "humidity",
    "position",
    "tilt_position",
    "volume_level",
    "media_content_id",
    "media_content_type",
    "value",
]


class HassServiceTool(llm.Tool):
    """Tool for calling Home Assistant services."""

    name = SERVICE_TOOL_NAME
    description = (
        "Calls a Home Assistant service to control devices. "
        "Use this to turn devices on/off, adjust settings, etc."
    )

    parameters = vol.Schema(
        {
            vol.Required("service"): str,
            vol.Required("target_device"): str,
        }
    )

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the tool."""
        self.hass = hass

    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> dict:
        """Call the Home Assistant service."""
        service = tool_input.tool_args.get("service")
        target_device = tool_input.tool_args.get("target_device")

        if not service or not target_device:
            return {
                "result": "error",
                "error": "Missing required parameters: service and target_device",
            }

        # Validate service
        try:
            domain, service_name = service.split(".", 1)
        except ValueError:
            return {
                "result": "error",
                "error": f"Invalid service format: {service}. Expected 'domain.service'",
            }

        # Check if domain is allowed
        if domain not in SERVICE_TOOL_ALLOWED_DOMAINS:
            return {
                "result": "error",
                "error": f"Service domain '{domain}' is not allowed",
            }

        # Check if service is allowed
        if service not in SERVICE_TOOL_ALLOWED_SERVICES:
            return {
                "result": "error",
                "error": f"Service '{service}' is not allowed",
            }

        # Build service data
        service_data = {ATTR_ENTITY_ID: target_device}

        # Add allowed additional arguments
        for key, value in tool_input.tool_args.items():
            if key in ALLOWED_SERVICE_CALL_ARGUMENTS:
                service_data[key] = value

        try:
            await hass.services.async_call(
                domain,
                service_name,
                service_data,
                blocking=True,
            )
            return {
                "result": "success",
                "service": service,
                "target": target_device,
            }
        except Exception as err:
            _LOGGER.error("Error calling service %s: %s", service, err)
            return {
                "result": "error",
                "error": str(err),
            }


class BedrockServicesAPI(llm.API):
    """Bedrock Services LLM API."""

    def __init__(self, hass: HomeAssistant, id: str, name: str) -> None:
        """Initialize the API."""
        self.hass = hass
        self.id = id
        self.name = name

    async def async_get_api_instance(
        self, llm_context: llm.LLMContext
    ) -> llm.APIInstance:
        """Get API instance."""
        tools = [HassServiceTool(self.hass)]
        
        return llm.APIInstance(
            api=self,
            api_prompt=(
                "You can control Home Assistant devices using the HassCallService tool. "
                "Always use entity IDs from the device list provided in the system prompt."
            ),
            llm_context=llm_context,
            tools=tools,
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWS Bedrock Conversation from a config entry."""
    # Register the LLM API if not already registered
    if not llm.async_get_api(hass, HOME_LLM_API_ID):
        llm.async_register_api(hass, BedrockServicesAPI(hass, HOME_LLM_API_ID, "AWS Bedrock Services"))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Create the Bedrock client and store it in the entry's runtime_data
    entry.runtime_data = {}
    entry.runtime_data["client"] = BedrockClient(hass, entry)

    await hass.config_entries.async_forward_entry_setup(entry, Platform.CONVERSATION)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
