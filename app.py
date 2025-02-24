from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
from mistralai import Mistral
import anthropic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
session = requests.Session()  # Reusable HTTP session for connection pooling

# Load environment variables
load_dotenv()

# Update PATH environment variable
additional_path = "/home/em/.local/bin"
os.environ["PATH"] = f"{additional_path}:{os.environ.get('PATH', '')}"

# API configuration
API_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "mistral": "https://api.mistral.ai/api/chat/completions",
    "deepseek": "https://api.deepseek.ai/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "xai": "https://api.x.ai/v1/chat/completions"  # Added X AI endpoint
}

API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "groq": os.getenv("GROQ_API_KEY"),
    "mistral": os.getenv("MISTRAL_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "xai": os.getenv("XAI_API_KEY")  # Updated to match .env file
}

MODEL_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/models",
    "groq": None,
    "mistral": "https://api.mistral.ai/v1/models",
    "anthropic": None,
    "deepseek": None,
    "xai": None  # X AI does not have a model listing endpoint
}

SYSTEM_MESSAGE = "Your system message here..."  # Keep your original message

# Simple cache for model lists
model_cache = {}

@app.route('/')
def home():
    return render_template('index.html')

def build_headers(provider, api_key):
    headers = {'Content-Type': 'application/json'}
    if provider == 'anthropic':
        headers.update({
            'anthropic-version': '2024-01-01',
            'x-api-key': api_key
        })
    elif provider in ['groq', 'mistral']:
        headers['Authorization'] = f'Bearer {api_key}'
    elif provider == 'xai':
        headers['Authorization'] = f'Bearer {api_key}'
    else:
        headers['Authorization'] = f'Bearer {api_key}'
    return headers

def build_payload(provider, model, user_message):
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_MESSAGE},
            {'role': 'user', 'content': user_message}
        ]
    }
    if provider == 'groq':
        payload['temperature'] = 0.7
    return payload

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    provider = data.get('provider')
    model = data.get('model')
    user_message = data.get('message')

    if not all([provider, model, user_message]):
        return jsonify({'error': 'Missing required parameters'}), 400

    if provider not in API_ENDPOINTS:
        return jsonify({'error': 'Invalid provider'}), 400

    api_key = API_KEYS.get(provider)
    if not api_key:
        return jsonify({'error': f'{provider} API key not configured'}), 401

    try:
        if provider == 'mistral':
            client = Mistral(api_key=api_key)
            chat_response = client.chat.complete(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ]
            )
            ai_response = chat_response.choices[0].message.content
        elif provider == 'anthropic':
            client = anthropic.Anthropic()
            message = client.messages.create(
                model=model,
                max_tokens=1000,
                temperature=0,
                system="You are a world-class poet. Respond only with short poems.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            )
            ai_response = message.content[0].text
        elif provider == 'xai':
            headers = build_headers(provider, api_key)
            payload = build_payload(provider, model, user_message)
            logger.info(f"Request to {provider} with payload: {payload}")
            response = session.post(
                API_ENDPOINTS[provider],
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            ai_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        else:
            headers = build_headers(provider, api_key)
            payload = build_payload(provider, model, user_message)
            logger.info(f"Request to {provider} with payload: {payload}")
            response = session.post(
                API_ENDPOINTS[provider],
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            if provider == 'anthropic':
                ai_response = response.json().get('content', [{}])[0].get('text', '')
            else:
                ai_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')

        logger.info(f"Response from {provider}: {ai_response}")
        return jsonify({'response': ai_response})

    except requests.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        if response := getattr(e, 'response', None):
            error_msg += f"\nStatus: {response.status_code}\nResponse: {response.text[:200]}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500

def get_cached_models(provider):
    cache_entry = model_cache.get(provider)
    if cache_entry and datetime.now() < cache_entry['expires']:
        return cache_entry['data']
    return None

@app.route('/get_models/<provider>')
def get_models(provider):
    if provider not in MODEL_ENDPOINTS:
        return jsonify([])

    # Return cached models if available
    if cached := get_cached_models(provider):
        return jsonify(cached)

    # Handle providers with static model lists
    static_models = {
        'groq': [
            'distil-whisper-large-v3-en',
            'gemma2-9b-it',
            'llama-3.3-70b-versatile',
            'llama-3.1-8b-instant',
            'llama-guard-3-8b',
            'llama3-70b-8192',
            'llama3-8b-8192',
            'mixtral-8x7b-32768',
            'whisper-large-v3',
            'whisper-large-v3-turbo'
        ],
        'anthropic': [
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022',
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307'
        ],
        'mistral': [
            'codestral-latest',
            'mistral-large-latest',
            'pixtral-large-latest',
            'mistral-moderation-latest',
            'ministral-3b-latest',
            'ministral-8b-latest',
            'open-mistral-nemo',
            'mistral-small-latest',
            'mistral-saba-latest'
        ],
        'deepseek': [
            'deepseek-chat',
            'deepseek-reasoner'
        ],
        'xai': [
            'grok-2-vision-latest',
            'grok-2-latest',
            'grok-vision-beta',
            'grok-beta'
        ]
    }

    if provider in static_models:
        model_cache[provider] = {
            'data': static_models[provider],
            'expires': datetime.now() + timedelta(hours=24)
        }
        return jsonify(static_models[provider])

    # Dynamic model fetching for OpenAI/Mistral
    api_key = API_KEYS.get(provider)
    if not api_key:
        return jsonify({'error': 'API key not configured'}), 401

    try:
        response = session.get(
            MODEL_ENDPOINTS[provider],
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=5
        )
        response.raise_for_status()

        if provider == 'openai':
            models = [m['id'] for m in response.json()['data']
                     if any(x in m['id'].lower() for x in ['gpt-4', 'gpt-3.5'])]
            models = sorted(models)
        elif provider == 'mistral':
            models = [m['id'] for m in response.json()['data']]

        # Cache results for 24 hours
        model_cache[provider] = {
            'data': models,
            'expires': datetime.now() + timedelta(hours=24)
        }
        return jsonify(models)

    except requests.RequestException as e:
        logger.error(f"Model fetch error: {str(e)}")
        # Fallback to recent known models
        fallback_models = {
            'openai': [
                'gpt-4-turbo-preview',
                'gpt-4-0125-preview',
                'gpt-4',
                'gpt-3.5-turbo-0125',
                'gpt-3.5-turbo'
            ],
            'mistral': static_models['mistral']
        }
        return jsonify(fallback_models.get(provider, []))

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')