import asyncio
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache, wraps  # Add this import
from pathlib import Path

import anthropic
import requests
import speech_recognition as sr
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from pydub import AudioSegment
from werkzeug.utils import secure_filename

# Removed unused OpenAI import
from persona import PERSONAS

# Removed unused traceback import
from core.file_processor import FileProcessor, ProcessingError, status_tracker

PROCESSING_STATUS = status_tracker._statuses
PROCESSING_ERRORS = {}
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.file_manager import FileManager
from services.xai_service import XAIService

# Initialize Flask app
app = Flask(__name__,
    template_folder=str(Path(__file__).parent / 'templates'),
    static_folder=str(Path(__file__).parent / 'static')
)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # Increase to 64MB
app.config['UPLOAD_FOLDER'] = str(Path(app.root_path) / 'uploads')
app.config['MAX_FILES'] = 10

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize services with app context
with app.app_context():
    file_manager = FileManager()

# Optimization settings
CACHE_TTL = 300
REQUEST_TIMEOUT = 60  # Increased from 30 to 60 seconds
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 50
MAX_RETRIES = 3

# Configure retry strategy
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

# Create session with retry strategy
def create_request_session():
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Ensure .env is loaded with verbose debugging
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    app.logger.error(f".env file not found at: {env_path.absolute()}")
else:
    app.logger.info(f"Found .env file at: {env_path.absolute()}")
load_dotenv(dotenv_path=env_path, verbose=True)
app.logger.info(f"Loaded env from: {env_path.absolute()}")

# Verify all env vars at startup
for key in ["OPENAI_API_KEY", "GROQ_API_KEY", "XAI_API_KEY"]:
    value = os.getenv(key, "").strip()
    app.logger.info(f"{key} at startup: '{value[:6] if value else 'EMPTY'}...'")

# API configurations
API_CONFIGS = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "key": os.getenv("OPENAI_API_KEY", ""),
        "default": "gpt-4o-mini",
        "fallback": "gpt-3.5-turbo"
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY", ""),
        "default": "deepseek-r1-distill-llama-70b",
        "fallback": "mixtral-8x7b-32768"
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "key": os.getenv("MISTRAL_API_KEY", ""),
        "default": "codestral-latest",
        "fallback": "mistral-small-latest"
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key": os.getenv("ANTHROPIC_API_KEY", ""),
        "default": "claude-3-5-sonnet-latest",
        "fallback": "claude-3-sonnet-20240229"
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "key": os.getenv("XAI_API_KEY", ""),
        "default": "grok-2-latest",
        "fallback": "grok-2"
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "key": os.getenv("DEEPSEEK_API_KEY", ""),
        "default": "deepseek-chat",
        "fallback": "deepseek-chat"
    },
    "gemini": {
        "endpoint": "https://generativelanguage.googleapis.com/v1/models/",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "default": "gemini-1.5-flash",
        "fallback": "gemini-1.5-flash"
    },
    "cohere": {
        "endpoint": "https://api.cohere.com/v1/chat",
        "key": os.getenv("COHERE_API_KEY", ""),
        "default": "command-r",
        "fallback": "command"
    },
    "alibaba": {
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "key": os.getenv("ALIBABA_API_KEY", ""),
        "default": "qwen-2.5-72b-instruct",
        "fallback": "qwen-2.5-32b-instruct"
    },
    "openrouter": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "key": os.getenv("OPENROUTER_API_KEY", ""),
        "default": "moonshot/moonshot-v1-32k",
        "fallback": "moonshot/moonshot-v1-8k"
    },
    "huggingface": {
        "endpoint": "https://api-inference.huggingface.co/models/",
        "key": os.getenv("HF_API_KEY", ""),
        "default": "meta-llama/Llama-2-70b-chat-hf",
        "fallback": "microsoft/DialoGPT-large"
    }
}

# Model configurations
MODEL_CONFIGS = {
    "openai": [
        "gpt-4o",
        "gpt-4.1",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4o-realtime-preview",
        "gpt-4o-audio-preview"
    ],
    "gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite-preview",
        "gemini-2.5-flash-native-audio",
        "gemini-2.5-flash-preview-tts",
        "gemini-2.5-pro-preview-tts",
        "gemini-2.0-flash",
        "gemini-2.0-flash-preview-image-generation",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro"
    ],
    "anthropic": [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768",
        "mistral-saba-24b",
        "qwen/qwen3-32b",
        "moonshotai/kimi-k2-instruct"
    ],
    "mistral": [
        "mistral-large-latest",
        "mistral-saba-24b",
        "codestral-latest",
        "mistral-small-latest",
        "pixtral-large-latest"
    ],
    "xai": [
        "grok-4",
        "grok-4-latest",
        "grok-3",
        "grok-3-mini"
    ],
    "deepseek": [
        "deepseek-r1-distill-llama-70b",
        "deepseek-chat",
        "deepseek-reasoner"
    ],
    "cohere": [
        "command-a-03-2025",
        "command-r7b-12-2024",
        "command-r-plus",
        "command-r",
        "command",
        "command-light"
    ],
    "alibaba": [
        "qwen3-32b",
        "qwen-2.5-72b-instruct",
        "qwen-2.5-32b-instruct",
        "qwen-2.5-14b-instruct",
        "qwen-2.5-7b-instruct",
        "qwen-2.5-coder-32b-instruct",
        "qwen-2.5-math-72b-instruct"
    ],
    "openrouter": [
        "google/gemini-2.5-pro-preview",
        "openai/gpt-4o",
        "moonshotai/kimi-k2-instruct",
        "meta-llama/llama-3.3-70b-versatile",
        "qwen/qwen3-32b"
    ],
    "huggingface": [
        "moonshotai/Kimi-K2-Instruct",
        "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "mistralai/Voxtral-Small-24B-2507",
        "mistralai/Voxtral-Mini-3B-2507",
        "meta-llama/Llama-2-70b-chat-hf"
    ]
}

# Initialize paths
SAVE_DIR = Path(__file__).parent / 'saved_chats'
EXPORT_DIR = Path(__file__).parent / 'exports'

# Ensure directories exist with proper permissions
SAVE_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
EXPORT_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)

# Load cached models and defaults
def load_cached_models():
    """Load cached models on startup"""
    try:
        models_cache_file = Path(__file__).parent / 'models_cache.json'
        defaults_cache_file = Path(__file__).parent / 'defaults_cache.json'
        
        # Load models cache
        if models_cache_file.exists():
            with open(models_cache_file, 'r') as f:
                models_cache = json.load(f)
                
            for provider, data in models_cache.items():
                if provider in MODEL_CONFIGS:
                    MODEL_CONFIGS[provider] = data['models']
                    app.logger.info(f"Loaded {len(data['models'])} cached models for {provider}")
        
        # Load defaults cache
        if defaults_cache_file.exists():
            with open(defaults_cache_file, 'r') as f:
                defaults_cache = json.load(f)
                
            for provider, data in defaults_cache.items():
                if provider in API_CONFIGS:
                    API_CONFIGS[provider]['default'] = data['default_model']
                    app.logger.info(f"Loaded cached default model {data['default_model']} for {provider}")
                    
    except Exception as e:
        app.logger.warning(f"Failed to load cached models/defaults: {str(e)}")

# Initialize cached models and defaults
with app.app_context():
    load_cached_models()

# Rate limiting
request_times = {}
RATE_LIMIT = 60
RATE_LIMIT_WINDOW = 60  # Explicitly define window size

def rate_limit_check(key: str) -> bool:
    """Check rate limit with caching and window-based logic"""
    now = time.time()
    request_times[key] = request_times.get(key, [])
    
    # Filter requests within current window
    request_times[key] = [t for t in request_times[key] if t > now - RATE_LIMIT_WINDOW]
    
    if len(request_times[key]) >= RATE_LIMIT:
        app.logger.warning(f"Rate limit hit for {key}. Current count: {len(request_times[key])}")
        return False
    
    request_times[key].append(now)
    return True

@lru_cache(maxsize=100)
def get_cached_response(provider: str, model: str, message: str, persona: str) -> dict:
    return process_chat_request({"provider": provider, "model": model, "message": message, "persona": persona})

# Add response caching with TTL
CACHE = {}
CACHE_TTL = 300  # 5 minutes
CACHE = {}
CACHE_TTL = 300  # 5 minutes

def cache_response(func):
    """Decorator to cache function responses with TTL"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = f"{args}:{kwargs}"
        now = time.time()


        # Check cache and TTL
        if cache_key in CACHE:
            result, timestamp = CACHE[cache_key]
            if now - timestamp < CACHE_TTL:
                return result

        result = func(*args, **kwargs)
        CACHE[cache_key] = (result, now)

        # Cleanup old cache entries
        for key in list(CACHE.keys()):
            if now - CACHE[key][1] > CACHE_TTL:
                del CACHE[key]

        return result
    return wrapper

# Initialize thread pool
executor = ThreadPoolExecutor(max_workers=4)

def async_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return executor.submit(func, *args, **kwargs).result()
    return wrapper

def initialize_llm_services():
    llm_services = {}

    # Initialize other LLM services
    # ...existing code...

    # Initialize XAI if configured
    try:
        if XAIService.is_configured():
            llm_services['xai'] = XAIService()
    except Exception as e:
        print(f"Warning: Failed to initialize XAI service: {str(e)}")

    return llm_services

llm_services = initialize_llm_services()

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        provider = data.get('provider')
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400

        # For XAI, check if the service is initialized
        if provider == 'xai' and ('xai' not in llm_services):
            return jsonify({'error': 'API key not configured for xai'}), 401

        config = API_CONFIGS.get(provider)
        if not config or not config['key']:
            return jsonify({'error': f'API key not configured for {provider}'}), 401

        response = process_chat_request(data)
        return jsonify(response)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/search_context', methods=['POST'])
def search_context():
    """Search uploaded documents for relevant content"""
    try:
        data = request.get_json()
        query = data.get('message', '')

        if not query:
            return jsonify({'error': 'No query provided'}), 400

        with app.app_context():
            results = file_manager.search_documents(query)

            # Format results for response
            formatted_results = [{
                'filename': r['filename'],
                'excerpt': r['content'][:500] + '...' if len(r['content']) > 500 else r['content'],
                'similarity': r['similarity']
            } for r in results]

            return jsonify({'results': formatted_results})

    except Exception as e:
        app.logger.error(f"Context search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@async_response
def process_gemini_request(model: str, message: str, persona: str) -> dict:
    api_key = API_CONFIGS['gemini']['key']
    if not api_key:
        app.logger.error("Gemini API key not found")
        raise ValueError("Gemini API key not found")

    # Validate model name
    valid_models = MODEL_CONFIGS.get('gemini', [])
    if model not in valid_models:
        app.logger.error(f"Invalid Gemini model: {model}. Valid models: {valid_models}")
        raise ValueError(f"Invalid Gemini model: {model}")

    # Gemini API uses API key as query parameter, not Authorization header
    endpoint = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"{persona}\n{message}"}
                ]
            }
        ]
    }
    try:
        session = create_request_session()
        response = session.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        response.raise_for_status()
        result = response.json()
        app.logger.info(f"Gemini raw response: {json.dumps(result)[:500]}")
        candidates = result.get('candidates', [])
        if candidates and 'content' in candidates[0]:
            parts = candidates[0]['content'].get('parts', [])
            if parts and 'text' in parts[0]:
                text = parts[0]['text']
                if not text:
                    app.logger.error("Gemini response text is empty.")
                    raise ValueError("Empty response from Gemini API")
                return {
                    'response': {
                        'text': text,
                        'metadata': {'provider': 'gemini', 'model': model, 'response_time': f"{response.elapsed.total_seconds()}s"}
                    }
                }
        app.logger.error(f"Invalid Gemini response structure: {json.dumps(result)[:500]}")
        raise ValueError('Invalid response structure from Gemini API')
    except requests.Timeout as e:
        error_msg = f"Request to Gemini timed out after {READ_TIMEOUT}s"
        app.logger.error(error_msg)
        raise ValueError(error_msg) from e
    except requests.RequestException as e:
        error_msg = f"Gemini API request failed: {str(e)}"
        app.logger.error(f"{error_msg}\nEndpoint: {endpoint}")
        raise ValueError(error_msg) from e

def process_chat_request(data: dict) -> dict:
    provider = data['provider']
    model = data['model']
    message = data['message']
    persona = data.get('persona', '')

    # Enhanced context handling
    try:
        with app.app_context():
            context_results = file_manager.search_documents(message, top_n=3)
            if context_results:
                context_texts = []
                for result in context_results:
                    excerpt = result['content'][:800] + '...' if len(result['content']) > 800 else result['content']
                    context_texts.append(f"""### From {result['filename']} (Relevance: {result['similarity']:.2%})
```
{excerpt}
```""")

                if context_texts:
                    message = f"""I have access to {file_manager.total_documents} documents. Here's relevant information I found:

{'\n\n'.join(context_texts)}

User question: {message}

Please synthesize a clear, well-organized answer using this context where relevant. Format your response in Markdown, and cite the source documents when using their information."""

    except Exception as e:
        app.logger.warning(f"Error getting document context: {str(e)}")

    # Add markdown formatting instruction to all providers
    markdown_instruction = "Format your response using proper Markdown. Use headers (###) for sections, code blocks for examples or quotes (```), and proper linking when referencing sources. Use bullet points and numbered lists where appropriate."

    # Handle different providers
    if provider == 'anthropic':
        system_prompt = f"{PERSONAS.get(persona, '')}\n{markdown_instruction}"
        return process_anthropic_request(model, message, system_prompt)
    elif provider == 'xai':
        return process_xai_request(model, message, f"{persona}\n{markdown_instruction}")
    elif provider == 'gemini':
        return process_gemini_request(model, message, persona)

    # Add markdown formatting instruction to system prompt
    config = API_CONFIGS[provider]
    endpoint = config['endpoint']
    api_key = config['key']

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': f"""Persona: {persona}
{markdown_instruction}

When using context from documents, format the references like this:
> Source: [filename] (relevance: XX%)"""},
            {'role': 'user', 'content': message}
        ]
    }

    try:
        session = create_request_session()
        response = session.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        response.raise_for_status()

        result = response.json()
        if 'choices' in result and result['choices']:
            return {
                'response': {
                    'text': result['choices'][0]['message']['content'],
                    'metadata': {'provider': provider, 'model': model, 'response_time': f"{response.elapsed.total_seconds()}s"}
                }
            }

        raise ValueError('Invalid response structure from API')

    except requests.Timeout:
        error_msg = f"Request to {provider} timed out after {READ_TIMEOUT}s"
        app.logger.error(error_msg)
        raise ValueError(error_msg)

    except requests.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        app.logger.error(f"{error_msg}\nEndpoint: {endpoint}")
        raise ValueError(error_msg)

def process_anthropic_request(model: str, message: str, system_prompt: str) -> dict:
    api_key = API_CONFIGS['anthropic']['key']
    if not api_key:
        raise ValueError("Anthropic API key not found")

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
        max_tokens=4096
    )

    response_text = response.content[0].text if response.content else ""
    if not response_text:
        raise ValueError("Empty response from Anthropic API")

    # Ensure response is properly formatted
    if '```' not in response_text and '#' not in response_text:
        response_text = f"""### Response
{response_text}"""

    return {
        'response': {
            'text': response_text,
            'metadata': {'provider': 'anthropic', 'model': model, 'response_time': '1s'}
        }
    }

def process_xai_request(model: str, message: str, persona: str) -> dict:
    # Get the API key from the services dict rather than the config
    if 'xai' not in llm_services:
        app.logger.error("XAI service not initialized")
        raise ValueError("API key not configured for xai")

    xai_service = llm_services['xai']

    try:
        # Use the XAI service to generate a response
        response_data = xai_service.generate_response(
            prompt=message,
            model=model,
            max_tokens=4000
        )

        # Extract text from the response
        response_text = response_data.get('text', '')
        if not response_text:
            raise ValueError("Empty response from X AI API")

        return {
            'response': {
                'text': response_text,
                'metadata': {'provider': 'xai', 'model': model, 'response_time': '1s'}
            }
        }
    except Exception as e:
        app.logger.error(f"X AI request failed: {str(e)}")
        raise ValueError(f"X AI request failed: {str(e)}")

@app.route('/get_models/<provider>')
def get_models(provider):
    if provider not in MODEL_CONFIGS:
        return jsonify({'error': f'Invalid provider: {provider}'}), 400

    config = API_CONFIGS.get(provider, {})
    models = sorted(MODEL_CONFIGS.get(provider, []))
    default = config.get('default')
    if default and default not in models:
        models.append(default)

    return jsonify({
        'models': models,
        'default': default,
        'fallback': config.get('fallback'),
        'selected': default or models[0] if models else None
    })

@app.route('/update_models/<provider>', methods=['POST'])
def update_models(provider):
    """Update model list by fetching from provider's API"""
    if provider not in API_CONFIGS:
        return jsonify({'error': f'Invalid provider: {provider}'}), 400

    try:
        config = API_CONFIGS.get(provider)
        api_key = config.get('key')
        
        if not api_key:
            return jsonify({'error': f'No API key found for {provider}'}), 400

        # Fetch models from provider's API
        session = create_request_session()
        
        if provider == 'openai':
            url = 'https://api.openai.com/v1/models'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                # Filter for chat models only
                models = [
                    model['id'] for model in data.get('data', [])
                    if 'gpt' in model['id'].lower() or 'o1' in model['id'].lower() or 'o3' in model['id'].lower()
                ]
                
        elif provider == 'anthropic':
            url = 'https://api.anthropic.com/v1/models'
            headers = {
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                models = [model['id'] for model in data.get('data', [])]
                
        elif provider == 'groq':
            url = 'https://api.groq.com/openai/v1/models'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                # Filter for text models only (exclude audio models)
                models = [
                    model['id'] for model in data.get('data', [])
                    if model.get('active', True) and 'whisper' not in model['id'].lower()
                ]
                
        else:
            # For other providers, use current model list as fallback
            models = MODEL_CONFIGS.get(provider, [])
        
        if models:
            # Update the model configuration
            MODEL_CONFIGS[provider] = sorted(models)
            
            # Update ai_models.py file dynamically (optional - for persistence)
            update_ai_models_file(provider, models)
            
            return jsonify({
                'success': True,
                'models': sorted(models),
                'message': f'Successfully updated {len(models)} models for {provider}'
            })
        else:
            return jsonify({'error': 'No models found or API error'}), 400
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request timeout while fetching models'}), 408
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request error for {provider}: {str(e)}")
        return jsonify({'error': f'Failed to fetch models: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Update models error for {provider}: {str(e)}")
        return jsonify({'error': f'Failed to update models: {str(e)}'}), 500

@app.route('/set_default_model/<provider>', methods=['POST'])
def set_default_model(provider):
    """Set default model for a provider"""
    if provider not in API_CONFIGS:
        return jsonify({'error': f'Invalid provider: {provider}'}), 400
    
    try:
        data = request.get_json()
        model = data.get('model')
        
        if not model:
            return jsonify({'error': 'No model specified'}), 400
        
        # Verify model exists in the provider's model list
        available_models = MODEL_CONFIGS.get(provider, [])
        if model not in available_models:
            return jsonify({'error': f'Model {model} not available for {provider}'}), 400
        
        # Update the default model
        API_CONFIGS[provider]['default'] = model
        
        # Optionally persist this change to configuration file
        update_default_in_config(provider, model)
        
        return jsonify({
            'success': True,
            'provider': provider,
            'default_model': model,
            'message': f'Default model for {provider} set to {model}'
        })
        
    except Exception as e:
        app.logger.error(f"Set default model error for {provider}: {str(e)}")
        return jsonify({'error': f'Failed to set default model: {str(e)}'}), 500

def update_ai_models_file(provider, models):
    """Update ai_models.py file with new models (optional persistence)"""
    try:
        # Save updated models to a JSON file for persistence
        models_cache_file = Path(__file__).parent / 'models_cache.json'
        
        # Load existing cache or create new one
        if models_cache_file.exists():
            with open(models_cache_file, 'r') as f:
                models_cache = json.load(f)
        else:
            models_cache = {}
        
        # Update cache with new models
        models_cache[provider] = {
            'models': models,
            'last_updated': datetime.now().isoformat()
        }
        
        # Save updated cache
        with open(models_cache_file, 'w') as f:
            json.dump(models_cache, f, indent=2)
            
        app.logger.info(f"Saved {len(models)} models for {provider} to cache")
        
    except Exception as e:
        app.logger.warning(f"Failed to update models cache: {str(e)}")

def update_default_in_config(provider, model):
    """Update default model in configuration (optional persistence)"""
    try:
        # Save default model changes to a JSON file for persistence
        defaults_cache_file = Path(__file__).parent / 'defaults_cache.json'
        
        # Load existing cache or create new one
        if defaults_cache_file.exists():
            with open(defaults_cache_file, 'r') as f:
                defaults_cache = json.load(f)
        else:
            defaults_cache = {}
        
        # Update cache with new default
        defaults_cache[provider] = {
            'default_model': model,
            'last_updated': datetime.now().isoformat()
        }
        
        # Save updated cache
        with open(defaults_cache_file, 'w') as f:
            json.dump(defaults_cache, f, indent=2)
            
        app.logger.info(f"Saved default model {model} for {provider} to cache")
        
    except Exception as e:
        app.logger.warning(f"Failed to update defaults cache: {str(e)}")

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Handle audio transcription with better error handling"""
    if 'audio' not in request.files:
        return jsonify({
            'error': 'No audio file provided',
            'status': 'error'
        }), 400

    try:
        audio_file = request.files['audio']
        if audio_file.filename == '':
            raise ValueError("Empty audio file")

        recognizer = sr.Recognizer()
        audio = AudioSegment.from_file(audio_file)
        wav_data = io.BytesIO()
        audio.export(wav_data, format="wav")
        wav_data.seek(0)

        with sr.AudioFile(wav_data) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return jsonify({
                'text': text,
                'status': 'success'
            })

    except sr.UnknownValueError:
        return jsonify({
            'error': 'Could not understand audio',
            'status': 'error'
        }), 400
    except Exception as e:
        app.logger.error(f"Transcription error: {str(e)}")
        return jsonify({
            'error': f'Transcription failed: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/save_chat', methods=['POST'])
def save_chat():
    """Save chat history with improved error handling and sanitization"""
    try:
        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'No chat history provided'}), 400

        # Sanitize filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_id = ''.join(c for c in str(hash(str(data)))[:8] if c.isalnum())
        filename = f'chat_{timestamp}_{safe_id}.json'

        filepath = SAVE_DIR / filename

        # Save with proper encoding and formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'history': data['history']
            }, f, ensure_ascii=False, indent=2)

        return jsonify({
            'message': 'Chat saved successfully',
            'filename': filename
        })

    except Exception as e:
        app.logger.error(f"Save chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export_chat', methods=['POST'])
def export_chat():
    """Export chat to Markdown with improved formatting"""
    try:
        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'No chat history provided'}), 400

        # Generate filename from chat content
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        topic = generate_chat_topic(data['history'])
        filename = f'{topic}_{timestamp}.md'
        filepath = EXPORT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f'# Chat Export: {topic}\n\n')
            f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            f.write('---\n\n')

            # Write messages with improved formatting
            for msg in data['history']:
                role = "User" if msg.get('isUser') else "Assistant"
                content = msg.get('content', '')

                if isinstance(content, dict):
                    # Handle structured responses
                    text = content.get('text', '')
                    metadata = content.get('metadata', {})

                    f.write(f'## {role}\n\n{text}\n\n')
                    if metadata:
                        f.write('> *Generated by: ' +
                               f"{metadata.get('provider', 'unknown')}/{metadata.get('model', 'unknown')} " +
                               f"in {metadata.get('response_time', 'unknown')}*\n\n")
                else:
                    # Handle plain text messages
                    f.write(f'## {role}\n\n{content}\n\n')

                f.write('---\n\n')

        return jsonify({
            'message': 'Chat exported successfully',
            'filename': filename
        })

    except Exception as e:
        app.logger.error(f"Export chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_chat_topic(messages: list) -> str:
    """Generate a safe, clean topic from chat content"""
    try:
        # Get first user message
        first_message = next((
            msg.get('content', '') for msg in messages
            if msg.get('isUser', False)
        ), 'untitled')

        if isinstance(first_message, dict):
            first_message = first_message.get('text', '')

        # Clean and format topic
        topic = first_message.strip().lower()
        # Take first few words
        topic = ' '.join(topic.split()[:5])[:50]
        # Replace unsafe chars
        topic = ''.join(c if c.isalnum() else '_' for c in topic)
        # Clean up multiple underscores
        topic = '_'.join(filter(None, topic.split('_')))

        return topic or 'untitled'
    except Exception:
        return f'chat_{datetime.now().strftime("%Y%m%d")}'

ALLOWED_EXTENSIONS = {
    'pdf', 'epub', 'docx', 'xlsx',
    'csv', 'md', 'jpg', 'jpeg', 'png'
}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads with improved error handling"""
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        uploaded_files = request.files.getlist('files[]')

        # Check number of files
        if len(uploaded_files) > app.config['MAX_FILES']:
            return jsonify({
                'error': f'Too many files. Maximum {app.config["MAX_FILES"]} files allowed'
            }), 400

        results = []
        temp_dir = Path(app.config['UPLOAD_FOLDER']) / 'temp'
        temp_dir.mkdir(exist_ok=True)

        for file in uploaded_files:
            if not file or not file.filename:
                continue

            try:
                # Clean and validate filename
                filename = secure_filename(file.filename)
                if not filename:
                    continue

                # Validate file type
                if not allowed_file(filename):
                    results.append({
                        'filename': filename,
                        'status': 'error',
                        'error': 'Invalid file type'
                    })
                    continue

                # Check file size
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)

                if size > app.config['MAX_CONTENT_LENGTH']:
                    results.append({
                        'filename': filename,
                        'status': 'error',
                        'error': f'File too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB'
                    })
                    continue

                # Save and process file
                temp_path = temp_dir / filename
                file.save(str(temp_path))

                try:
                    with open(temp_path, 'rb') as f:
                        content = asyncio.run(FileProcessor.process_file(f, filename))

                    # Store in file manager
                    with app.app_context():
                        file_manager.add_document(filename, content)

                    results.append({
                        'filename': filename,
                        'status': 'success',
                        'size': len(content)
                    })

                finally:
                    # Clean up temp file
                    if temp_path.exists():
                        temp_path.unlink()

            except Exception as e:
                app.logger.error(f"Error processing {file.filename}: {str(e)}")
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'error': str(e)
                })

        return jsonify({
            'status': 'success' if any(r['status'] == 'success' for r in results) else 'error',
            'results': results
        })

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/upload/status/<filename>')
def get_processing_status(filename):
    """Get file processing status with better error handling"""
    try:
        status = status_tracker.get(filename)
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'filename': filename
        }), 500

@app.route('/upload/retry/<filename>', methods=['POST'])
def retry_processing(filename):
    """Retry failed file processing"""
    if filename not in PROCESSING_STATUS:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    if not PROCESSING_STATUS[filename].get('recoverable', False):
        return jsonify({
            'status': 'error',
            'message': 'This error is not recoverable'
        }), 400

    try:
        # Clear error state
        PROCESSING_STATUS[filename]['status'] = 'Retrying...'
        if filename in PROCESSING_ERRORS:
            del PROCESSING_ERRORS[filename]

        # Reprocess file
        file = request.files.get('file')
        if not file:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400

        # Use FileProcessor to process the file
        try:
            content = asyncio.run(FileProcessor.process_file(file, filename))
            result = {'status': 'success', 'content': content}
        except ProcessingError as e:
            result = {'status': 'error', 'message': str(e)}

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Retry failed: {str(e)}'
        }), 500

@app.route('/documents/list', methods=['GET'])
def list_documents():
    """Get list of uploaded documents with better error handling"""
    try:
        with app.app_context():
            # Ensure file_manager exists
            if not hasattr(app, 'file_manager'):
                return jsonify({
                    'documents': [],
                    'stats': {'total_documents': 0, 'total_size': 0}
                })

            documents = app.file_manager.list_documents()
            stats = app.file_manager.get_stats()

            # Ensure we always return valid data structure
            return jsonify({
                'documents': documents or [],
                'stats': stats or {'total_documents': 0, 'total_size': 0}
            })
    except Exception as e:
        app.logger.error(f"Error listing documents: {str(e)}")
        return jsonify({
            'error': str(e),
            'documents': [],
            'stats': {'total_documents': 0, 'total_size': 0}
        }), 500

@app.route('/documents/view/<filename>', methods=['GET'])
def view_document(filename):
    """Get contents of a specific document"""
    try:
        with app.app_context():
            doc = file_manager.get_document(filename)
            return jsonify({
                'content': doc['content'],
                'timestamp': doc['timestamp'],
                'preview': (
                    doc['content'][:1000] + '...' if len(doc['content']) > 1000
                    else doc['content']
                )
            })
    except KeyError:
        return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        app.logger.error(f"Error viewing document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html', default_provider='groq')

if __name__ == '__main__':
    app.run(debug=False, threaded=True)
