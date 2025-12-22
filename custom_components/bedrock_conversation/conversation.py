"""AWS Bedrock conversation implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    HomeAssistantError,
    TemplateError,
)
from homeassistant.helpers import (
    chat_session,
    intent,
    llm,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_LLM_HASS_API,
    CONF_MAX_TOOL_CALL_ITERATIONS,
    CONF_PROMPT,
    CONF_REFRESH_SYSTEM_PROMPT,
    CONF_REMEMBER_CONVERSATION,
    CONF_REMEMBER_NUM_INTERACTIONS,
    DEFAULT_MAX_TOOL_CALL_ITERATIONS,
    DEFAULT_PROMPT,
    DEFAULT_REFRESH_SYSTEM_PROMPT,
    DEFAULT_REMEMBER_CONVERSATION,
    DEFAULT_REMEMBER_NUM_INTERACTIONS,
    DOMAIN,
)
from .bedrock_client import BedrockClient

_LOGGER = logging.getLogger(__name__)


class BedrockConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """Bedrock conversation agent entity."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.history = {}
        self.client: BedrockClient = entry.runtime_data["client"]
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = None
        
        # Check if we should enable device control
        if entry.options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """When entity is being removed from hass."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        options = {**self.entry.data, **self.entry.options}
        
        with (
            chat_session.async_get_chat_session(
                self.hass, user_input.conversation_id
            ) as session,
            conversation.async_get_chat_log(self.hass, session, user_input) as chat_log,
        ):
            raw_prompt = options.get(CONF_PROMPT, DEFAULT_PROMPT)
            refresh_system_prompt = options.get(
                CONF_REFRESH_SYSTEM_PROMPT, DEFAULT_REFRESH_SYSTEM_PROMPT
            )
            remember_conversation = options.get(
                CONF_REMEMBER_CONVERSATION, DEFAULT_REMEMBER_CONVERSATION
            )
            remember_num_interactions = options.get(
                CONF_REMEMBER_NUM_INTERACTIONS, DEFAULT_REMEMBER_NUM_INTERACTIONS
            )
            max_tool_call_iterations = options.get(
                CONF_MAX_TOOL_CALL_ITERATIONS, DEFAULT_MAX_TOOL_CALL_ITERATIONS
            )
            
            # Get LLM API if configured
            llm_api: llm.APIInstance | None = None
            if options.get(CONF_LLM_HASS_API):
                try:
                    llm_api = await llm.async_get_api(
                        self.hass,
                        options[CONF_LLM_HASS_API],
                        llm_context=user_input.as_llm_context(DOMAIN)
                    )
                except HomeAssistantError as err:
                    _LOGGER.error("Error getting LLM API: %s", err)
                    intent_response = intent.IntentResponse(language=user_input.language)
                    intent_response.async_set_error(
                        intent.IntentResponseErrorCode.UNKNOWN,
                        f"Error preparing LLM API: {err}",
                    )
                    return conversation.ConversationResult(
                        response=intent_response,
                        conversation_id=user_input.conversation_id
                    )
            
            # Ensure chat log has the LLM API instance
            chat_log.llm_api = llm_api
            
            # Get message history
            if remember_conversation:
                message_history = chat_log.content[:]
            else:
                message_history = []
            
            # Trim history if needed
            if remember_num_interactions and len(message_history) > (remember_num_interactions * 2) + 1:
                new_message_history = [message_history[0]]  # Keep system prompt
                new_message_history.extend(message_history[1:][-(remember_num_interactions * 2):])
                message_history = new_message_history
            
            # Generate or refresh system prompt
            if len(message_history) == 0 or refresh_system_prompt:
                try:
                    system_prompt_text = await self.client._generate_system_prompt(
                        raw_prompt, llm_api, options
                    )
                    system_prompt = conversation.SystemContent(content=system_prompt_text)
                except TemplateError as err:
                    _LOGGER.error("Error rendering prompt: %s", err)
                    intent_response = intent.IntentResponse(language=user_input.language)
                    intent_response.async_set_error(
                        intent.IntentResponseErrorCode.UNKNOWN,
                        f"Sorry, I had a problem with my template: {err}",
                    )
                    return conversation.ConversationResult(
                        response=intent_response,
                        conversation_id=user_input.conversation_id
                    )
                
                if len(message_history) == 0:
                    message_history.append(system_prompt)
                else:
                    message_history[0] = system_prompt
            
            # Add user message
            message_history.append(conversation.UserContent(content=user_input.text))
            
            # Tool calling loop
            tool_iterations = 0
            agent_id = self.entry.entry_id
            
            while tool_iterations <= max_tool_call_iterations:
                try:
                    # Call Bedrock
                    response = await self.client.async_generate(
                        message_history,
                        llm_api,
                        agent_id,
                        options
                    )
                    
                    # Parse response
                    stop_reason = response.get("stopReason")
                    content_blocks = response.get("content", [])
                    
                    _LOGGER.debug(
                        "Bedrock response - stop_reason: %s, content_blocks: %d",
                        stop_reason, len(content_blocks)
                    )
                    
                    # Extract text and tool uses
                    response_text = ""
                    tool_calls = []
                    tool_use_ids = {}  # Map tool_call to Bedrock's tool_use_id
                    
                    for block in content_blocks:
                        if "text" in block:
                            response_text += block["text"]
                        elif "toolUse" in block:
                            tool_use = block["toolUse"]
                            # Bedrock returns the tool use ID we need to reference later
                            tool_use_id = tool_use.get("toolUseId")
                            
                            tool_input = llm.ToolInput(
                                tool_name=tool_use["name"],
                                tool_args=tool_use.get("input", {})
                            )
                            tool_calls.append(tool_input)
                            
                            # Store the mapping from tool_input to Bedrock's ID
                            if tool_use_id:
                                tool_use_ids[id(tool_input)] = tool_use_id
                                _LOGGER.debug(
                                    "Found tool use '%s' with ID: %s",
                                    tool_use["name"], tool_use_id
                                )
                    
                    # Add assistant response to history
                    if response_text or tool_calls:
                        message_history.append(
                            conversation.AssistantContent(
                                agent_id=agent_id,
                                content=response_text.strip(),
                                tool_calls=tool_calls if tool_calls else None
                            )
                        )
                    
                    # If no tool calls or stop reason is not tool_use, we're done
                    if stop_reason != "tool_use" or not tool_calls:
                        intent_response = intent.IntentResponse(language=user_input.language)
                        intent_response.async_set_speech(response_text.strip())
                        return conversation.ConversationResult(
                            response=intent_response,
                            conversation_id=user_input.conversation_id
                        )
                    
                    # Execute tool calls
                    tool_iteration_results = []
                    for tool_call in tool_calls:
                        try:
                            _LOGGER.debug(
                                "Executing tool: %s with args: %s",
                                tool_call.tool_name, tool_call.tool_args
                            )
                            
                            tool_result = await llm_api.async_call_tool(tool_call)
                            
                            # Use the Bedrock tool_use_id if available, otherwise fallback
                            tool_call_id = tool_use_ids.get(id(tool_call), f"tool_{id(tool_call)}")
                            
                            _LOGGER.debug(
                                "Tool %s completed with result: %s (using ID: %s)",
                                tool_call.tool_name, tool_result, tool_call_id
                            )
                            
                            tool_iteration_results.append(
                                conversation.ToolResultContent(
                                    agent_id=agent_id,
                                    tool_call_id=tool_call_id,
                                    tool_name=tool_call.tool_name,
                                    tool_result=tool_result
                                )
                            )
                        except Exception as err:
                            _LOGGER.error("Error executing tool %s: %s", tool_call.tool_name, err)
                            tool_call_id = tool_use_ids.get(id(tool_call), f"tool_{id(tool_call)}")
                            tool_iteration_results.append(
                                conversation.ToolResultContent(
                                    agent_id=agent_id,
                                    tool_call_id=tool_call_id,
                                    tool_name=tool_call.tool_name,
                                    tool_result={"error": str(err)}
                                )
                            )
                    
                    # Add tool results to history
                    message_history.extend(tool_iteration_results)
                    
                    _LOGGER.debug(
                        "Iteration %d complete, added %d tool results to history",
                        tool_iterations, len(tool_iteration_results)
                    )
                    
                    tool_iterations += 1
                    
                except HomeAssistantError as err:
                    _LOGGER.error("Error calling Bedrock: %s", err)
                    intent_response = intent.IntentResponse(language=user_input.language)
                    intent_response.async_set_error(
                        intent.IntentResponseErrorCode.UNKNOWN,
                        f"Sorry, there was an error: {err}",
                    )
                    return conversation.ConversationResult(
                        response=intent_response,
                        conversation_id=user_input.conversation_id
                    )
            
            # Max iterations reached
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(
                "I'm sorry, I couldn't complete that request after multiple attempts."
            )
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id
            )

    async def async_reload(self, language: str | None = None) -> None:
        """Clear cached intents for a language."""
        pass

    async def async_prepare(self, language: str | None = None) -> None:
        """Load intents for a language."""
        pass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up conversation agent."""
    agent = BedrockConversationEntity(hass, config_entry)
    async_add_entities([agent])
