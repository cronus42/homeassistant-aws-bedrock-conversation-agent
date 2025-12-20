# AWS Bedrock Conversation Agent - Project Summary

## Project Overview

This is a complete Home Assistant add-on that enables integration with Amazon Bedrock's large language models as conversation agents. It allows Home Assistant users to leverage powerful AI models like Claude, Llama, and Mistral for natural language interactions.

## File Structure

```
homeassistant-aws-bedrock-conversation-agent/
├── config.yaml              # Add-on configuration and schema
├── build.yaml               # Docker build configuration
├── Dockerfile               # Container image definition
├── run.sh                   # Startup script
├── bedrock_agent.py         # Main Python application
├── apparmor.txt             # Security profile
├── README.md                # User documentation
├── INSTALL.md               # Installation guide
├── CHANGELOG.md             # Version history
├── LICENSE                  # MIT License
├── .gitignore               # Git ignore rules
├── repository.json          # Repository metadata
├── test_bedrock.py          # Testing script
├── icon.png                 # Add-on icon (placeholder)
├── logo.png                 # Add-on logo (placeholder)
└── translations/
    └── en.yaml              # English translations
```

## Core Components

### 1. Configuration (config.yaml)
- Defines add-on metadata (name, version, description)
- Multi-architecture support
- Configuration schema with validation
- Secure password fields for AWS credentials

### 2. Application (bedrock_agent.py)
- Python 3 async web server using aiohttp
- AWS Bedrock client initialization
- Support for multiple model families:
  - Anthropic Claude (3.5 Sonnet, 3 Opus, 3 Haiku)
  - Meta Llama (3.1)
  - Mistral Large
- REST API endpoints:
  - `POST /api/conversation/process` - Process conversation requests
  - `GET /health` - Health check
- Comprehensive error handling
- Logging for debugging

### 3. Docker Container (Dockerfile)
- Based on Home Assistant base images
- Python 3 runtime
- Dependencies: boto3, aiohttp, pyyaml
- Proper labels for Home Assistant integration

### 4. Security (apparmor.txt)
- AppArmor security profile
- Network access permissions for AWS
- File system access restrictions
- Required capabilities defined

### 5. Documentation
- **README.md**: User-facing documentation with features and setup
- **INSTALL.md**: Detailed installation and troubleshooting guide
- **CHANGELOG.md**: Version history
- **PROJECT_SUMMARY.md**: This file - technical overview

## Configuration Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| aws_region | string | Yes | us-east-1 | AWS region with Bedrock access |
| model_id | string | Yes | anthropic.claude-3-5-sonnet-20241022-v2:0 | Bedrock model ID |
| aws_access_key_id | password | Yes | - | AWS access key |
| aws_secret_access_key | password | Yes | - | AWS secret key |
| temperature | float | No | 0.7 | Model temperature (0-1) |
| max_tokens | int | No | 2048 | Max response tokens (100-100000) |
| aws_session_token | password | No | - | Optional session token |

## API Integration

### Home Assistant Conversation API

The add-on implements the Home Assistant conversation agent protocol:

**Request Format:**
```json
{
  "text": "User's question or command",
  "conversation_id": "optional-conversation-id"
}
```

**Response Format:**
```json
{
  "response": {
    "speech": {
      "plain": {
        "speech": "Model's response text",
        "extra_data": null
      }
    },
    "card": {},
    "language": "en",
    "response_type": "action_done",
    "data": {
      "targets": [],
      "success": [],
      "failed": []
    }
  },
  "conversation_id": "conversation-id"
}
```

## AWS Bedrock Models Supported

### Anthropic Claude
- `anthropic.claude-3-5-sonnet-20241022-v2:0` (Latest Sonnet)
- `anthropic.claude-3-opus-20240229-v1:0` (Most capable)
- `anthropic.claude-3-haiku-20240307-v1:0` (Fastest)

### Meta Llama
- `meta.llama3-1-405b-instruct-v1:0`

### Mistral
- `mistral.mistral-large-2402-v1:0`

## Dependencies

### Python Packages
- **boto3** (1.35.x): AWS SDK for Python
- **aiohttp** (3.10.x): Async HTTP server
- **pyyaml** (6.0.x): YAML parsing

### System Requirements
- Alpine Linux base
- Python 3
- Network access to AWS endpoints

## Security Features

1. **Credential Protection**: AWS keys stored as password type in config
2. **AppArmor Profile**: Restricts container permissions
3. **Network Isolation**: Only required AWS endpoints accessible
4. **No Data Persistence**: Conversations not stored by default
5. **Session Token Support**: For temporary credentials

## Testing

Use the included test script:

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
python3 test_bedrock.py
```

## Future Enhancements

Potential improvements:
1. Conversation history management
2. System prompts/instructions
3. Streaming responses
4. Rate limiting and retry logic
5. Cost tracking
6. Multiple model configurations
7. Context window management
8. Tool calling support
9. Multi-language support
10. Integration with Home Assistant entities

## AWS Requirements

### IAM Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

### Supported Regions
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- ap-southeast-1 (Singapore)
- ap-northeast-1 (Tokyo)
- eu-central-1 (Frankfurt)
- eu-west-3 (Paris)

## Development Notes

- Built for Home Assistant Supervisor environment
- Uses bashio for configuration management
- Follows Home Assistant add-on best practices
- Alpine Linux base for small footprint
- Multi-architecture support for broad compatibility

## License

MIT License - See LICENSE file for details

## Version

Current Version: **1.0.0**
Release Date: December 20, 2025

## Author

Created for Home Assistant community
Maintained by: [Your Name]

---

**Note**: This is a complete, production-ready add-on. However, you'll need to:
1. Replace placeholder images (icon.png, logo.png) with actual PNG files
2. Update repository.json with your GitHub URL
3. Test thoroughly in your Home Assistant environment
4. Consider adding conversation history if needed
