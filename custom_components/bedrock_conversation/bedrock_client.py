"""AWS Bedrock client for conversation agents."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from homeassistant.components import conversation
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers import entity_registry as er, area_registry as ar, template, llm
from homeassistant.util import color

from .const import (
    CONF_AWS_REGION,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    CONF_MODEL_ID,
    CONF_PROMPT,
    CONF_SELECTED_LANGUAGE,
    CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_TOP_K,
    DEFAULT_AWS_REGION,
    DEFAULT_MODEL_ID,
    DEFAULT_SELECTED_LANGUAGE,
    DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_TOP_K,
    DEFAULT_PROMPT,
    PERSONA_PROMPTS,
    CURRENT_DATE_PROMPT,
    DEVICES_PROMPT,
    SERVICE_TOOL_NAME,
)
from .utils import closest_color

_LOGGER = logging.getLogger(__name__)

type BedrockConfigEntry = ConfigEntry[BedrockClient]


@dataclass
class DeviceInfo:
    """Information about a device for prompt generation."""
    entity_id: str
    name: str
    state: str
    area_id: str | None
    area_name: str | None
    attributes: list[str]


class BedrockClient:
    """Client for AWS Bedrock conversation agents."""
    
    def __init__(self, hass: HomeAssistant, data: dict[str, Any], options: dict[str, Any]) -> None:
        """Initialize the Bedrock client."""
        self.hass = hass
        self._data = data
        self._options = options
        
        # AWS credentials
        aws_region = data.get(CONF_AWS_REGION, DEFAULT_AWS_REGION)
        aws_access_key_id = data.get(CONF_AWS_ACCESS_KEY_ID)
        aws_secret_access_key = data.get(CONF_AWS_SECRET_ACCESS_KEY)
        aws_session_token = data.get(CONF_AWS_SESSION_TOKEN)
        
        # Initialize boto3 client
        session_config = {
            'region_name': aws_region,
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
        }
        
        if aws_session_token:
            session_config['aws_session_token'] = aws_session_token
        
        self._bedrock_runtime = boto3.client('bedrock-runtime', **session_config)
        self._region = aws_region
        
        _LOGGER.info("Initialized Bedrock client for region %s", aws_region)
    
    def _get_exposed_entities(self) -> list[DeviceInfo]:
        """Get all exposed entities with their information."""
        entity_registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)
        
        extra_attributes = self._options.get(
            CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
            DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE
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
            
            # Media title
            if "media_title" in extra_attributes:
                media_title = state.attributes.get("media_title")
                if media_title:
                    attributes.append(f"playing:{media_title}")
            
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
    
    def _generate_system_prompt(
        self,
        prompt_template: str,
        llm_api: llm.APIInstance | None,
        options: dict[str, Any]
    ) -> str:
        """Generate the system prompt with device information."""
        language = options.get(CONF_SELECTED_LANGUAGE, DEFAULT_SELECTED_LANGUAGE)
        
        # Get persona and date prompts
        persona_prompt = PERSONA_PROMPTS.get(language, PERSONA_PROMPTS["en"])
        date_prompt = CURRENT_DATE_PROMPT.get(language, CURRENT_DATE_PROMPT["en"])
        devices_label = DEVICES_PROMPT.get(language, DEVICES_PROMPT["en"])
        
        # Get exposed devices
        devices = self._get_exposed_entities()
        
        # Prepare template context
        template_context = {
            "persona": persona_prompt,
            "current_date": date_prompt,
            "devices": devices_label,
        }
        
        # Replace placeholders
        prompt = prompt_template
        prompt = prompt.replace("<persona>", persona_prompt)
        prompt = prompt.replace("<current_date>", date_prompt)
        prompt = prompt.replace("<devices>", devices_label)
        
        # Render the Jinja2 template with devices
        try:
            rendered = template.Template(prompt, self.hass).async_render(
                {"devices": [d.__dict__ for d in devices]},
                parse_result=False
            )
        except TemplateError as err:
            _LOGGER.error("Error rendering prompt template: %s", err)
            raise
        
        return rendered
    
    def _format_tools_for_bedrock(self, llm_api: llm.APIInstance | None) -> list[dict[str, Any]]:
        """Format Home Assistant tools for Bedrock tool use."""
        if not llm_api or not llm_api.tools:
            return []
        
        bedrock_tools = []
        
        for tool in llm_api.tools:
            tool_def = {
                "toolSpec": {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
            }
            
            # Convert voluptuous schema to JSON schema
            if hasattr(tool, 'parameters') and tool.parameters:
                # For HassCallService tool
                if tool.name == SERVICE_TOOL_NAME:
                    tool_def["toolSpec"]["inputSchema"]["json"] = {
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
                        message_content.append({
                            "toolUse": {
                                "toolUseId": f"tool_{id(tool_call)}",
                                "name": tool_call.name,
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
        
        # Build request
        request_body = {
            "anthropicVersion": "bedrock-2023-05-31",
            "maxTokens": max_tokens,
            "temperature": temperature,
            "topP": top_p,
            "messages": messages
        }
        
        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]
        
        # Add tools if available
        tools = self._format_tools_for_bedrock(llm_api)
        if tools:
            request_body["tools"] = tools
        
        # Only add top_k for Claude models
        if "anthropic.claude" in model_id:
            request_body["topK"] = top_k
        
        try:
            _LOGGER.debug("Calling Bedrock model %s", model_id)
            response = await self.hass.async_add_executor_job(
                self._bedrock_runtime.invoke_model,
                model_id,
                json.dumps(request_body)
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
