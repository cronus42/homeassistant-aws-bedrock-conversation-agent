#!/usr/bin/env python3
"""AWS Bedrock Conversation Agent for Home Assistant."""

import os
import json
import logging
from typing import Optional
from aiohttp import web
import boto3
from botocore.exceptions import ClientError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BedrockConversationAgent:
    """Handler for AWS Bedrock conversation requests."""
    
    def __init__(self):
        """Initialize the Bedrock client."""
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.model_id = os.getenv('MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
        self.max_tokens = int(os.getenv('MAX_TOKENS', '2048'))
        
        # Initialize Bedrock client
        session_config = {
            'region_name': self.aws_region,
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        }
        
        # Add session token if provided
        session_token = os.getenv('AWS_SESSION_TOKEN')
        if session_token:
            session_config['aws_session_token'] = session_token
        
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            **session_config
        )
        
        logger.info(f"Initialized Bedrock client for region {self.aws_region}")
        logger.info(f"Using model: {self.model_id}")
    
    def invoke_model(self, prompt: str, conversation_id: Optional[str] = None) -> dict:
        """Invoke the Bedrock model with the given prompt."""
        try:
            # Prepare the request based on model family
            if 'anthropic.claude' in self.model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            elif 'meta.llama' in self.model_id:
                body = {
                    "prompt": prompt,
                    "max_gen_len": self.max_tokens,
                    "temperature": self.temperature,
                }
            elif 'mistral' in self.model_id:
                body = {
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }
            else:
                # Generic format
                body = {
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                }
            
            logger.info(f"Invoking model with prompt: {prompt[:100]}...")
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            logger.debug(f"Raw response: {response_body}")
            
            # Extract response text based on model family
            if 'anthropic.claude' in self.model_id:
                response_text = response_body['content'][0]['text']
            elif 'meta.llama' in self.model_id:
                response_text = response_body['generation']
            elif 'mistral' in self.model_id:
                response_text = response_body['outputs'][0]['text']
            else:
                response_text = str(response_body)
            
            return {
                'response': {
                    'speech': {
                        'plain': {
                            'speech': response_text,
                            'extra_data': None
                        }
                    },
                    'card': {},
                    'language': 'en',
                    'response_type': 'action_done',
                    'data': {
                        'targets': [],
                        'success': [],
                        'failed': []
                    }
                },
                'conversation_id': conversation_id
            }
            
        except ClientError as e:
            error_msg = f"AWS Bedrock error: {str(e)}"
            logger.error(error_msg)
            return {
                'response': {
                    'speech': {
                        'plain': {
                            'speech': f"Sorry, I encountered an error: {error_msg}",
                            'extra_data': None
                        }
                    },
                    'card': {},
                    'language': 'en',
                    'response_type': 'error',
                    'data': {
                        'code': 'bedrock_error'
                    }
                },
                'conversation_id': conversation_id
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'response': {
                    'speech': {
                        'plain': {
                            'speech': f"Sorry, I encountered an unexpected error.",
                            'extra_data': None
                        }
                    },
                    'card': {},
                    'language': 'en',
                    'response_type': 'error',
                    'data': {
                        'code': 'unknown_error'
                    }
                },
                'conversation_id': conversation_id
            }


async def handle_process(request):
    """Handle conversation process requests."""
    try:
        data = await request.json()
        logger.info(f"Received request: {data}")
        
        text = data.get('text', '')
        conversation_id = data.get('conversation_id')
        
        if not text:
            return web.json_response({
                'error': 'No text provided'
            }, status=400)
        
        agent = request.app['agent']
        result = agent.invoke_model(text, conversation_id)
        
        logger.info(f"Sending response: {result['response']['speech']['plain']['speech'][:100]}...")
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return web.json_response({
            'error': str(e)
        }, status=500)


async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({'status': 'healthy'})


def main():
    """Run the web server."""
    app = web.Application()
    
    # Initialize the agent
    agent = BedrockConversationAgent()
    app['agent'] = agent
    
    # Setup routes
    app.router.add_post('/api/conversation/process', handle_process)
    app.router.add_get('/health', handle_health)
    
    # Run the server
    port = int(os.getenv('PORT', '8099'))
    logger.info(f"Starting server on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
