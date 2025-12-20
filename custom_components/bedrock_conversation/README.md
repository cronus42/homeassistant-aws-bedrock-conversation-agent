# AWS Bedrock Conversation for Home Assistant

A custom component that enables AWS Bedrock models (Claude, Llama, Mistral) as conversation agents in Home Assistant with full device control capabilities.

## Features

✅ **Native Tool Calling** - Control Home Assistant devices using Claude 3.5's tool calling  
✅ **Multi-Model Support** - Claude 3.5 Sonnet/Opus/Haiku, Llama 3.1, Mistral Large  
✅ **Rich System Prompts** - Auto-generated with device states, areas, and attributes  
✅ **Conversation Memory** - Remembers previous turns in conversations  
✅ **Multi-Language** - English, German, French, Spanish support  
✅ **Device Exposure Control** - Only exposes entities you explicitly allow  
✅ **Full Configuration UI** - No YAML editing required  

## Architecture

This is a **custom component** (not an add-on) that integrates directly with Home Assistant's conversation system. It provides feature parity with [home-llm](https://github.com/acon96/home-llm) but uses AWS Bedrock as the backend.

## Installation

### Method 1: HACS (Recommended)
1. Open HACS
2. Go to "Integrations"
3. Click the three dots in the top right
4. Select "Custom repositories"
5. Add this repository URL
6. Install "AWS Bedrock Conversation"
7. Restart Home Assistant

### Method 2: Manual
1. Copy `custom_components/bedrock_conversation` to your `config/custom_components/` directory
2. Restart Home Assistant

## Setup

### 1. AWS Prerequisites

#### Enable Bedrock Models
1. Log into AWS Console
2. Go to Amazon Bedrock
3. Click "Model access" in the left sidebar
4. Request access to desired models (Claude, Llama, etc.)
5. Wait for approval (usually instant)

#### Create IAM User
Create an IAM user with this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

Create access keys and save them securely.

### 2. Home Assistant Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "AWS Bedrock Conversation"
4. Enter your AWS credentials:
   - AWS Region (e.g., `us-east-1`)
   - AWS Access Key ID
   - AWS Secret Access Key
   - (Optional) AWS Session Token
   - Model ID (default: Claude 3.5 Sonnet)
5. Click **Submit**

### 3. Expose Devices

For the assistant to control devices:

1. Go to **Settings** → **Voice assistants** → **Expose**
2. Select entities you want to control
3. Click **Expose** for each entity

### 4. Create Voice Assistant

1. Go to **Settings** → **Voice assistants**
2. Click **Add Assistant**
3. Configure:
   - **Name**: AWS Bedrock Assistant
   - **Conversation agent**: AWS Bedrock Conversation
   - **Language**: Your preference
   - Configure STT/TTS as desired
4. Click **Create**

## Configuration Options

Access options via **Settings** → **Devices & Services** → **AWS Bedrock Conversation** → **Configure**

### Model Parameters
- **Model ID**: Which Bedrock model to use
- **Max Tokens**: Maximum response length (100-100000)
- **Temperature**: Randomness (0-1, default 0.7)
- **Top P**: Nucleus sampling (0-1, default 1.0)
- **Top K**: Token selection limit (1-500, default 250)

### Conversation Settings
- **Language**: en, de, fr, es
- **System Prompt Template**: Jinja2 template for context
- **Refresh Prompt Each Turn**: Update device states every message
- **Remember Conversation**: Keep chat history
- **Number of Interactions to Remember**: History length (1-20)
- **Max Tool Call Iterations**: Tool calling loop limit (0-10)

### Device Control
- **Home Assistant LLM API**: API for tool calling (default: Bedrock Services API)

## Available Models

### Anthropic Claude
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (Latest, best balance) ⭐
- `anthropic.claude-3-5-haiku-20241022-v1:0` (Fast, economical)
- `anthropic.claude-3-opus-20240229-v1:0` (Most capable)
- `anthropic.claude-3-haiku-20240307-v1:0` (Legacy)

### Meta Llama
- `meta.llama3-1-405b-instruct-v1:0`
- `meta.llama3-1-70b-instruct-v1:0`

### Mistral
- `mistral.mistral-large-2402-v1:0`

## How It Works

### System Prompt Generation

The component automatically generates rich system prompts:

```
You are 'Al', a helpful AI Assistant that controls the devices in a house.
The current time and date is 02:30 PM on Friday December 20, 2024

Devices:
## Area: Living Room
light.living_room_lamp 'Living Room Lamp' = on;80%;warm_white
fan.living_room_fan 'Living Room Fan' = off

## Area: Kitchen
light.kitchen 'Kitchen Light' = on;100%
climate.kitchen 'Kitchen Thermostat' = heat;72°

## Area: Bedroom
light.bedroom 'Bedroom Light' = off
```

### Tool Calling Flow

1. User: "Turn on the living room lights"
2. Claude generates tool call:
   ```json
   {
     "name": "HassCallService",
     "input": {
       "service": "light.turn_on",
       "target_device": "light.living_room_lamp"
     }
   }
   ```
3. Component executes the service
4. Returns result to Claude
5. Claude responds: "I've turned on the living room lights"

### Supported Services

- **Light**: turn_on, turn_off, toggle (with brightness, color)
- **Switch**: turn_on, turn_off, toggle
- **Fan**: turn_on, turn_off, increase_speed, decrease_speed
- **Cover**: open_cover, close_cover, stop_cover
- **Lock**: lock, unlock
- **Climate**: set_temperature, set_humidity, set_fan_mode, set_hvac_mode, set_preset_mode
- **Media Player**: turn_on, turn_off, toggle
- **Vacuum**: start, stop, return_to_base
- **Button**: press
- **Todo**: add_item
- **Timer**: start, cancel, pause
- **Script**: turn_on, turn_off, toggle

## Troubleshooting

### Integration won't load
- Check Home Assistant logs: **Settings** → **System** → **Logs**
- Ensure boto3 is installed: The component will install it automatically
- Restart Home Assistant after installation

### "Invalid credentials" error
- Verify AWS Access Key ID and Secret Access Key
- Check the IAM user has `bedrock:InvokeModel` permission
- Ensure credentials haven't expired

### "Access denied" error
- IAM user needs `bedrock:InvokeModel` permission
- Check that model access is enabled in Bedrock console
- Verify the region supports your chosen model

### Devices not being controlled
- Ensure entities are **exposed** in Settings → Voice assistants → Expose
- Check that the LLM API is set to "Bedrock Services API"
- Verify `max_tool_call_iterations` > 0

### Slow responses
- Use Claude 3.5 Haiku for faster responses
- Reduce `max_tokens` to limit response length
- Set `refresh_prompt_per_turn` to False to skip device state updates

## Cost Considerations

AWS Bedrock pricing varies by model and region. As of December 2024:

### Claude 3.5 Sonnet (Recommended)
- Input: $3 per 1M tokens
- Output: $15 per 1M tokens
- Typical conversation: ~$0.01-0.05

### Claude 3.5 Haiku (Economical)
- Input: $0.80 per 1M tokens
- Output: $4 per 1M tokens
- Typical conversation: ~$0.005-0.01

**Tips to reduce costs:**
- Use Haiku for simple tasks
- Set lower `max_tokens`
- Disable `refresh_prompt_per_turn` if device states don't change often
- Limit conversation history

## Comparison to home-llm

| Feature | AWS Bedrock | home-llm |
|---------|-------------|----------|
| Local execution | ❌ Cloud | ✅ Local |
| Setup complexity | ⭐⭐ Easy | ⭐⭐⭐ Advanced |
| Hardware requirements | None | GPU recommended |
| Model quality | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good |
| Cost | Pay per use | Free |
| Privacy | Data sent to AWS | 100% local |
| Tool calling | Native (Claude) | Trained |
| Streaming | ❌ Not yet | ✅ Yes |
| Multi-language | ✅ Yes | ✅ Yes |

## Advanced Usage

### Custom System Prompts

You can customize the system prompt template using Jinja2:

```jinja
You are a smart home assistant for the Smith family.
Current date: <current_date>

Available devices:
<devices>

The family prefers dimmed lights in the evening.
Always confirm actions before executing.
```

### Using Different LLM APIs

The component supports Home Assistant's LLM API system. You can:
1. Use the built-in "Bedrock Services API" (default)
2. Use Home Assistant's "Assist" API for intent-based control
3. Create custom LLM APIs in other integrations

## Support

- **Issues**: https://github.com/yourusername/homeassistant-aws-bedrock-conversation-agent/issues
- **Discussions**: https://github.com/yourusername/homeassistant-aws-bedrock-conversation-agent/discussions
- **Home Assistant Community**: Tag @yourusername

## License

MIT License - See LICENSE file

## Credits

- Inspired by [home-llm](https://github.com/acon96/home-llm) by @acon96
- Uses AWS Bedrock APIs
- Built for the Home Assistant community
