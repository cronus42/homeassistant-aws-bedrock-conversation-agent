"""AWS Bedrock client for conversation agents."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import re

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from homeassistant.core import HomeAssistant
from homeassistant.components import conversation
from homeassistant.components.conversation import agent, history as conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    entity_registry as er,
    intent,
    llm,
    template,
)
from homeassistant.util import dt as dt_util

from .utils import closest_color
from .const import (
    ALLOWED_SERVICE_CALL_ARGUMENTS,
    ATTR_ENTITY_ID,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_DEFAULT_REGION,
    CONF_AWS_REGION,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
    CURRENT_DATE_PROMPT,
    DEFAULT_AWS_REGION,
    DEFAULT_EXTRA_ATTRIBUTES,
    DEVICES_PROMPT,
    DOMAIN,
    PERSONA_PROMPTS,
    SERVICE_TOOL_ALLOWED_DOMAINS,
    SERVICE_TOOL_ALLOWED_SERVICES,
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
        self._setup_bedrock_client()

    def _setup_bedrock_client(self) -> None:
        """Set up the AWS Bedrock client."""
        options = self.entry.options
        
        # Get AWS credentials from config entry
        aws_access_key_id = self.entry.data.get(CONF_AWS_ACCESS_KEY_ID)
        aws_secret_access_key = self.entry.data.get(CONF_AWS_SECRET_ACCESS_KEY)
        aws_session_token = self.entry.data.get(CONF_AWS_SESSION_TOKEN)
        
        # Get region - try entry.options first, then entry.data, then default
        aws_region = options.get(
            CONF_AWS_REGION, 
            self.entry.data.get(CONF_AWS_REGION, 
            self.entry.data.get(CONF_AWS_DEFAULT_REGION, DEFAULT_AWS_REGION)))
        
        # Create the boto3 session
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=aws_region,
        )
        
        self._bedrock_runtime = session.client('bedrock-runtime')
        _LOGGER.debug("Bedrock client initialized with region %s", aws_region)

    async def _get_exposed_entities(self, options: dict[str, Any]) -> list[DeviceInfo]:
        """Get exposed entities with their states."""
        entity_registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)
        exposed_entities = []
        
        # Get the list of additional attributes to expose
        extra_attributes_to_expose = options.get(
            CONF_EXTRA_ATTRIBUTES_TO_EXPOSE, DEFAULT_EXTRA_ATTRIBUTES
        )
        
        for state in self.hass.states.async_all():
            if not agent.should_expose(state, "conversation"):
                continue
                
            entity_id = state.entity_id
            
            # Get area info if available
            area_id = None
            area_name = None
            entity_entry = entity_registry.async_get(entity_id)
            if entity_entry and entity_entry.area_id:
                area_id = entity_entry.area_id
                area = area_registry.async_get_area(area_id)
                if area:
                    area_name = area.name
                    
            # Get formatted attributes for this entity
            attributes = []
            for attr_name in extra_attributes_to_expose:
                if attr_name in state.attributes:
                    attr_value = state.attributes[attr_name]
                    
                    # Format special attributes in a more readable way
                    if attr_name == "brightness" and attr_value is not None:
                        # Convert brightness (0-255) to percentage
                        attributes.append(f"brightness: {round((attr_value / 255) * 100)}%")
                    elif attr_name == "rgb_color" and attr_value is not None:
                        # Convert RGB to color name
                        color_name = closest_color(attr_value)
                        attributes.append(f"color: {color_name}")
                    elif attr_name in ["temperature", "current_temperature", "target_temperature"]:
                        attributes.append(f"temperature: {attr_value}°")
                    elif attr_name == "humidity":
                        attributes.append(f"humidity: {attr_value}%")
                    elif attr_name == "fan_mode":
                        attributes.append(f"fan mode: {attr_value}")
                    elif attr_name == "hvac_mode":
                        attributes.append(f"mode: {attr_value}")
                    elif attr_name == "hvac_action":
                        attributes.append(f"currently: {attr_value}")
                    elif attr_name == "preset_mode":
                        attributes.append(f"preset: {attr_value}")
                    elif attr_name == "media_title" and attr_value:
                        attributes.append(f"playing: {attr_value}")
                    elif attr_name == "media_artist" and attr_value:
                        attributes.append(f"artist: {attr_value}")
                    elif attr_name == "volume_level" and attr_value is not None:
                        # Convert volume (0-1) to percentage
                        attributes.append(f"volume: {round(attr_value * 100)}%")
                    else:
                        attributes.append(f"{attr_name}: {attr_value}")
            
            exposed_entities.append(
                DeviceInfo(
                    entity_id=entity_id,
                    name=state.name,
                    state=state.state,
                    attributes=attributes,
                    area_id=area_id,
                    area_name=area_name,
                )
            )
            
        return exposed_entities

    async def _generate_system_prompt(
        self, prompt_template: str, llm_api: llm.APIInstance | None, options: dict[str, Any]
    ) -> str:
        """Generate system prompt with device state information."""
        try:
            # Set language-specific persona prompt, date format, and device label
            language = options.get("language", "en")
            persona_prompt = PERSONA_PROMPTS.get(language, PERSONA_PROMPTS["en"])
            current_date_prompt = CURRENT_DATE_PROMPT.get(language, CURRENT_DATE_PROMPT["en"])
            devices_prompt = DEVICES_PROMPT.get(language, DEVICES_PROMPT["en"])
            
            # Replace simple placeholders
            prompt = prompt_template.replace("<persona>", persona_prompt)
            prompt = prompt.replace("<current_date>", current_date_prompt)
            prompt = prompt.replace("<devices>", devices_prompt)
            
            # Get exposed entities and their states
            device_info = await self._get_exposed_entities(options)
            
            # Create the Jinja template
            template_obj = template.Template(prompt, self.hass)
            
            # Render the template
            current_date = dt_util.now()
            prompt = template_obj.async_render(
                devices=device_info,
                current_date=current_date,
                strict=False,
            )
            
            return prompt
            
        except TemplateError as err:
            _LOGGER.error("Error rendering system prompt template: %s", err)
            raise HomeAssistantError(f"Error rendering system prompt template: {err}")

    def _format_tools_for_bedrock(self, llm_api: llm.APIInstance | None, model_id: str = "") -> list[dict[str, Any]]:
        """Format Home Assistant tools for Bedrock tool use."""
        if not llm_api or not llm_api.tools:
            return []
        
        bedrock_tools = []

        # Check if we're using a Claude model that needs newer format
        is_claude3 = "anthropic.claude-3" in model_id
        
        for tool in llm_api.tools:
            if is_claude3:
                # Claude 3 format (newer Bedrock API)
                tool_def = {
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
            else:
                # Older format for other models
                tool_def = {
                    "type": "function",
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
                    schema_key = "parameters" if is_claude3 else "input_schema"
                    if is_claude3:
                        tool_def["function"][schema_key] = {
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
                    else:
                        tool_def[schema_key] = {
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
                    "content": [{"text": content.content}]
                })
            
            elif isinstance(content, conversation.AssistantContent):
                message_content = []
                
                if content.content:
                    message_content.append({"text": content.content})
                
                if content.tool_calls:
                    for tool_call in content.tool_calls:
                        # Fix: Check if tool_call has 'name' attribute, otherwise use 'function'
                        tool_name = tool_call.name if hasattr(tool_call, 'name') else tool_call.function
                        message_content.append({
                            "toolUse": {
                                "toolUseId": f"tool_{id(tool_call)}",
                                "name": tool_name,
                                "input": tool_call.tool_args
                            }
                        })
                
                if message_content:
                    messages.append({
                        "role": "assistant",
                        "content": message_content
                    })
            
            elif isinstance(content, conversation.ToolResultContent):
                # Tool results go in user messages in Bedrock
                if messages and messages[-1]["role"] == "user":
                    # Append to last user message
                    messages[-1]["content"].append({
                        "toolResult": {
                            "toolUseId": content.tool_call_id,
                            "content": [{"json": content.result}]
                        }
                    })
                else:
                    # Create new user message
                    messages.append({
                        "role": "user",
                        "content": [{
                            "toolResult": {
                                "toolUseId": content.tool_call_id,
                                "content": [{"json": content.result}]
                            }
                        }]
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
        
        # Build messages
        messages = self._build_bedrock_messages(conversation_content)
        
        # Build request - Update to use snake_case for keys
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": messages
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
        
        # Add tools if available
        tools = self._format_tools_for_bedrock(llm_api, model_id)
        if tools:
            request_body["tools"] = tools
        
        # Only add top_k for Claude models
        if "anthropic.claude" in model_id:
            request_body["top_k"] = top_k
        
        try:
            _LOGGER.debug("Calling Bedrock model %s", model_id)
            _LOGGER.debug("Request body: %s", json.dumps(request_body))
            # invoke_model requires keyword arguments
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
