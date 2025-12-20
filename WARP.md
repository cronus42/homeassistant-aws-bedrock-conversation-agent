# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development commands

All commands assume the repo root `/home/cronus/repos/homeassistant/homeassistant-aws-bedrock-conversation-agent`.

### Environment and dependencies

- Create a virtualenv (uses `.venv` by default):
  ```bash
  make venv
  ```
- Install development and test dependencies into the venv:
  ```bash
  make deps
  ```

### Running tests

Preferred test entrypoint (uses the venv and generates coverage):
- Run the full test suite with coverage:
  ```bash
  make test
  ```
  - Runs `pytest tests/` with coverage for `custom_components.bedrock_conversation`.
  - HTML coverage report ends up in `htmlcov/index.html`.

Alternative direct script (installs test deps into the current interpreter, not the venv):
- Run tests via helper script:
  ```bash
  ./run_tests.sh
  ```

Run a focused test with pytest (after `make deps` and activating the venv):
- Single test example:
  ```bash
  . .venv/bin/activate
  pytest tests/test_config_flow.py::test_validate_credentials_success -v
  ```

Manual Bedrock connectivity check (uses real AWS credentials from env vars):
- Smoke test against Bedrock:
  ```bash
  . .venv/bin/activate
  python3 test_bedrock.py
  ```
  - Requires `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_REGION`, `MODEL_ID`.

### Linting, formatting, and type checking

All of these implicitly run `make deps` first.

- Lint (Ruff + flake8):
  ```bash
  make lint
  ```
- Format (black + isort):
  ```bash
  make format
  ```
- Type checking (mypy):
  ```bash
  make typecheck
  ```

### Cleaning and release tagging

- Remove the venv, caches, and build artifacts:
  ```bash
  make clean
  ```

- Show the current integration version and derived git tag (version is read from `custom_components/bedrock_conversation/manifest.json`):
  ```bash
  make version
  ```

- Tag a release from the current `manifest.json` version and push the tag:
  ```bash
  make release
  ```
  - Fails if the working tree is not clean or the tag already exists.

## High-level architecture

This repository is centered around a Home Assistant **custom component** in `custom_components/bedrock_conversation`.

Most of the Home Assistant integration and tool-calling logic lives in this custom component.

### Custom component: `custom_components/bedrock_conversation`

#### Manifest and configuration constants

- `manifest.json`
  - Declares the `bedrock_conversation` domain, integration metadata, version, dependencies, and required Python packages (`boto3`, `webcolors`).
  - `version` is the single source of truth for releases and is used by `make release` to compute the git tag.

- `const.py`
  - Centralizes all configuration keys, defaults, and model lists (`AVAILABLE_MODELS` / `RECOMMENDED_MODELS`).
  - Defines the domain (`DOMAIN`), the Home Assistant LLM API id (`HOME_LLM_API_ID`), and the Hass service tool name and allowed services/domains.
  - Contains Jinja-based templates and helpers for system prompt construction:
    - `PERSONA_PROMPTS` for different languages.
    - `CURRENT_DATE_PROMPT` for localized date/time strings.
    - `SYSTEM_PROMPT_DEVICE_FORMAT` (exported as `DEVICES_PROMPT`) that enumerates exposed entities grouped by area with state and key attributes.

When changing configuration behavior or defaults (e.g., new model IDs, parameters), update `const.py` and, if needed, the manifest.

#### Integration setup and LLM API wiring: `__init__.py`

Key responsibilities:

- `async_setup_entry(hass, entry)`
  - Registers a custom Home Assistant LLM API (`BedrockServicesAPI`) under `HOME_LLM_API_ID` if it is not already present.
  - Stores the config entry in `hass.data[DOMAIN][entry.entry_id]`.
  - Creates a `BedrockClient` and attaches it to `entry.runtime_data` so that other modules (like `conversation.py`) can access the configured client instance.
  - Forwards the config entry setup to the `conversation` platform.
  - Registers `_async_update_listener` to reload the entry when options change.

- `HassServiceTool`
  - Implements `homeassistant.helpers.llm.Tool` and exposes a controlled subset of Home Assistant services to the LLM.
  - Validates the `service` string (`domain.service`) against allowed domains and services (`SERVICE_TOOL_ALLOWED_DOMAINS`, `SERVICE_TOOL_ALLOWED_SERVICES`).
  - Builds `service_data` from `target_device` (mapped to `ATTR_ENTITY_ID`) plus a whitelist of additional arguments (`ALLOWED_SERVICE_CALL_ARGUMENTS`).
  - Performs the actual `hass.services.async_call` and returns a structured `{"result": "success" | "error", ...}` payload.

- `BedrockServicesAPI`
  - Registers an LLM API instance that exposes `HassServiceTool` to the conversation agent.
  - The API’s `async_get_api_instance` creates an `llm.APIInstance` containing a short `api_prompt` and the tool list.

These pieces are the bridge between Bedrock-generated tool calls and actual Home Assistant service executions.

#### Bedrock client and prompt generation: `bedrock_client.py`

`BedrockClient` encapsulates all direct interaction with AWS Bedrock and most of the prompt and tool wiring.

Core pieces:

- Initialization
  - Reads Bedrock configuration and AWS credentials from the config entry data/options (`CONF_AWS_REGION`, keys, optional session token).
  - Builds a `boto3` `bedrock-runtime` client and logs the configured region.

- `DeviceInfo` dataclass and `_get_exposed_entities()`
  - Uses `entity_registry` and `area_registry` to build a list of exposed entities that are eligible for conversation control (`async_should_expose` with the `conversation` context).
  - For each state, collects:
    - Entity id and friendly name.
    - Area id/name (if available).
    - A list of formatted attribute strings based on `CONF_EXTRA_ATTRIBUTES_TO_EXPOSE` (brightness percentage, nearest CSS color name, temperature, humidity, fan mode, media title, volume, etc.).

- `_generate_system_prompt(prompt_template, llm_api, options)`
  - Chooses language-specific persona/date/device labels from `PERSONA_PROMPTS`, `CURRENT_DATE_PROMPT`, and `DEVICES_PROMPT`.
  - Replaces simple placeholders like `<persona>`, `<current_date>`, and `<devices>` inside `prompt_template`.
  - Renders the final Jinja template via `homeassistant.helpers.template.Template`, injecting the serialized `DeviceInfo` list as `devices`.
  - Any template errors are logged and propagated back to the caller (the conversation agent) for user-visible error responses.

- `_format_tools_for_bedrock(llm_api)`
  - Converts Home Assistant `llm.Tool` instances (notably `HassServiceTool`) into the Bedrock "toolSpec" JSON schema format.
  - For `HassServiceTool`, builds a detailed JSON schema for the `service`, `target_device`, and supported arguments.

- `_build_bedrock_messages(conversation)`
  - Converts Home Assistant conversation history (`SystemContent`, `UserContent`, `AssistantContent`, `ToolResultContent`) into the format expected by Bedrock (list of messages with `role` + `content` blocks of `text`, `toolUse`, or `toolResult`).
  - System messages are handled separately and excluded from the Bedrock `messages` list; they are passed via the `system` field of the request body.

- `async_generate(conversation_content, llm_api, agent_id, options)`
  - Extracts the system prompt (if present) from the conversation history.
  - Builds the Anthropic Bedrock request body (`anthropicVersion`, `maxTokens`, `temperature`, `topP`, optional `topK` for Claude models).
  - Attaches `system` and `tools` fields when applicable.
  - Calls `invoke_model` via `hass.async_add_executor_job` on the `bedrock-runtime` client.
  - Returns the parsed JSON response or raises `HomeAssistantError` on failures.

Any changes to Bedrock request/response handling, tool schemas, or prompt structure should go through this module.

#### Conversation agent and tool loop: `conversation.py`

`BedrockConversationAgent` is the Home Assistant `ConversationEntity` that uses `BedrockClient` to fulfill user queries.

Key behavior:

- Entity lifecycle
  - `async_setup_entry` constructs a `BedrockConversationAgent` using the config entry and its `runtime_data` (`BedrockClient`) and registers it with Home Assistant.
  - On add/remove, it calls `conversation.async_set_agent` / `conversation.async_unset_agent` so that Home Assistant routes conversation traffic to this agent.

- `async_process(user_input)` flow
  - Merges `entry.data` and `entry.options` to get the effective configuration, including prompt, memory, and tool-calling settings.
  - Opens a chat session (`chat_session.async_get_chat_session`) and associated chat log (`conversation.async_get_chat_log`).
  - Optionally resolves an LLM API instance via `llm.async_get_api` using the configured `CONF_LLM_HASS_API` (usually the Bedrock services API registered in `__init__.py`).
  - Controls conversation memory:
    - If `CONF_REMEMBER_CONVERSATION` is false, it starts from an empty history each turn.
    - Otherwise, it keeps previous messages, trimming to `CONF_REMEMBER_NUM_INTERACTIONS` to bound history length while preserving the system prompt.

- System prompt handling
  - On first turn or when `CONF_REFRESH_SYSTEM_PROMPT` is true, generates or refreshes the system prompt using `BedrockClient._generate_system_prompt` and ensures it is the first element in the message history.

- Tool-calling loop
  - Appends the current user message to `message_history`.
  - Enters a loop up to `CONF_MAX_TOOL_CALL_ITERATIONS`:
    - Calls `BedrockClient.async_generate` with the full message history and optional `llm_api`.
    - Parses the Bedrock response into plain text plus zero or more tool calls (`llm.ToolInput` instances) based on `content` blocks.
    - Appends an `AssistantContent` entry with the text and tool calls to the history.
    - If there is no `tool_use` stop reason or no tool calls, it returns the answer as an `IntentResponse` and stops.
    - Otherwise, executes each tool via `llm.async_call_tool`, records results as `ToolResultContent`, appends them to the history, and iterates again.
  - If the max iteration count is reached without a final answer, it returns a fallback message to the user.

When modifying tool-calling behavior or how Bedrock responses are turned into Home Assistant responses, use this file together with `bedrock_client.py`.

#### Config flow and options UI: `config_flow.py`

- `validate_aws_credentials(...)`
  - Uses a small `boto3` client to call `bedrock.list_foundation_models` and validates the provided credentials and permissions, mapping specific AWS error codes into Home Assistant form errors.

- `BedrockConversationConfigFlow`
  - Handles the initial integration setup: prompts for AWS region and credentials, optionally a model id, and validates them via `validate_aws_credentials`.
  - Stores core AWS configuration in the config entry `data` and all behavioral settings (prompt, model parameters, memory and tool-calling settings, extra attributes, LLM API id) in `options`.

- `BedrockConversationOptionsFlow`
  - Provides a rich options UI using Home Assistant selectors for model id, language, prompt template, numeric parameters, memory limits, and the choice of LLM API instance.

Use this module when changing how the integration is configured via the Home Assistant UI.

#### Utilities: `utils.py`

- Maintains a precomputed mapping from CSS3 color names to RGB values using `webcolors`.
- `closest_color` returns the nearest CSS3 color name for a given RGB triple and is used by `BedrockClient` when generating human-readable device attributes.
- `format_tool_call_for_bedrock` and `parse_bedrock_tool_use` provide helpers for constructing and interpreting Bedrock tool-use blocks.


### Tests

- Tests live under `tests/` and use `pytest` plus `pytest-homeassistant-custom-component` to exercise integration logic in a Home Assistant-like environment.
  - `test_init.py` validates integration constants and the `HassServiceTool` definition.
  - `test_config_flow.py` tests AWS credential validation behavior and error mapping.
  - `test_utils.py` covers the color matching helper.
  - `test_bedrock_client.py` exercises the `DeviceInfo` dataclass.
- `tests/README.md` documents using `./run_tests.sh`; coverage results are written to `htmlcov/index.html`.
- `test_bedrock.py` is a manual integration test that hits the real Bedrock API using local credentials and prints the response.
