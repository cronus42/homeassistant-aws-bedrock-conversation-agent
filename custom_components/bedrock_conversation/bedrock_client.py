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
from homeassistant.components.conversation import (
    SystemContent, UserContent, AssistantContent, ToolResultContent, Content
)
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
    intent,
    llm,
    template,
)
from homeassistant.util import dt as dt_util

from .utils import closest_color
from .const import (
    DEFAULT_MODEL_ID,
    ALLOWED_SERVICE_CALL_ARGUMENTS,
    ATTR_ENTITY_ID,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_DEFAULT_REGION,
    CONF_AWS_REGION,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
    CONF_MODEL_ID,
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
