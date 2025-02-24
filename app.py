from flask import Flask, request, jsonify, render_template, Markup
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
from functools import lru_cache
import markdown2
import html

# Initialize Flask and logging
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Reusable session for connection pooling
session = requests.Session()

# API configuration
API_CONFIG = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "models_endpoint": "https://api.openai.com/v1/models",
        "key": os.getenv("OPENAI_API_KEY"),
        "dynamic_models": True
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY"),
        "models": ['mixtral-8x7b-32768', 'llama2-70b-4096', 'gemma-7b-it']
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "key": os.getenv("MISTRAL_API_KEY"),
        "models": ['mistral-large-latest', 'mistral-medium-latest', 'mistral-small-latest']
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key": os.getenv("ANTHROPIC_API_KEY"),
        "models": ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "key": os.getenv("XAI_API_KEY"),
        "models": ['grok-2-vision-latest', 'grok-2-latest', 'grok-vision-beta']
    }
}

SYSTEM_MESSAGE = "You are an expert developer skilled in multiple programming languages. You are a Knowledgeable Friendly Assistant, designed to provide accurate and helpful responses to user inquiries. Your goal is to assist users in understanding various topics by offering clear, concise, and engaging information. Always maintain a friendly and approachable tone, and be ready to delve into any subject with enthusiasm and expertise. If you don't know an answer, it's okay to say so, and you can offer to look it up or suggest where the user might find the information. Remember, your aim is to make learning enjoyable and informative for everyone you interact with!"

@lru_cache(maxsize=128)
def get_cached_models(provider: str, timestamp: int) -> list:
    """Cache models with TTL"""
    config = API_CONFIG.get(provider, {})
    if not config.get('dynamic_models'):
        return config.get('models', [])

    try:
        response = session.get(
            config['models_endpoint'],
            headers={'Authorization': f'Bearer {config["key"]}'},
            timeout=5
        )
        response.raise_for_status()
        if provider == 'openai':
            return [m['id'] for m in response.json()['data']
                   if any(x in m['id'].lower() for x in ['gpt-4', 'gpt-3.5'])]
    except Exception as e:
        logger.error(f"Model fetch error for {provider}: {e}")
        return config.get('models', [])

def build_headers(provider: str) -> dict:
    """Build request headers"""
    config = API_CONFIG.get(provider, {})
    headers = {'Content-Type': 'application/json'}

    if provider == 'anthropic':
        headers.update({
            'anthropic-version': '2024-01-01',
            'x-api-key': config['key']
        })
    else:
        headers['Authorization'] = f'Bearer {config["key"]}'

    return headers

def build_payload(provider: str, model: str, message: str) -> dict:
    """Build request payload with provider-specific structure"""
    payload = {'model': model}

    if provider == 'anthropic':
        payload.update({
            'system': SYSTEM_MESSAGE,
            'messages': [{'role': 'user', 'content': message}],
            'max_tokens': 4096
        })
    else:
        payload['messages'] = [
            {'role': 'system', 'content': SYSTEM_MESSAGE},
            {'role': 'user', 'content': message}
        ]

    if provider == 'groq':
        payload['temperature'] = 0.7

    return payload

def format_response(content: str) -> str:
    """Format the response with markdown and syntax highlighting"""
    try:
        # Convert markdown to HTML with extras
        html_content = markdown2.markdown(content, extras=[
            "fenced-code-blocks",
            "code-friendly",
            "break-on-newline",
            "tables",
            "smarty-pants"
        ])

        # Escape any remaining HTML except for our converted markdown
        safe_content = html.escape(content)

        return {
            'markdown': content,  # Original markdown
            'html': html_content,  # HTML version
            'text': safe_content   # Plain text version
        }
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return {
            'markdown': content,
            'html': f"<pre>{html.escape(content)}</pre>",
            'text': content
        }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_models/<provider>')
def get_models(provider):
    if provider not in API_CONFIG:
        return jsonify([])

    # Get cached models with 1-hour TTL
    timestamp = int(datetime.now().timestamp() // 3600)
    return jsonify(get_cached_models(provider, timestamp))

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    provider = data.get('provider')
    model = data.get('model')
    message = data.get('message')

    if not all([provider, model, message]):
        return jsonify({'error': 'Missing required parameters'}), 400

    config = API_CONFIG.get(provider)
    if not config or not config.get('key'):
        return jsonify({'error': f'Invalid provider or missing API key'}), 401

    try:
        headers = build_headers(provider)
        payload = build_payload(provider, model, message)

        response = session.post(
            config['endpoint'],
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        json_response = response.json()

        # Extract and format response content
        if provider == 'anthropic':
            content = json_response.get('content', [{}])[0].get('text', '')
        else:
            content = json_response.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Format the response
        formatted_response = format_response(content)
        return jsonify({
            'response': formatted_response
        })

    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(f"{error_msg}. Response: {e.response.text[:200] if e.response else 'No response'}")
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        logger.exception("Unexpected error processing request")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=False)