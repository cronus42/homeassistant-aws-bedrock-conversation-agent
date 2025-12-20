# AWS Bedrock Conversation Agent for Home Assistant

This add-on enables you to use Amazon Bedrock's powerful language models as conversation agents in Home Assistant. Connect your Home Assistant to models like Claude, Llama, and others available through AWS Bedrock.

## Features

- 🤖 Access to multiple LLM models via Amazon Bedrock
- 🔐 Secure credential management
- ⚙️ Configurable model parameters (temperature, max tokens)
- 🏠 Full integration with Home Assistant conversation system

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the "AWS Bedrock Conversation Agent" add-on
3. Configure your AWS credentials and preferences
4. Start the add-on

## Configuration

### Required Settings

- **aws_region**: AWS region where Bedrock is available (e.g., `us-east-1`, `us-west-2`)
- **model_id**: The Bedrock model ID to use (e.g., `anthropic.claude-3-5-sonnet-20241022-v2:0`)
- **aws_access_key_id**: Your AWS access key ID
- **aws_secret_access_key**: Your AWS secret access key

### Optional Settings

- **temperature**: Controls randomness (0-1, default: 0.7)
- **max_tokens**: Maximum tokens in response (100-100000, default: 2048)
- **aws_session_token**: Optional session token for temporary credentials

### Example Configuration

```yaml
aws_region: "us-east-1"
model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
aws_access_key_id: "AKIAIOSFODNN7EXAMPLE"
aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
temperature: 0.7
max_tokens: 2048
```

## Available Models

Common Bedrock model IDs:
- **Claude 3.5 Sonnet**: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Claude 3 Opus**: `anthropic.claude-3-opus-20240229-v1:0`
- **Claude 3 Haiku**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Llama 3.1**: `meta.llama3-1-405b-instruct-v1:0`
- **Mistral Large**: `mistral.mistral-large-2402-v1:0`

## Setup in Home Assistant

After starting the add-on:

1. Go to **Settings** → **Voice assistants** → **Add Assistant**
2. Choose "AWS Bedrock Conversation Agent" as the conversation agent
3. Configure your assistant with wake words and text-to-speech as desired

## Permissions Required

- Network access to AWS Bedrock endpoints
- Access to Home Assistant configuration

## Support

For issues and feature requests, please visit the GitHub repository.

## License

MIT License
