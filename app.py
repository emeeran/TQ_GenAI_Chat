from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import lru_cache
import requests
import speech_recognition as sr
from pydub import AudioSegment
import io, time, json, os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from persona import PERSONAS

# Initialize Flask app with correct template directory
app = Flask(__name__,
    template_folder=str(Path(__file__).parent / 'templates'),
    static_folder=str(Path(__file__).parent / 'static')
)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['JSON_SORT_KEYS'] = False  # Preserve JSON order
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-size

# Optimization settings
CACHE_TTL = 300  # Cache TTL in seconds
REQUEST_TIMEOUT = 30  # API request timeout
MAX_RETRIES = 3  # Maximum retry attempts

# Initialize paths and configs
load_dotenv()
SAVE_DIR = Path("saved_chats").mkdir(exist_ok=True) or Path("saved_chats")
EXPORT_DIR = Path("exports").mkdir(exist_ok=True) or Path("exports")

# Rate limiting
request_times = {}
RATE_LIMIT = 60  # requests per minute

def rate_limit_check(key: str) -> bool:
    now = time.time()
    request_times[key] = request_times.get(key, [])
    request_times[key] = [t for t in request_times[key] if t > now - 60]
    if len(request_times[key]) >= RATE_LIMIT:
        return False
    request_times[key].append(now)
    return True

@lru_cache(maxsize=100)
def get_cached_response(provider: str, model: str, message: str, persona: str) -> Dict:
    """Cache API responses to improve performance"""
    # Implementation here

# Improved API configurations with validation
API_CONFIGS = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "key": os.getenv("OPENAI_API_KEY"),
        "default": "gpt-4o-mini",
        "fallback": "gpt-3.5-turbo"
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",  # Fixed URL
        "key": os.getenv("GROQ_API_KEY"),
        "default": "deepseek-r1-distill-llama-70b",
        "fallback": "mixtral-8x7b-32768"
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "key": os.getenv("MISTRAL_API_KEY"),
        "default": "codestral-latest",
        "fallback": "mistral-small-latest"
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key": os.getenv("ANTHROPIC_API_KEY"),
        "default": "claude-3-5-sonnet-latest",
        "fallback": "claude-3-sonnet-20240229"
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "key": os.getenv("XAI_API_KEY", "").strip(),
        "default": "grok-2-latest",
        "fallback": "grok-2",
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "key": os.getenv("DEEPSEEK_API_KEY"),
        "default": "deepseek-r1-distill-llama-70b",
        "fallback": "deepseek-chat"
    }
}

# Add complete model configurations
MODEL_CONFIGS = {
    "openai": [
        'gpt-4o', 'chatgpt-4o-latest', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini',
        'o1-preview', 'gpt-4o-realtime-preview', 'gpt-4o-mini-realtime-preview',
        'gpt-4o-audio-preview'
    ],
    "groq": [
        'distil-whisper-large-v3-en', 'gemma2-9b-it', 'llama-3.3-70b-versatile',
        'llama-3.1-8b-instant', 'llama-guard-3-8b', 'llama3-70b-8192', 'llama3-8b-8192',
        'mixtral-8x7b-32768', 'whisper-large-v3', 'whisper-large-v3-turbo',
        'qwen-2.5-coder-32b', 'qwen-2.5-32b', 'deepseek-r1-distill-qwen-32b',
        'deepseek-r1-distill-llama-70b-specdec', 'deepseek-r1-distill-llama-70b',
        'llama-3.3-70b-specdec'
    ],
    "mistral": [
        'codestral-latest', 'mistral-large-latest', 'pixtral-large-latest',
        'mistral-saba-latest', 'ministral-3b-latest', 'ministral-8b-latest',
        'mistral-embed', 'mistral-moderation-latest', 'mistral-small-latest',
        'pixtral-12b-2409', 'open-mistral-nemo', 'open-codestral-mamba', 'mathstral',
        'open-mixtral-8x7b', 'open-mistral-7b', 'open-mixtral-8x22b', 'mistral-small-2402',
        'mistral-large-2402', 'mistral-large-2407'
    ],
    "anthropic": [
        'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229',
        'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-5-sonnet-latest',
        'claude-3-5-haiku-latest'
    ],
    "xai": [
        'grok-2-vision-1212', 'grok-2-vision', 'grok-2-vision-latest', 'grok-2-1212',
        'grok-2', 'grok-2-latest', 'grok-vision-beta', 'grok-beta'
    ],
    "deepseek": [
        'deepseek-chat', 'deepseek-reasoner'
    ]
}

# Update chat endpoint with better error handling
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['message', 'provider', 'model']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Get provider config
        provider = data['provider']
        config = API_CONFIGS.get(provider)
        if not config:
            return jsonify({'error': f'Invalid provider: {provider}'}), 400

        # Check API key
        if not config.get('key'):
            return jsonify({'error': f'No API key configured for {provider}'}), 401

        # Process request
        try:
            response = process_chat_request(data)
            return jsonify(response)
        except requests.RequestException as e:
            app.logger.error(f"API request error: {str(e)}")
            return jsonify({'error': f'API request failed: {str(e)}'}), 502

    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Optimized utility functions
def process_chat_request(data: Dict) -> Dict:
    """Process chat request with optimized error handling"""
    provider = data['provider']
    model = data['model']
    message = data['message']
    persona = data.get('persona', '')

    config = API_CONFIGS[provider]
    endpoint = config['endpoint']
    api_key = config['key']

    # Add more detailed logging
    app.logger.info(f"Making request to {endpoint}")
    app.logger.info(f"Selected model: {model}")
    app.logger.info(f"Provider: {provider}")

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Base payload
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': f'Persona: {persona}'},
            {'role': 'user', 'content': message}
        ]
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        app.logger.info(f"Response status: {response.status_code}")

        response.raise_for_status()
        result = response.json()

        if 'choices' in result and len(result['choices']) > 0:
            return {
                'response': {
                    'text': result['choices'][0]['message']['content'],
                    'metadata': {
                        'provider': provider,
                        'model': model,
                        'response_time': f"{response.elapsed.total_seconds()}s"
                    }
                }
            }
        else:
            raise ValueError('Invalid response structure from API')

    except requests.RequestException as e:
        app.logger.error(f"API request error: {str(e)}")
        app.logger.error(f"Request payload: {json.dumps(payload)}")
        app.logger.error(f"Response status code: {response.status_code if 'response' in locals() else 'N/A'}")
        app.logger.error(f"Response content: {response.content if 'response' in locals() else 'N/A'}")
        raise

def validate_api_key(provider: str, key: str) -> bool:
    """Validate API key format and credentials"""
    # Implementation here

# Add performance monitoring
@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        app.logger.info(f'Request to {request.path} took {duration:.2f}s')
    return response

# Add error handling middleware
@app.errorhandler(400)
def bad_request(error):
    app.logger.error(f"Bad Request: {error}")
    return jsonify({
        'error': 'Bad Request',
        'message': str(error)
    }), 400

# Update the get_models route
@app.route('/get_models/<provider>')
def get_models(provider):
    """Get available models for provider"""
    try:
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400

        if provider not in MODEL_CONFIGS:
            return jsonify({'error': f'Invalid provider: {provider}'}), 400

        config = API_CONFIGS.get(provider, {})
        available_models = MODEL_CONFIGS.get(provider, [])
        default_model = config.get('default')
        fallback_model = config.get('fallback')

        # Sort models alphabetically
        available_models = sorted(available_models)

        # Ensure default and fallback models exist in available models
        if default_model and default_model not in available_models:
            available_models.append(default_model)
        if fallback_model and fallback_model not in available_models:
            available_models.append(fallback_model)

        # Simplify response structure
        return jsonify({
            'models': available_models,
            'default': default_model,
            'fallback': fallback_model,
            'selected': default_model or fallback_model or (available_models[0] if available_models else None)
        })

    except Exception as e:
        app.logger.error(f"Error getting models: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Add transcribe route with proper error handling
@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Handle audio transcription"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']
        if not audio_file:
            return jsonify({'error': 'Empty audio file'}), 400

        # Initialize recognizer
        recognizer = sr.Recognizer()

        try:
            # Convert audio file to WAV
            audio = AudioSegment.from_file(audio_file)
            wav_data = io.BytesIO()
            audio.export(wav_data, format="wav")
            wav_data.seek(0)

            # Transcribe audio
            with sr.AudioFile(wav_data) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                return jsonify({'text': text})

        except sr.UnknownValueError:
            return jsonify({'error': 'Could not understand audio'}), 400
        except sr.RequestError:
            return jsonify({'error': 'Error connecting to speech recognition service'}), 503

    except Exception as e:
        app.logger.error(f"Transcription error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Add favicon route
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/')
def home():
    """Serve the main application page with groq as default provider"""
    try:
        return render_template('index.html', default_provider='groq')
    except Exception as e:
        app.logger.error(f"Error rendering template: {str(e)}")
        return str(e), 500

# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist"""
    dirs = [
        Path(__file__).parent / 'templates',
        Path(__file__).parent / 'static',
        Path(__file__).parent / 'saved_chats',
        Path(__file__).parent / 'exports'
    ]
    for dir_path in dirs:
        dir_path.mkdir(exist_ok=True, parents=True)

# Add new routes for save and export
@app.route('/save_chat', methods=['POST'])
def save_chat():
    try:
        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'No chat history provided'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'chat_{timestamp}.json'
        filepath = SAVE_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'message': 'Chat saved successfully',
            'filename': filename
        })

    except Exception as e:
        app.logger.error(f"Save chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/list_saved_chats')
def list_saved_chats():
    try:
        files = []
        for file in SAVE_DIR.glob('*.json'):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Get first message for preview
                preview = next((msg['content'] for msg in data['history'] if msg['content']), '')
                if isinstance(preview, dict):
                    preview = preview.get('text', '')
                preview = preview[:100]  # Limit preview length

                files.append({
                    'filename': file.name,
                    'timestamp': data.get('timestamp', ''),
                    'preview': preview
                })

        return jsonify(sorted(files, key=lambda x: x['timestamp'], reverse=True))

    except Exception as e:
        app.logger.error(f"List saved chats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/load_chat/<filename>')
def load_chat(filename):
    try:
        filepath = SAVE_DIR / filename
        if not filepath.exists():
            return jsonify({'error': 'File not found'}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return jsonify(data)

    except Exception as e:
        app.logger.error(f"Load chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_chat_topic(messages: list) -> str:
    """Generate a topic from chat history"""
    # Get first user message
    first_message = next((msg['content'] for msg in messages if msg['isUser']), '')
    if isinstance(first_message, dict):
        first_message = first_message.get('text', '')

    # Clean and format the topic
    topic = first_message.strip().lower()
    # Take first few words, max 50 chars
    topic = ' '.join(topic.split()[:5])[:50]
    # Replace special chars with underscores
    topic = ''.join(c if c.isalnum() else '_' for c in topic)
    # Remove multiple underscores
    topic = '_'.join(filter(None, topic.split('_')))
    return topic or 'untitled'

@app.route('/export_chat', methods=['POST'])
def export_chat():
    try:
        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'No chat history provided'}), 400

        # Generate topic-based filename
        topic = generate_chat_topic(data['history'])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{topic}_{timestamp}.md'
        filepath = EXPORT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f'# Chat: {topic}\n\n')
            f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            # ...rest of existing write operations...

        return jsonify({
            'message': 'Chat exported successfully',
            'filename': filename
        })

    except Exception as e:
        app.logger.error(f"Export chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Initialize directories before running
ensure_directories()

if __name__ == '__main__':
    app.run(debug=False, threaded=True)  # Enable threading for better performance