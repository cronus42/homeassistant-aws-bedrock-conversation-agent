"""AWS Bedrock Conversation integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
import logging

# Essential imports
from .const import DOMAIN, HOME_LLM_API_ID
from .bedrock_client import BedrockClient
from .conversation import BedrockConversationAgent, BedrockServicesAPI, HassServiceTool

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CONVERSATION]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWS Bedrock Conversation from a config entry."""
    # Register the LLM API if not already registered
    if not llm.async_get_api(hass, HOME_LLM_API_ID):
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
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
