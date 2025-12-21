
"Config flow for AWS Bedrock Conversation integration."
import asyncio
import logging
from typing import Any

import boto3
import voluptuous as vol
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    BotoCoreError,
)

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    AVAILABLE_MODELS,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_DEFAULT_REGION,
    CONF_AWS_REGION,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
    CONF_LLM_HASS_API,
    CONF_MAX_TOKENS,
    CONF_MAX_TOOL_CALL_ITERATIONS,
    CONF_MODEL_ID,
    CONF_PROMPT,
    CONF_REFRESH_SYSTEM_PROMPT,
    CONF_REMEMBER_CONVERSATION,
    CONF_REMEMBER_NUM_INTERACTIONS,
    CONF_TEMPERATURE,
    CONF_TOP_K,
    CONF_TOP_P,
    DEFAULT_AWS_REGION,
    DEFAULT_EXTRA_ATTRIBUTES,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOOL_CALL_ITERATIONS,
    DEFAULT_MODEL_ID,
    DEFAULT_PROMPT,
    DEFAULT_REFRESH_SYSTEM_PROMPT,
    DEFAULT_REMEMBER_CONVERSATION,
    DEFAULT_REMEMBER_NUM_INTERACTIONS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    DOMAIN,
    HOME_LLM_API_ID,
)

_LOGGER = logging.getLogger(__name__)


async def validate_aws_credentials(hass: HomeAssistant, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str | None = None, aws_region: str | None = None) -> dict[str, str] | None:
    """Validate AWS credentials by attempting to list foundation models."""
    if aws_region is None:
        aws_region = DEFAULT_AWS_REGION
    
    try:
        # Run boto3 client creation in executor to avoid blocking
        def _create_client():
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=aws_region,
            )
            return session.client("bedrock")

        bedrock_client = await hass.async_add_executor_job(_create_client)
        
        # Try to list foundation models to verify credentials work
        await hass.async_add_executor_job(bedrock_client.list_foundation_models)
        return None
        
    except NoCredentialsError as e:
        _LOGGER.debug("Caught NoCredentialsError: %s", e)
        return {"base": "invalid_credentials"}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        _LOGGER.debug("Caught ClientError with code %s: %s", error_code, e)
        if error_code == "UnrecognizedClientException":
            return {"base": "invalid_credentials"}
        elif error_code == "AccessDeniedException":
            return {"base": "access_denied"}
        else:
            _LOGGER.error("Unexpected error validating AWS credentials: %s", e)
            return {"base": "unknown_error"}
    except BotoCoreError as e:
        _LOGGER.debug("Caught BotoCoreError: %s", e)
        _LOGGER.error("BotoCore error validating AWS credentials: %s", e)
        return {"base": "unknown_error"}
    except Exception as e:
        _LOGGER.debug("Caught unexpected Exception: %s", e)
        _LOGGER.error("Unknown error validating AWS credentials: %s", e)
        return {"base": "unknown_error"}
