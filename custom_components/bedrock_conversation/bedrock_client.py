### /home/cronus/repos/homeassistant/homeassistant-aws-bedrock-conversation-agent/./custom_components/bedrock_conversation/bedrock_client.py
```python
1: """AWS Bedrock client for conversation agents."""
2: from __future__ import annotations
3: 
4: import json
5: import logging
6: from typing import Any, AsyncGenerator
7: from dataclasses import dataclass
8: 
9: import boto3
10: from botocore.exceptions import ClientError
11: 
12: from homeassistant.components import conversation
13: from homeassistant.components.homeassistant.exposed_entities import async_should_expose
14: from homeassistant.config_entries import ConfigEntry
15: from homeassistant.core import HomeAssistant
16: from homeassistant.exceptions import HomeAssistantError, TemplateError
17: from homeassistant.helpers import entity_registry as er, area_registry as ar, template, llm
18: from homeassistant.util import color
19: 
20: from .const import (
21:     CONF_AWS_REGION,
22:     CONF_AWS_ACCESS_KEY_ID,
23:     CONF_AWS_SECRET_ACCESS_KEY,
24:     CONF_AWS_SESSION_TOKEN,
25:     CONF_MODEL_ID,
26:     CONF_PROMPT,
27:     CONF_SELECTED_LANGUAGE,
28:     CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
29:     CONF_MAX_TOKENS,
30:     CONF_TEMPERATURE,
31:     CONF_TOP_P,
32:     CONF_TOP_K,
33:     DEFAULT_AWS_REGION,
34:     DEFAULT_MODEL_ID,
35:     DEFAULT_SELECTED_LANGUAGE,
36:     DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE,
37:     DEFAULT_MAX_TOKENS,
38:     DEFAULT_TEMPERATURE,
39:     DEFAULT_TOP_P,
40:     DEFAULT_TOP_K,
41:     DEFAULT_PROMPT,
42:     PERSONA_PROMPTS,
43:     CURRENT_DATE_PROMPT,
44:     DEVICES_PROMPT,
45:     SERVICE_TOOL_NAME,
46: )
47: from .utils import closest_color
48: 
49: _LOGGER = logging.getLogger(__name__)
50: 
51: type BedrockConfigEntry = ConfigEntry[BedrockClient]
52: 
53: 
54: @dataclass
55: class DeviceInfo:
56:     """Information about a device for prompt generation."""
57:     entity_id: str
58:     name: str
59:     state: str
60:     area_id: str | None
61:     area_name: str | None
62:     attributes: list[str]
63: 
64: 
65: class BedrockClient:
66:     """Client for AWS Bedrock conversation agents."""
67:     
68:     def __init__(self, hass: HomeAssistant, data: dict[str, Any], options: dict[str, Any]) -> None:
69:         """Initialize the Bedrock client."""
70:         self.hass = hass
71:         self._data = data
72:         self._options = options
73:         
74:         # AWS credentials
75:         aws_region = data.get(CONF_AWS_REGION, DEFAULT_AWS_REGION)
76:         aws_access_key_id = data.get(CONF_AWS_ACCESS_KEY_ID)
77:         aws_secret_access_key = data.get(CONF_AWS_SECRET_ACCESS_KEY)
78:         aws_session_token = data.get(CONF_AWS_SESSION_TOKEN)
79:         
80:         # Initialize boto3 client
81:         session_config = {
82:             'region_name': aws_region,
83:             'aws_access_key_id': aws_access_key_id,
84:             'aws_secret_access_key': aws_secret_access_key,
85:         }
86:         
87:         if aws_session_token:
88:             session_config['aws_session_token'] = aws_session_token
89:         
90:         self._bedrock_runtime = boto3.client('bedrock-runtime', **session_config)
91:         self._region = aws_region
92:         
93:         _LOGGER.info("Initialized Bedrock client for region %s", aws_region)
94:     
95:     def _get_exposed_entities(self) -> list[DeviceInfo]:
96:         """Get all exposed entities with their information."""
97:         entity_registry = er.async_get(self.hass)
98:         area_registry = ar.async_get(self.hass)
99:         
100:         extra_attributes = self._options.get(
101:             CONF_EXTRA_ATTRIBUTES_TO_EXPOSE,
102:             DEFAULT_EXTRA_ATTRIBUTES_TO_EXPOSE
103:         )
104:         
105:         devices = []
106:         
107:         for state in self.hass.states.async_all():
108:             if not async_should_expose(self.hass, "conversation", state.entity_id):
109:                 continue
110:             
111:             entity_entry = entity_registry.async_get(state.entity_id)
112:             area_id = entity_entry.area_id if entity_entry else None
113:             area_name = None
114:             
115:             if area_id:
116:                 area = area_registry.async_get_area(area_id)
117:                 area_name = area.name if area else None
118:             
119:             # Extract relevant attributes
120:             attributes = []
121:             
122:             # Brightness
123:             if state.domain == "light" and "brightness" in extra_attributes:
124:                 brightness = state.attributes.get("brightness")
125:                 if brightness is not None:
126:                     attributes.append(f"{int(brightness * 100 / 255)}%")
127:             
128:             # Color
129:             if state.domain == "light" and "rgb_color" in extra_attributes:
130:                 rgb_color = state.attributes.get("rgb_color")
131:                 if rgb_color:
132:                     color_name = closest_color(tuple(rgb_color))
133:                     attributes.append(color_name)
134:             
135:             # Temperature
136:             if "temperature" in extra_attributes:
137:                 temp = state.attributes.get("temperature")
138:                 if temp is not None:
139:                     attributes.append(f"{temp}°")
140:             
141:             # Humidity
142:             if "humidity" in extra_attributes:
143:                 humidity = state.attributes.get("humidity")
144:                 if humidity is not None:
145:                     attributes.append(f"{humidity}%RH")
146:             
147:             # Fan mode
148:             if "fan_mode" in extra_attributes:
149:                 fan_mode = state.attributes.get("fan_mode")
150:                 if fan_mode:
151:                     attributes.append(f"fan:{fan_mode}")
152:             
153:             # Media title
154:             if "media_title" in extra_attributes:
155:                 media_title = state.attributes.get("media_title")
156:                 if media_title:
157:                     attributes.append(f"playing:{media_title}")
158:             
159:             # Volume level
160:             if "volume_level" in extra_attributes:
161:                 volume = state.attributes.get("volume_level")
162:                 if volume is not None:
163:                     attributes.append(f"vol:{int(volume * 100)}%")
164:             
165:             devices.append(DeviceInfo(
166:                 entity_id=state.entity_id,
167:                 name=state.attributes.get("friendly_name", state.entity_id),
168:                 state=state.state,
169:                 area_id=area_id,
170:                 area_name=area_name,
171:                 attributes=attributes
172:             ))
173:         
174:         return devices
175:     
176:     def _generate_system_prompt(
177:         self,
178:         prompt_template: str,
179:         llm_api: llm.APIInstance | None,
180:         options: dict[str, Any]
181:     ) -> str:
182:         """Generate the system prompt with device information."""
183:         language = options.get(CONF_SELECTED_LANGUAGE, DEFAULT_SELECTED_LANGUAGE)
184:         
185:         # Get persona and date prompts
186:         persona_prompt = PERSONA_PROMPTS.get(language, PERSONA_PROMPTS["en"])
187:         date_prompt = CURRENT_DATE_PROMPT.get(language, CURRENT_DATE_PROMPT["en"])
188:         devices_label = DEVICES_PROMPT.get(language, DEVICES_PROMPT["en"])
189:         
190:         # Get exposed devices
191:         devices = self._get_exposed_entities()
192:         
193:         # Prepare template context
194:         template_context = {
195:             "persona": persona_prompt,
196:             "current_date": date_prompt,
197:             "devices": devices_label,
198:         }
199:         
200:         # Replace placeholders
201:         prompt = prompt_template
202:         prompt = prompt.replace("<persona>", persona_prompt)
203:         prompt = prompt.replace("<current_date>", date_prompt)
204:         prompt = prompt.replace("<devices>", devices_label)
205:         
206:         # Render the Jinja2 template with devices
207:         try:
208:             rendered = template.Template(prompt, self.hass).async_render(
209:                 {"devices": [d.__dict__ for d in devices]},
210:                 parse_result=False
211:             )
212:         except TemplateError as err:
213:             _LOGGER.error("Error rendering prompt template: %s", err)
214:             raise
215:         
216:         return rendered
217:     
218:     def _format_tools_for_bedrock(self, llm_api: llm.APIInstance | None, model_id: str = "") -> list[dict[str, Any]]:
219:         """Format Home Assistant tools for Bedrock tool use."""
220:         if not llm_api or not llm_api.tools:
221:             return []
222:         
223:         bedrock_tools = []
224:         
225:         for tool in llm_api.tools:
226:             tool_def = {
227:                 "type": "function",
228:                 "name": tool.name,
229:                 "description": tool.description,
230:                 "input_schema": {
231:                     "type": "object",
232:                     "properties": {},
233:                     "required": []
234:                 }
235:             }
236:             
237:             # Convert voluptuous schema to JSON schema
238:             if hasattr(tool, 'parameters') and tool.parameters:
239:                 # For HassCallService tool
240:                 if tool.name == SERVICE_TOOL_NAME:
241:                     tool_def["input_schema"] = {
242:                         "type": "object",
243:                         "properties": {
244:                             "service": {
245:                                 "type": "string",
246:                                 "description": "The service to call (e.g., 'light.turn_on')"
247:                             },
248:                             "target_device": {
249:                                 "type": "string",
250:                                 "description": "The entity_id of the device to control"
251:                             },
252:                             "brightness": {
253:                                 "type": "number",
254:                                 "description": "Brightness level (0-255)"
255:                             },
256:                             "rgb_color": {
257:                                 "type": "string",
258:                                 "description": "RGB color as comma-separated values (e.g., '255,0,0')"
259:                             },
260:                             "temperature": {
261:                                 "type": "number",
262:                                 "description": "Temperature setting"
263:                             },
264:                             "humidity": {
265:                                 "type": "number",
266:                                 "description": "Humidity setting"
267:                             },
268:                             "fan_mode": {
269:                                 "type": "string",
270:                                 "description": "Fan mode setting"
271:                             },
272:                             "hvac_mode": {
273:                                 "type": "string",
274:                                 "description": "HVAC mode setting"
275:                             },
276:                             "preset_mode": {
277:                                 "type": "string",
278:                                 "description": "Preset mode"
279:                             },
280:                             "item": {
281:                                 "type": "string",
282:                                 "description": "Item to add to a list"
283:                             },
284:                             "duration": {
285:                                 "type": "string",
286:                                 "description": "Duration for the action"
287:                             }
288:                         },
289:                         "required": ["service", "target_device"]
290:                     }
291:             
292:             bedrock_tools.append(tool_def)
293:         
294:         return bedrock_tools
295:     
296:     def _build_bedrock_messages(
297:         self,
298:         conversation_content: list[conversation.Content]
299:     ) -> list[dict[str, Any]]:
300:         """Convert Home Assistant conversation to Bedrock message format."""
301:         messages = []
302:         
303:         for content in conversation_content:
304:             if isinstance(content, conversation.SystemContent):
305:                 # System prompt is handled separately in Bedrock
306:                 continue
307:             
308:             elif isinstance(content, conversation.UserContent):
309:                 messages.append({
310:                     "role": "user",
311:                     "content": [{"text": content.content}]
312:                 })
313:             
314:             elif isinstance(content, conversation.AssistantContent):
315:                 message_content = []
316:                 
317:                 if content.content:
318:                     message_content.append({"text": content.content})
319:                 
320:                 if content.tool_calls:
321:                     for tool_call in content.tool_calls:
322:                         message_content.append({
323:                             "toolUse": {
324:                                 "toolUseId": f"tool_{id(tool_call)}",
325:                                 "name": tool_call.name if hasattr(tool_call, 'name') else tool_call.function,
326:                                 "input": tool_call.tool_args
327:                             }
328:                         })
329:                 
330:                 if message_content:
331:                     messages.append({
332:                         "role": "assistant",
333:                         "content": message_content
334:                     })
335:             
336:             elif isinstance(content, conversation.ToolResultContent):
337:                 # Tool results go in user messages in Bedrock
338:                 if messages and messages[-1]["role"] == "user":
339:                     # Append to last user message
340:                     messages[-1]["content"].append({
341:                         "toolResult": {
342:                             "toolUseId": content.tool_call_id,
343:                             "content": [{"json": content.result}]
344:                         }
345:                     })
346:                 else:
347:                     # Create new user message
348:                     messages.append({
349:                         "role": "user",
350:                         "content": [{
351:                             "toolResult": {
352:                                 "toolUseId": content.tool_call_id,
353:                                 "content": [{"json": content.result}]
354:                             }
355:                         }]
356:                     })
357:         
358:         return messages
359:     
360:     async def async_generate(
361:         self,
362:         conversation_content: list[conversation.Content],
363:         llm_api: llm.APIInstance | None,
364:         agent_id: str,
365:         options: dict[str, Any]
366:     ) -> dict[str, Any]:
367:         """Generate a response from Bedrock."""
368:         model_id = options.get(CONF_MODEL_ID, DEFAULT_MODEL_ID)
369:         max_tokens = options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
370:         temperature = options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
371:         top_p = options.get(CONF_TOP_P, DEFAULT_TOP_P)
372:         top_k = options.get(CONF_TOP_K, DEFAULT_TOP_K)
373:         
374:         # Extract system prompt
375:         system_prompt = None
376:         for content in conversation_content:
377:             if isinstance(content, conversation.SystemContent):
378:                 system_prompt = content.content
379:                 break
380:         
381:         # Build messages
382:         messages = self._build_bedrock_messages(conversation_content)
383:         
384:         # Build request - Update to use snake_case for keys
385:         request_body = {
386:             "anthropic_version": "bedrock-2023-05-31",
387:             "max_tokens": max_tokens,
388:             "temperature": temperature,
389:             "top_p": top_p,
390:             "messages": messages
391:         }
392:         
393:         if system_prompt:
394:             request_body["system"] = system_prompt
395:         
396:         # Add tools if available
397:         tools = self._format_tools_for_bedrock(llm_api, model_id)
398:         if tools:
399:             request_body["tools"] = tools
400:         
401:         # Only add top_k for Claude models
402:         if "anthropic.claude" in model_id:
403:             request_body["top_k"] = top_k
404:         
405:         try:
406:             _LOGGER.debug("Calling Bedrock model %s", model_id)
407:             _LOGGER.debug("Request body: %s", json.dumps(request_body))
408:             # invoke_model requires keyword arguments
409:             response = await self.hass.async_add_executor_job(
410:                 lambda: self._bedrock_runtime.invoke_model(
411:                     modelId=model_id,
412:                     body=json.dumps(request_body)
413:                 )
414:             )
415:             
416:             response_body = json.loads(response['body'].read())
417:             _LOGGER.debug("Received response from Bedrock: %s", response_body)
418:             
419:             return response_body
420:             
421:         except ClientError as err:
422:             _LOGGER.error("AWS Bedrock error: %s", err)
423:             raise HomeAssistantError(f"Bedrock API error: {err}") from err
424:         except Exception as err:
425:             _LOGGER.exception("Unexpected error calling Bedrock")
426:             raise HomeAssistantError(f"Unexpected error: {err}") from err
```
