"""AWS Bedrock client for conversation agents."""
from __future__ import annotations

import json
import logging
from typing import Any
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import (
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import (
    area_registry as ar,
    entity_registry as er,
    llm,
    template,
)

from .utils import closest_color
from .const import (
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_REGION,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
    CONF_MAX_TOKENS,
    CONF_MODEL_ID,
    CONF_SELECTED_LANGUAGE,
    CONF_TEMPERATURE,
    CONF_TOP_K,
    CONF_TOP_P,
    CURRENT_DATE_PROMPT,
    DEFAULT_AWS_REGION,
    DEFAULT_EXTRA_ATTRIBUTES,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_ID,
    DEFAULT_SELECTED_LANGUAGE,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    DEVICES_PROMPT,
    PERSONA_PROMPTS,
    SERVICE_TOOL_NAME,
)

_LOGGER = logging.getLogger(__name__)

BedrockConfigEntry = ConfigEntry


@dataclass
class DeviceInfo:
    """Class to hold device information."""

    entity_id: str
    name: str
    state: str
    attributes: list[str]
    area_id: str | None = None
    area_name: str | None = None


class BedrockClient:
    """AWS Bedrock client."""

    def __init__(self, hass: HomeAssistant, entry: BedrockConfigEntry) -> None:
        """Initialize the client."""
        self.hass = hass
        self.entry = entry
        self._bedrock_runtime = None
        self._client_lock = None

    def _create_bedrock_client(self) -> Any:
        """Create the AWS Bedrock client (runs in executor)."""
        options = self.entry.options
        
        # Get AWS credentials from config entry
        aws_access_key_id = self.entry.data.get(CONF_AWS_ACCESS_KEY_ID)
        aws_secret_access_key = self.entry.data.get(CONF_AWS_SECRET_ACCESS_KEY)
        aws_session_token = self.entry.data.get(CONF_AWS_SESSION_TOKEN)
        
        # Get region - try entry.options first, then entry.data, then default
        aws_region = options.get(
            CONF_AWS_REGION, 
            self.entry.data.get(CONF_AWS_REGION, DEFAULT_AWS_REGION))
        
        # Create the boto3 session
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=aws_region,
        )
        
        bedrock_runtime = session.client('bedrock-runtime')
        _LOGGER.debug("Bedrock client initialized with region %s", aws_region)
        return bedrock_runtime

    async def _ensure_client(self) -> None:
        """Ensure the Bedrock client is initialized (lazy initialization)."""
        if self._bedrock_runtime is None:
            if self._client_lock is None:
                import asyncio
                self._client_lock = asyncio.Lock()
            
            async with self._client_lock:
                # Double-check after acquiring lock
                if self._bedrock_runtime is None:
                    _LOGGER.debug("Creating Bedrock client in executor")
                    self._bedrock_runtime = await self.hass.async_add_executor_job(
                        self._create_bedrock_client
                    )

    def _get_exposed_entities(self) -> list[DeviceInfo]:
        """Get all exposed entities with their information."""
        entity_registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)
        
        extra_attributes = self.entry.options.get(
            CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
            DEFAULT_EXTRA_ATTRIBUTES
        )
        
        devices = []
        
        for state in self.hass.states.async_all():
            if not async_should_expose(self.hass, "conversation", state.entity_id):
                continue
            
            entity_entry = entity_registry.async_get(state.entity_id)
            area_id = entity_entry.area_id if entity_entry else None
            area_name = None
            
            if area_id:
                area = area_registry.async_get_area(area_id)
                area_name = area.name if area else None
            
            # Extract relevant attributes
            attributes = []
            
            # Brightness
            if state.domain == "light" and "brightness" in extra_attributes:
                brightness = state.attributes.get("brightness")
                if brightness is not None:
                    attributes.append(f"{int(brightness * 100 / 255)}%")
            
            # Color
            if state.domain == "light" and "rgb_color" in extra_attributes:
                rgb_color = state.attributes.get("rgb_color")
                if rgb_color:
                    color_name = closest_color(tuple(rgb_color))
                    attributes.append(color_name)
            
            # Temperature
            if "temperature" in extra_attributes:
                temp = state.attributes.get("temperature")
                if temp is not None:
                    attributes.append(f"{temp}°")
            
            # Current temperature
            if "current_temperature" in extra_attributes:
                temp = state.attributes.get("current_temperature")
                if temp is not None:
                    attributes.append(f"current:{temp}°")
            
            # Target temperature
            if "target_temperature" in extra_attributes:
                temp = state.attributes.get("target_temperature")
                if temp is not None:
                    attributes.append(f"target:{temp}°")
            
            # Humidity
            if "humidity" in extra_attributes:
                humidity = state.attributes.get("humidity")
                if humidity is not None:
                    attributes.append(f"{humidity}%RH")
            
            # Fan mode
            if "fan_mode" in extra_attributes:
                fan_mode = state.attributes.get("fan_mode")
                if fan_mode:
                    attributes.append(f"fan:{fan_mode}")
            
            # HVAC mode
            if "hvac_mode" in extra_attributes:
                hvac_mode = state.attributes.get("hvac_mode")
                if hvac_mode:
                    attributes.append(f"hvac:{hvac_mode}")
            
            # HVAC action
            if "hvac_action" in extra_attributes:
                hvac_action = state.attributes.get("hvac_action")
                if hvac_action:
                    attributes.append(f"action:{hvac_action}")
            
            # Preset mode
            if "preset_mode" in extra_attributes:
                preset = state.attributes.get("preset_mode")
                if preset:
                    attributes.append(f"preset:{preset}")
            
            # Media title
            if "media_title" in extra_attributes:
                media_title = state.attributes.get("media_title")
                if media_title:
                    attributes.append(f"playing:{media_title}")
            
            # Media artist
            if "media_artist" in extra_attributes:
                media_artist = state.attributes.get("media_artist")
                if media_artist:
                    attributes.append(f"artist:{media_artist}")
            
            # Volume level
            if "volume_level" in extra_attributes:
                volume = state.attributes.get("volume_level")
                if volume is not None:
                    attributes.append(f"vol:{int(volume * 100)}%")
            
            devices.append(DeviceInfo(
                entity_id=state.entity_id,
                name=state.attributes.get("friendly_name", state.entity_id),
                state=state.state,
                area_id=area_id,
                area_name=area_name,
                attributes=attributes
            ))
        
        return devices

    async def _generate_system_prompt(
        self,
        prompt_template: str,
        llm_api: llm.APIInstance | None,
        options: dict[str, Any]
    ) -> str:
        """Generate the system prompt with device information."""
        from datetime import datetime
        
        language = options.get(CONF_SELECTED_LANGUAGE, DEFAULT_SELECTED_LANGUAGE)
        
        # Get persona and date prompts
        persona_prompt = PERSONA_PROMPTS.get(language, PERSONA_PROMPTS["en"])
        date_prompt_template = CURRENT_DATE_PROMPT.get(language, CURRENT_DATE_PROMPT["en"])
        devices_template = DEVICES_PROMPT.get(language, DEVICES_PROMPT["en"])
        
        # Get current date/time and format it
        current_datetime = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        date_prompt = date_prompt_template.replace("<current_date>", current_datetime)
        
        # Get exposed devices
        devices = self._get_exposed_entities()
        
        _LOGGER.debug("Found %d exposed devices for system prompt", len(devices))
        
        # First, render the devices section with Jinja
        try:
            devices_rendered = template.Template(devices_template, self.hass).async_render(
                {"devices": [d.__dict__ for d in devices]},
                parse_result=False
            )
        except TemplateError as err:
            _LOGGER.error("Error rendering devices template: %s", err)
            raise
        
        # Now replace placeholders in the main prompt template
        prompt = prompt_template
        prompt = prompt.replace("<persona>", persona_prompt)
        prompt = prompt.replace("<current_date>", date_prompt)
        prompt = prompt.replace("<devices>", devices_rendered)
        
        _LOGGER.debug("Generated system prompt with %d characters", len(prompt))
        
        return prompt

    def _format_tools_for_bedrock(self, llm_api: llm.APIInstance | None) -> list[dict[str, Any]]:
        """Format Home Assistant tools for Bedrock tool use."""
        if not llm_api or not llm_api.tools:
            return []
        
        bedrock_tools = []
        
        for tool in llm_api.tools:
            # Use Anthropic Messages API format (not Converse API)
            tool_def = {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # Convert voluptuous schema to JSON schema
            if hasattr(tool, 'parameters') and tool.parameters:
                # For HassCallService tool
                if tool.name == SERVICE_TOOL_NAME:
                    tool_def["input_schema"] = {
                        "type": "object",
                        "properties": {
                            "service": {
                                "type": "string",
                                "description": "The service to call (e.g., 'light.turn_on')"
                            },
                            "target_device": {
                                "type": "string",
                                "description": "The entity_id of the device to control"
                            },
                            "brightness": {
                                "type": "number",
                                "description": "Brightness level (0-255)"
                            },
                            "rgb_color": {
                                "type": "string",
                                "description": "RGB color as comma-separated values (e.g., '255,0,0')"
                            },
                            "temperature": {
                                "type": "number",
                                "description": "Temperature setting"
                            },
                            "humidity": {
                                "type": "number",
                                "description": "Humidity setting"
                            },
                            "fan_mode": {
                                "type": "string",
                                "description": "Fan mode setting"
                            },
                            "hvac_mode": {
                                "type": "string",
                                "description": "HVAC mode setting"
                            },
                            "preset_mode": {
                                "type": "string",
                                "description": "Preset mode"
                            },
                            "item": {
                                "type": "string",
                                "description": "Item to add to a list"
                            },
                            "duration": {
                                "type": "string",
                                "description": "Duration for the action"
                            }
                        },
                        "required": ["service", "target_device"]
                    }
            
            bedrock_tools.append(tool_def)
        
        return bedrock_tools


    def _build_bedrock_messages(
        self,
        conversation_content: list[conversation.Content]
    ) -> list[dict[str, Any]]:
        """Convert Home Assistant conversation to Bedrock message format."""
        messages = []
        
        for content in conversation_content:
            if isinstance(content, conversation.SystemContent):
                # System prompt is handled separately in Bedrock
                continue
            
            elif isinstance(content, conversation.UserContent):
                messages.append({
                    "role": "user",
                    "content": [{"type": "text", "text": content.content}]
                })
            
            elif isinstance(content, conversation.AssistantContent):
                message_content = []
                
                if content.content:
                    message_content.append({"type": "text", "text": content.content})
                
                if content.tool_calls:
                    for tool_call in content.tool_calls:
                        message_content.append({
                            "type": "tool_use",
                            "id": f"tool_{id(tool_call)}",
                            "name": tool_call.tool_name,
                            "input": tool_call.tool_args
                        })
                
                if message_content:
                    messages.append({
                        "role": "assistant",
                        "content": message_content
                    })
            
            elif isinstance(content, conversation.ToolResultContent):
                # Tool results go in user messages in Bedrock
                tool_result_block = {
                    "type": "tool_result",
                    "tool_use_id": content.tool_call_id,
                    "content": [{"type": "json", "json": content.result}]
                }
                
                if messages and messages[-1]["role"] == "user":
                    # Append to last user message
                    messages[-1]["content"].append(tool_result_block)
                else:
                    # Create new user message
                    messages.append({
                        "role": "user",
                        "content": [tool_result_block]
                    })
        
        return messages

    async def async_generate(
        self,
        conversation_content: list[conversation.Content],
        llm_api: llm.APIInstance | None,
        agent_id: str,
        options: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a response from Bedrock."""
        # Ensure client is initialized before use
        await self._ensure_client()
        
        model_id = options.get(CONF_MODEL_ID, DEFAULT_MODEL_ID)
        max_tokens = options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        temperature = options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        top_p = options.get(CONF_TOP_P, DEFAULT_TOP_P)
        top_k = options.get(CONF_TOP_K, DEFAULT_TOP_K)
        
        # Extract system prompt
        system_prompt = None
        for content in conversation_content:
            if isinstance(content, conversation.SystemContent):
                system_prompt = content.content
                break
        
        _LOGGER.debug("System prompt length: %d characters", len(system_prompt) if system_prompt else 0)
        
        # Build messages
        messages = self._build_bedrock_messages(conversation_content)
        
        # Build request using Anthropic Messages API format (snake_case)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        # System prompt should be a string, not a list
        if system_prompt:
            request_body["system"] = system_prompt
        
        # Add tools if available
        tools = self._format_tools_for_bedrock(llm_api)
        if tools:
            request_body["tools"] = tools
            _LOGGER.debug("Added %d tools to request", len(tools))
        
        # Note: For Claude models, temperature and top_p are mutually exclusive.
        # We use temperature by default and do not include top_p in the request.
        if not "anthropic.claude" in model_id:
            request_body["top_p"] = top_p
        
        try:
            _LOGGER.debug("Calling Bedrock model %s", model_id)
            response = await self.hass.async_add_executor_job(
                lambda: self._bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body)
                )
            )
            
            response_body = json.loads(response['body'].read())
            _LOGGER.debug("Received response from Bedrock: %s", response_body)
            
            return response_body
            
        except ClientError as err:
            _LOGGER.error("AWS Bedrock error: %s", err)
            raise HomeAssistantError(f"Bedrock API error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error calling Bedrock")
            raise HomeAssistantError(f"Unexpected error: {err}") from err
