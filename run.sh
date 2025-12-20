#!/usr/bin/with-contenv bashio

bashio::log.info "Starting AWS Bedrock Conversation Agent..."

# Read configuration
export AWS_REGION=$(bashio::config 'aws_region')
export AWS_ACCESS_KEY_ID=$(bashio::config 'aws_access_key_id')
export AWS_SECRET_ACCESS_KEY=$(bashio::config 'aws_secret_access_key')
export MODEL_ID=$(bashio::config 'model_id')
export TEMPERATURE=$(bashio::config 'temperature')
export MAX_TOKENS=$(bashio::config 'max_tokens')

# Optional session token
if bashio::config.has_value 'aws_session_token'; then
    export AWS_SESSION_TOKEN=$(bashio::config 'aws_session_token')
fi

bashio::log.info "Region: ${AWS_REGION}"
bashio::log.info "Model: ${MODEL_ID}"

# Start the Python application
exec python3 /bedrock_agent.py
