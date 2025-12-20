"""Config flow for AWS Bedrock Conversation integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LLM_HASS_API
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import llm, selector

from .const import (
    DOMAIN,
    CONF_AWS_REGION,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_AWS_SESSION_TOKEN,
    CONF_MODEL_ID,
    CONF_PROMPT,
    CONF_SELECTED_LANGUAGE,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_TOP_K,
    CONF_REQUEST_TIMEOUT,
    CONF_REFRESH_SYSTEM_PROMPT,
    CONF_REMEMBER_CONVERSATION,
    CONF_REMEMBER_NUM_INTERACTIONS,
    CONF_MAX_TOOL_CALL_ITERATIONS,
    CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
    DEFAULT_AWS_REGION,
    DEFAULT_MODEL_ID,
    DEFAULT_SELECTED_LANGUAGE,
    DEFAULT_PROMPT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    DEFAULT_TOP_K,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_REFRESH_SYSTEM_PROMPT,
    DEFAULT_REMEMBER_CONVERSATION,
    DEFAULT_REMEMBER_NUM_INTERACTIONS,
    DEFAULT_MAX_TOOL_CALL_ITERATIONS,
    DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE,
    RECOMMENDED_MODELS,
    HOME_LLM_API_ID,
)

_LOGGER = logging.getLogger(__name__)


async def validate_aws_credentials(
    hass: HomeAssistant,
    region: str,
    access_key_id: str,
    secret_access_key: str,
    session_token: str | None = None
) -> dict[str, str] | None:
    """Validate AWS credentials by attempting to create a Bedrock client."""
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    
    try:
        session_config = {
            'region_name': region,
            'aws_access_key_id': access_key_id,
            'aws_secret_access_key': secret_access_key,
        }
        
        if session_token:
            session_config['aws_session_token'] = session_token
        
        # Test credentials by listing foundation models
        bedrock = boto3.client('bedrock', **session_config)
        await hass.async_add_executor_job(bedrock.list_foundation_models)
        
        return None
    except NoCredentialsError:
        return {"base": "invalid_credentials"}
    except ClientError as err:
        error_code = err.response.get("Error", {}).get("Code", "unknown")
        if error_code in ["InvalidSignatureException", "UnrecognizedClientException"]:
            return {"base": "invalid_credentials"}
        elif error_code == "AccessDeniedException":
            return {"base": "access_denied"}
        else:
            return {"base": "cannot_connect"}
    except Exception as err:
        _LOGGER.exception("Unexpected error validating AWS credentials")
        return {"base": "unknown"}


class BedrockConversationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AWS Bedrock Conversation."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate credentials
            validation_error = await validate_aws_credentials(
                self.hass,
                user_input[CONF_AWS_REGION],
                user_input[CONF_AWS_ACCESS_KEY_ID],
                user_input[CONF_AWS_SECRET_ACCESS_KEY],
                user_input.get(CONF_AWS_SESSION_TOKEN)
            )
            
            if validation_error:
                errors.update(validation_error)
            else:
                # Create entry
                title = f"AWS Bedrock ({user_input[CONF_AWS_REGION]})"
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_AWS_REGION: user_input[CONF_AWS_REGION],
                        CONF_AWS_ACCESS_KEY_ID: user_input[CONF_AWS_ACCESS_KEY_ID],
                        CONF_AWS_SECRET_ACCESS_KEY: user_input[CONF_AWS_SECRET_ACCESS_KEY],
                    },
                    options={
                        CONF_AWS_SESSION_TOKEN: user_input.get(CONF_AWS_SESSION_TOKEN, ""),
                        CONF_MODEL_ID: user_input.get(CONF_MODEL_ID, DEFAULT_MODEL_ID),
                        CONF_SELECTED_LANGUAGE: DEFAULT_SELECTED_LANGUAGE,
                        CONF_PROMPT: DEFAULT_PROMPT,
                        CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
                        CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
                        CONF_TOP_P: DEFAULT_TOP_P,
                        CONF_TOP_K: DEFAULT_TOP_K,
                        CONF_REQUEST_TIMEOUT: DEFAULT_REQUEST_TIMEOUT,
                        CONF_REFRESH_SYSTEM_PROMPT: DEFAULT_REFRESH_SYSTEM_PROMPT,
                        CONF_REMEMBER_CONVERSATION: DEFAULT_REMEMBER_CONVERSATION,
                        CONF_REMEMBER_NUM_INTERACTIONS: DEFAULT_REMEMBER_NUM_INTERACTIONS,
                        CONF_MAX_TOOL_CALL_ITERATIONS: DEFAULT_MAX_TOOL_CALL_ITERATIONS,
                        CONF_EXTRA_ATTRIBUTES_TO_EXPOSE: DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE,
                        CONF_LLM_HASS_API: HOME_LLM_API_ID,
                    }
                )
        
        data_schema = vol.Schema({
            vol.Required(CONF_AWS_REGION, default=DEFAULT_AWS_REGION): str,
            vol.Required(CONF_AWS_ACCESS_KEY_ID): str,
            vol.Required(CONF_AWS_SECRET_ACCESS_KEY): str,
            vol.Optional(CONF_AWS_SESSION_TOKEN): str,
            vol.Optional(CONF_MODEL_ID, default=DEFAULT_MODEL_ID): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECOMMENDED_MODELS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
        })
        
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "aws_region": DEFAULT_AWS_REGION,
            }
        )
    
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BedrockConversationOptionsFlow:
        """Get the options flow for this handler."""
        return BedrockConversationOptionsFlow(config_entry)


class BedrockConversationOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for AWS Bedrock Conversation."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        # Get available LLM APIs
        llm_apis = [
            selector.SelectOptionDict(value=api.id, label=api.name)
            for api in llm.async_get_apis(self.hass)
        ]
        
        options_schema = vol.Schema({
            vol.Optional(
                CONF_MODEL_ID,
                default=self.config_entry.options.get(CONF_MODEL_ID, DEFAULT_MODEL_ID)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RECOMMENDED_MODELS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Optional(
                CONF_SELECTED_LANGUAGE,
                default=self.config_entry.options.get(CONF_SELECTED_LANGUAGE, DEFAULT_SELECTED_LANGUAGE)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["en", "de", "fr", "es"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_PROMPT,
                default=self.config_entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
            vol.Optional(
                CONF_MAX_TOKENS,
                default=self.config_entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=100, max=100000, step=100, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_TEMPERATURE,
                default=self.config_entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=1, step=0.05, mode=selector.NumberSelectorMode.SLIDER
                )
            ),
            vol.Optional(
                CONF_TOP_P,
                default=self.config_entry.options.get(CONF_TOP_P, DEFAULT_TOP_P)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=1, step=0.05, mode=selector.NumberSelectorMode.SLIDER
                )
            ),
            vol.Optional(
                CONF_TOP_K,
                default=self.config_entry.options.get(CONF_TOP_K, DEFAULT_TOP_K)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=500, step=10, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_REFRESH_SYSTEM_PROMPT,
                default=self.config_entry.options.get(CONF_REFRESH_SYSTEM_PROMPT, DEFAULT_REFRESH_SYSTEM_PROMPT)
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_REMEMBER_CONVERSATION,
                default=self.config_entry.options.get(CONF_REMEMBER_CONVERSATION, DEFAULT_REMEMBER_CONVERSATION)
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_REMEMBER_NUM_INTERACTIONS,
                default=self.config_entry.options.get(CONF_REMEMBER_NUM_INTERACTIONS, DEFAULT_REMEMBER_NUM_INTERACTIONS)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_MAX_TOOL_CALL_ITERATIONS,
                default=self.config_entry.options.get(CONF_MAX_TOOL_CALL_ITERATIONS, DEFAULT_MAX_TOOL_CALL_ITERATIONS)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(
                CONF_LLM_HASS_API,
                default=self.config_entry.options.get(CONF_LLM_HASS_API, HOME_LLM_API_ID)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=llm_apis,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })
        
        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )
