"The AWS Bedrock Conversation integration."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform, CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent, llm
from homeassistant.helpers.typing import ConfigType

from .const import (
    ALLOWED_SERVICE_CALL_ARGUMENTS,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_DEFAULT_REGION,
    CONF_AWS_REGION,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    DOMAIN,
    HOME_LLM_API_ID,
    SERVICE_TOOL_ALLOWED_DOMAINS,
    SERVICE_TOOL_ALLOWED_SERVICES,
    SERVICE_TOOL_NAME,
)
from .bedrock_client import BedrockClient, BedrockConfigEntry

_LOGGER = logging.getLogger(__name__)


class HassServiceTool(llm.Tool):
    """Tool for calling Home Assistant services."""

    name = SERVICE_TOOL_NAME
    description = "Call a Home Assistant service to control devices"

    @property
    def parameters(self) -> dict:
        """Return parameters."""
        return {
            "service": {
                "description": "The service to call (e.g., 'light.turn_on')",
                "type": "string",
                "required": True,
            },
            "target_device": {
                "description": "The entity_id of the device to control",
                "type": "string",
                "required": True,
            },
            "brightness": {
                "description": "Brightness level (0-255)",
                "type": "number",
                "required": False,
            },
            "rgb_color": {
                "description": "RGB color as comma-separated values (e.g., '255,0,0')",
                "type": "string",
                "required": False,
            },
            "temperature": {
                "description": "Temperature setting",
                "type": "number",
                "required": False,
            },
            "humidity": {
                "description": "Humidity setting",
                "type": "number",
                "required": False,
            },
            "fan_mode": {
                "description": "Fan mode setting",
                "type": "string",
                "required": False,
            },
            "hvac_mode": {
                "description": "HVAC mode setting",
                "type": "string",
                "required": False,
            },
            "preset_mode": {
                "description": "Preset mode",
                "type": "string",
                "required": False,
            },
            "item": {
                "description": "Item to add to a list",
                "type": "string",
                "required": False,
            },
            "duration": {
                "description": "Duration for the action",
                "type": "string",
                "required": False,
            },
        }

    async def _run(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> dict:
        """Call a Home Assistant service."""
        _LOGGER.debug("Service tool called with %s", tool_input.tool_args)

        try:
            service = tool_input.tool_args["service"]
            target_device = tool_input.tool_args["target_device"]
        except KeyError as err:
            _LOGGER.error("Missing required parameter: %s", err)
            return {"result": "error", "error": f"Missing required parameter: {err}"}

        # Verify domain and service are allowed
        domain, service_name = service.split(".")

        # Check if the domain is allowed
        if domain not in SERVICE_TOOL_ALLOWED_DOMAINS:
            _LOGGER.warning("Domain %s is not allowed", domain)
            return {"result": "error", "error": f"Domain {domain} is not allowed"}

        # Check if the service is allowed
        service_key = f"{domain}.{service_name}"
        if service_key not in SERVICE_TOOL_ALLOWED_SERVICES:
            _LOGGER.warning("Service %s is not allowed", service_key)
            return {"result": "error", "error": f"Service {service} is not allowed"}

        # Build service data
        service_data = {ATTR_ENTITY_ID: target_device}

        # Add any allowed additional parameters
        for arg, value in tool_input.tool_args.items():
            if arg in ("service", "target_device"):
                continue  # Skip already processed arguments
            if arg in ALLOWED_SERVICE_CALL_ARGUMENTS:
                service_data[arg] = value
            else:
                _LOGGER.warning("Ignoring unsupported parameter: %s", arg)

        try:
            await hass.services.async_call(
                domain, service_name, service_data, blocking=True
            )
            _LOGGER.debug(
                "Service %s called successfully for %s with data %s",
                service,
                target_device,
                service_data,
            )
            return {"result": "success", "service": service, "target": target_device}
        except HomeAssistantError as err:
            _LOGGER.error("Error calling service %s: %s", service, err)
            return {"result": "error", "error": str(err)}


class BedrockServicesAPI(llm.API):
    """AWS Bedrock LLM API that exposes Home Assistant services."""

    @property
    def name(self) -> str:
        """Return the name of the API."""
        return "AWS Bedrock Services"

    @property
    def description(self) -> str:
        """Return the description of the API."""
        return "API for AWS Bedrock that exposes Home Assistant services"

    async def async_get_api_instance(
        self, hass: HomeAssistant, llm_context: llm.LLMContext
    ) -> llm.APIInstance:
        """Return an API instance that can be used by an LLM."""
        return llm.APIInstance(
            api_prompt="You can control devices using the HassCallService tool.",
            tools=[HassServiceTool()],
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWS Bedrock Conversation from a config entry."""
    # Register the LLM API if not already registered
    if not llm.async_get_api_instance(hass, HOME_LLM_API_ID, None):
        llm.async_register_api(hass, BedrockServicesAPI(hass, HOME_LLM_API_ID, "AWS Bedrock Services"), HOME_LLM_API_ID)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Create the Bedrock client and store it in the entry's runtime_data
    entry.runtime_data = {}
    entry.runtime_data["client"] = BedrockClient(hass, entry)

    await hass.config_entries.async_forward_entry_setup(entry, Platform.CONVERSATION)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload AWS Bedrock Conversation."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.CONVERSATION]
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
