"""Constants for the AWS Bedrock Conversation integration."""
from typing import Final

DOMAIN: Final = "bedrock_conversation"
HOME_LLM_API_ID: Final = "bedrock-service-api"

# Service tool constants
SERVICE_TOOL_NAME: Final = "HassCallService"
SERVICE_TOOL_ALLOWED_SERVICES: Final = [
    "turn_on", "turn_off", "toggle", "press",
    "increase_speed", "decrease_speed",
    "open_cover", "close_cover", "stop_cover",
    "lock", "unlock", "start", "stop",
    "return_to_base", "pause", "cancel", "add_item",
    "set_temperature", "set_humidity",
    "set_fan_mode", "set_hvac_mode", "set_preset_mode"
]

SERVICE_TOOL_ALLOWED_DOMAINS: Final = [
    "light", "switch", "cover", "lock", "climate",
    "fan", "vacuum", "media_player", "button"
]

ALLOWED_SERVICE_CALL_ARGUMENTS: Final = [
    "brightness", "rgb_color", "temperature",
    "humidity", "fan_mode", "hvac_mode", "preset_mode"
]

SERVICE_TOOL_DESCRIPTION: Final = {
    "name": SERVICE_TOOL_NAME,
    "description": "Use this tool to call Home Assistant services to control devices.",
    "parameters": {
        "service": {"type": "string", "description": "Service name to call", "enum": SERVICE_TOOL_ALLOWED_SERVICES},
        "target_device": {"type": "string", "description": "Entity ID of the target device"},
        "brightness": {"type": "integer", "description": "Brightness level (0-255)"},
        "rgb_color": {"type": "array", "description": "RGB color values [R, G, B]"},
        "temperature": {"type": "number", "description": "Temperature to set"},
        "humidity": {"type": "number", "description": "Humidity level to set"},
        "fan_mode": {"type": "string", "description": "Fan mode to set"},
        "hvac_mode": {"type": "string", "description": "HVAC mode to set"},
        "preset_mode": {"type": "string", "description": "Preset mode to set"}
    },
    "required": ["service", "target_device"]
}

# Configuration constants
CONF_MODEL: Final = "model"
CONF_MODEL_ID: Final = "model"
CONF_PROMPT: Final = "prompt"
CONF_MAX_TOKENS: Final = "max_tokens"
CONF_TEMPERATURE: Final = "temperature"
CONF_TOP_P: Final = "top_p"
CONF_TOP_K: Final = "top_k"
CONF_AWS_REGION: Final = "aws_region"
CONF_AWS_ACCESS_KEY_ID: Final = "aws_access_key_id"
CONF_AWS_SECRET_ACCESS_KEY: Final = "aws_secret_access_key"
CONF_AWS_SESSION_TOKEN: Final = "aws_session_token"
CONF_MAX_TOOL_CALL_ITERATIONS: Final = "max_tool_call_iterations"
CONF_CONVERSATION_HISTORY_SIZE: Final = "conversation_history_size"
CONF_SELECTED_LANGUAGE: Final = "selected_language"
CONF_EXTRA_ATTRIBUTES_TO_EXPOSE: Final = "extra_attributes_to_expose"
CONF_REQUEST_TIMEOUT: Final = "request_timeout"
CONF_REFRESH_SYSTEM_PROMPT: Final = "refresh_system_prompt"
CONF_REMEMBER_CONVERSATION: Final = "remember_conversation"
CONF_REMEMBER_NUM_INTERACTIONS: Final = "remember_num_interactions"

# Defaults
DEFAULT_MODEL: Final = "anthropic.claude-3-5-sonnet-20240620-v1:0"
DEFAULT_MODEL_ID: Final = "anthropic.claude-3-5-sonnet-20240620-v1:0"
DEFAULT_PROMPT: Final = ""
DEFAULT_MAX_TOKENS: Final = 4096
DEFAULT_TEMPERATURE: Final = 1.0
DEFAULT_TOP_P: Final = 0.999
DEFAULT_TOP_K: Final = 250
DEFAULT_AWS_REGION: Final = "us-east-1"
DEFAULT_MAX_TOOL_CALL_ITERATIONS: Final = 5
DEFAULT_CONVERSATION_HISTORY_SIZE: Final = 10
DEFAULT_SELECTED_LANGUAGE: Final = "en"
DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE: Final = []
DEFAULT_REQUEST_TIMEOUT: Final = 30
DEFAULT_REFRESH_SYSTEM_PROMPT: Final = False
DEFAULT_REMEMBER_CONVERSATION: Final = True
DEFAULT_REMEMBER_NUM_INTERACTIONS: Final = 10

PERSONA_PROMPTS = {
    "en": "You are 'Al', a helpful AI Assistant that controls the devices in a house. Complete the following task as instructed with the information provided only.",
    "de": "Du bist 'Al', ein hilfreicher KI-Assistent, der die Geraete in einem Haus steuert. Fuehren Sie die folgende Aufgabe gemaess den Anweisungen durch.",
    "fr": "Vous etes 'Al', un assistant IA utile qui controle les appareils d'une maison. Effectuez la tache suivante comme indique.",
    "es": "Eres 'Al', un util asistente de IA que controla los dispositivos de una casa. Complete la siguiente tarea segun las instrucciones.",
}

CURRENT_DATE_PROMPT = {
    "en": """The current time and date is {{ (as_timestamp(now()) | timestamp_custom("%I:%M %p on %A %B %d, %Y", True, "")) }}""",
    "de": """{% set day_name = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"] %}{% set month_name = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"] %}Die aktuelle Uhrzeit und das aktuelle Datum sind {{ (as_timestamp(now()) | timestamp_custom("%H:%M", local=True)) }} {{ day_name[now().weekday()] }}, {{ now().day }} {{ month_name[now().month -1]}} {{ now().year }}.""",
    "fr": """{% set day_name = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"] %}{% set month_name = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"] %} L'heure et la date actuelles sont {{ (as_timestamp(now()) | timestamp_custom("%H:%M", local=True)) }} {{ day_name[now().weekday()] }}, {{ now().day }} {{ month_name[now().month -1]}} {{ now().year }}.""",
    "es": """{% set day_name = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"] %}{% set month_name = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"] %}La hora y fecha actuales son {{ (as_timestamp(now()) | timestamp_custom("%H:%M", local=True)) }} {{ day_name[now().weekday()] }}, {{ now().day }} de {{ month_name[now().month -1]}} de {{ now().year }}.""",
}

SYSTEM_PROMPT_DEVICE_FORMAT = """{% for area in areas() -%}
  {%- set area_name = area_name(area) -%}
  {%- set area_entities = namespace(items=[]) -%}
  {%- for entity_id in exposed_entities -%}
    {%- if area_id(entity_id) == area -%}
      {%- set domain = entity_id.split('.')[0] -%}
      {%- set state_obj = states[entity_id] -%}
      {%- if state_obj -%}
        {%- set friendly = state_attr(entity_id, 'friendly_name') or entity_id -%}
        {%- set current_state = states(entity_id) -%}
        {%- set entity_info = friendly + ' (' + entity_id + ', state=' + current_state -%}
        {%- if domain == 'light' -%}
          {%- if state_attr(entity_id, 'brightness') -%}
            {%- set entity_info = entity_info + ', brightness=' + (state_attr(entity_id, 'brightness') | string) -%}
          {%- endif -%}
          {%- if state_attr(entity_id, 'rgb_color') -%}
            {%- set rgb = state_attr(entity_id, 'rgb_color') -%}
            {%- set entity_info = entity_info + ', rgb_color=[' + (rgb[0]|string) + ',' + (rgb[1]|string) + ',' + (rgb[2]|string) + ']' -%}
          {%- endif -%}
        {%- elif domain == 'climate' -%}
          {%- if state_attr(entity_id, 'temperature') -%}
            {%- set entity_info = entity_info + ', temperature=' + (state_attr(entity_id, 'temperature') | string) -%}
          {%- endif -%}
          {%- if state_attr(entity_id, 'current_temperature') -%}
            {%- set entity_info = entity_info + ', current_temperature=' + (state_attr(entity_id, 'current_temperature') | string) -%}
          {%- endif -%}
        {%- endif -%}
        {%- set entity_info = entity_info + ')' -%}
        {%- set area_entities.items = area_entities.items + [entity_info] -%}
      {%- endif -%}
    {%- endif -%}
  {%- endfor -%}
  {%- if area_entities.items -%}
{{ area_name }}:
    {%- for item in area_entities.items %}
  - {{ item }}
    {%- endfor %}
  {%- endif -%}
{%- endfor %}"""

DEVICES_PROMPT: Final = SYSTEM_PROMPT_DEVICE_FORMAT

# Available models
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

