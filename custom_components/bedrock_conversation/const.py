"Constants for the AWS Bedrock Conversation integration."
from typing import Final

DOMAIN: Final = "bedrock_conversation"
HOME_LLM_API_ID: Final = f"{DOMAIN}_services"

# AWS Configuration
CONF_AWS_ACCESS_KEY_ID: Final = "aws_access_key_id"
CONF_AWS_SECRET_ACCESS_KEY: Final = "aws_secret_access_key"
CONF_AWS_SESSION_TOKEN: Final = "aws_session_token"
CONF_AWS_DEFAULT_REGION: Final = "aws_default_region"
CONF_AWS_REGION: Final = "aws_region"

# Agent configuration
CONF_MODEL_ID: Final = "model"
CONF_PROMPT: Final = "prompt"
CONF_TEMPERATURE: Final = "temperature"
CONF_TOP_P: Final = "top_p"
CONF_TOP_K: Final = "top_k"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_REFRESH_SYSTEM_PROMPT: Final = "refresh_prompt_per_turn"
CONF_REMEMBER_CONVERSATION: Final = "remember_conversation"
CONF_REMEMBER_NUM_INTERACTIONS: Final = "remember_num_interactions"
CONF_MAX_TOOL_CALL_ITERATIONS: Final = "max_tool_call_iterations"
CONF_EXTRA_ATTRIBUTES_TO_EXPOSE: Final = "extra_attributes_to_expose"
CONF_LLM_HASS_API: Final = "llm_hass_api"

DEFAULT_MODEL: Final = "anthropic.claude-3-5-sonnet-20240620-v1:0"
DEFAULT_MODEL_ID: Final = "anthropic.claude-3-5-sonnet-20240620-v1:0"
DEFAULT_PROMPT: Final = ""
DEFAULT_MAX_TOKENS: Final = 4096
DEFAULT_TEMPERATURE: Final = 1.0
DEFAULT_TOP_P: Final = 0.999
DEFAULT_TOP_K: Final = 250
DEFAULT_AWS_REGION: Final = "us-east-1"
DEFAULT_REFRESH_SYSTEM_PROMPT: Final = True
DEFAULT_REMEMBER_CONVERSATION: Final = True
DEFAULT_REMEMBER_NUM_INTERACTIONS: Final = 10
DEFAULT_MAX_TOOL_CALL_ITERATIONS: Final = 5
DEFAULT_EXTRA_ATTRIBUTES: Final = [
    "brightness",
    "rgb_color",
    "temperature",
    "current_temperature",
    "target_temperature",
    "humidity",
    "fan_mode",
    "hvac_mode",
    "hvac_action",
    "preset_mode",
    "media_title",
    "media_artist",
    "volume_level",
]

# Service tool configuration
SERVICE_TOOL_NAME: Final = "HassCallService"
SERVICE_TOOL_ALLOWED_DOMAINS: Final = [
    "light",
    "switch",
    "fan",
    "climate",
    "cover",
    "media_player",
    "lock",
    "script",
    "scene",
    "input_boolean",
    "input_number",
    "input_text",
    "input_select",
    "input_datetime",
    "timer",
]
SERVICE_TOOL_ALLOWED_SERVICES: Final = [
    "light.turn_on",
    "light.turn_off",
    "light.toggle",
    "switch.turn_on",
    "switch.turn_off",
    "switch.toggle",
    "fan.turn_on",
    "fan.turn_off",
    "fan.set_percentage",
    "fan.oscillate",
    "fan.set_direction",
    "fan.set_preset_mode",
    "climate.set_temperature",
    "climate.set_humidity",
    "climate.set_fan_mode",
    "climate.set_hvac_mode",
    "climate.set_preset_mode",
    "cover.open_cover",
    "cover.close_cover",
    "cover.stop_cover",
    "cover.set_cover_position",
    "media_player.turn_on",
    "media_player.turn_off",
    "media_player.toggle",
    "media_player.volume_up",
    "media_player.volume_down",
    "media_player.volume_set",
    "media_player.volume_mute",
    "media_player.media_play",
    "media_player.media_pause",
    "media_player.media_stop",
    "media_player.media_next_track",
    "media_player.media_previous_track",
    "media_player.play_media",
    "lock.lock",
    "lock.unlock",
    "script.turn_on",
    "scene.turn_on",
    "input_boolean.turn_on",
    "input_boolean.turn_off",
    "input_boolean.toggle",
    "input_number.set_value",
    "input_text.set_value",
    "input_select.select_option",
    "input_datetime.set_datetime",
    "timer.start",
    "timer.pause",
    "timer.cancel",
    "timer.finish",
]

ALLOWED_SERVICE_CALL_ARGUMENTS: Final = [
    "brightness",
    "rgb_color",
    "temperature",
    "humidity",
    "fan_mode",
    "hvac_mode",
    "preset_mode",
    "item",
    "duration",
    "percentage",
    "oscillating",
    "direction",
    "target_temp_high",
    "target_temp_low",
    "position",
    "volume_level",
    "is_volume_muted",
    "media_content_id",
    "media_content_type",
    "value",
    "option",
    "datetime",
]

AVAILABLE_MODELS: Final = [
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "meta.llama3-70b-instruct-v1:0",
    "meta.llama3-8b-instruct-v1:0",
    "mistral.mistral-7b-instruct-v0:2",
    "mistral.mixtral-8x7b-instruct-v0:1",
]

RECOMMENDED_MODELS: Final = AVAILABLE_MODELS

# Default prompts
PERSONA_PROMPTS = {
    "en": "You are a Home Assistant smart home assistant. You can help the user control their smart home devices and answer questions about Home Assistant.",
}

# Current date prompt
CURRENT_DATE_PROMPT = {
    "en": "The current date is <current_date>.",
}

# Template for devices prompt
DEVICES_PROMPT = {
    "en": "{% if devices %}The user has the following devices:\n\n{% for device in devices %}{% if device.area_name %}[{{ device.area_name }}] {% endif %}{{ device.name }} ({{ device.entity_id }}): {{ device.state }}{% if device.attributes %} ({% for attr in device.attributes %}{{ attr }}{% if not loop.last %}, {% endif %}{% endfor %}){% endif %}\n{% endfor %}{% else %}The user has no exposed devices.{% endif %}",
}

# Attribute constants
ATTR_ENTITY_ID: Final = "entity_id"
