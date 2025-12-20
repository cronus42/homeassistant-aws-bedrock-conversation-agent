# Installation Guide

## Prerequisites

Before installing this add-on, you need:

1. **AWS Account** with access to Amazon Bedrock
2. **AWS Credentials** (Access Key ID and Secret Access Key)
3. **Model Access** enabled in AWS Bedrock console
4. **Home Assistant** instance (Supervisor required for add-ons)

## AWS Setup

### 1. Enable Bedrock Models

1. Log into AWS Console
2. Navigate to Amazon Bedrock
3. Go to "Model access" in the left sidebar
4. Request access to desired models (Claude, Llama, etc.)
5. Wait for approval (usually instant for some models)

### 2. Create IAM User

1. Go to IAM Console
2. Create a new user for Home Assistant
3. Attach policy with these permissions:

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

4. Create access keys and save them securely

## Add-on Installation

### Method 1: Add Repository URL

1. Open Home Assistant
2. Go to **Settings** → **Add-ons** → **Add-on Store**
3. Click the **⋮** menu (top right) → **Repositories**
4. Add this repository URL:
   ```
   https://github.com/yourusername/homeassistant-aws-bedrock-conversation-agent
   ```
5. Find "AWS Bedrock Conversation Agent" in the store
6. Click **Install**

### Method 2: Local Installation (Development)

1. Clone this repository to your Home Assistant addons folder:
   ```bash
   cd /addons
   git clone https://github.com/yourusername/homeassistant-aws-bedrock-conversation-agent
   ```
2. Restart Home Assistant
3. Go to **Settings** → **Add-ons** → **Add-on Store**
4. Refresh the page
5. Find the add-on under "Local add-ons"
6. Click **Install**

## Configuration

1. After installation, go to the add-on's **Configuration** tab
2. Fill in your AWS credentials:
   - **AWS Region**: e.g., `us-east-1`
   - **Model ID**: e.g., `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - **AWS Access Key ID**: Your IAM user's access key
   - **AWS Secret Access Key**: Your IAM user's secret key
3. Optionally adjust:
   - **Temperature**: 0.7 (default)
   - **Max Tokens**: 2048 (default)
4. Click **Save**
5. Go to **Info** tab and click **Start**

## Home Assistant Integration

### 1. Add Conversation Agent

1. Go to **Settings** → **Voice assistants**
2. Click **Add Assistant**
3. Configure:
   - **Name**: AWS Bedrock Assistant
   - **Conversation agent**: AWS Bedrock Conversation Agent
   - **Language**: English (or your preference)
   - Configure STT/TTS as desired
4. Click **Create**

### 2. Test the Assistant

1. Open the Home Assistant interface
2. Click the microphone icon or type a message
3. Select your AWS Bedrock assistant
4. Ask a question or give a command
5. You should receive a response from the Bedrock model

## Troubleshooting

### Add-on Won't Start

- Check the **Log** tab for errors
- Verify AWS credentials are correct
- Ensure the AWS region supports Bedrock
- Check that you have model access enabled

### No Response from Model

- Verify network connectivity
- Check AWS credentials have Bedrock permissions
- Ensure the model ID is correct and available in your region
- Check the add-on logs for API errors

### Permission Errors

- Verify IAM user has `bedrock:InvokeModel` permission
- Check that model access is enabled in Bedrock console
- Try a different region if current one doesn't support Bedrock

### Rate Limiting

- AWS Bedrock has rate limits per model
- Consider using different models or requesting limit increases
- Add retry logic if needed (future enhancement)

## Support Regions

Amazon Bedrock is available in these regions:
- us-east-1 (N. Virginia)
- us-west-2 (Oregon)
- ap-southeast-1 (Singapore)
- ap-northeast-1 (Tokyo)
- eu-central-1 (Frankfurt)
- eu-west-3 (Paris)

Check AWS documentation for the most current list.
