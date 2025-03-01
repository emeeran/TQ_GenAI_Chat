from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import lru_cache, wraps
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
import anthropic
import asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback
from utils.file_processor import FileProcessor, ProcessingError

# Initialize Flask app
app = Flask(__name__,
    template_folder=str(Path(__file__).parent / 'templates'),
    static_folder=str(Path(__file__).parent / 'static')
)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Optimization settings
CACHE_TTL = 300
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

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
        "default": "deepseek-r1-distill-llama-70b",
        "fallback": "deepseek-chat"
    }
}

# Model configurations
MODEL_CONFIGS = {
    "openai": ['gpt-4o', 'chatgpt-4o-latest', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini', 'o1-preview', 'gpt-4o-realtime-preview', 'gpt-4o-mini-realtime-preview', 'gpt-4o-audio-preview'],
    "groq": ['distil-whisper-large-v3-en', 'gemma2-9b-it', 'llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'llama-guard-3-8b', 'llama3-70b-8192', 'llama3-8b-8192', 'mixtral-8x7b-32768', 'whisper-large-v3', 'whisper-large-v3-turbo', 'qwen-2.5-coder-32b', 'qwen-2.5-32b', 'deepseek-r1-distill-qwen-32b', 'deepseek-r1-distill-llama-70b-specdec', 'deepseek-r1-distill-llama-70b', 'llama-3.3-70b-specdec'],
    "mistral": ['codestral-latest', 'mistral-large-latest', 'pixtral-large-latest', 'mistral-saba-latest', 'ministral-3b-latest', 'ministral-8b-latest', 'mistral-embed', 'mistral-moderation-latest', 'mistral-small-latest', 'pixtral-12b-2409', 'open-mistral-nemo', 'open-codestral-mamba', 'mathstral', 'open-mixtral-8x7b', 'open-mistral-7b', 'open-mixtral-8x22b', 'mistral-small-2402', 'mistral-large-2402', 'mistral-large-2407'],
    "anthropic": ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-5-sonnet-latest', 'claude-3-5-haiku-latest'],
    "xai": ['grok-2-vision-1212', 'grok-2-vision', 'grok-2-vision-latest', 'grok-2-1212', 'grok-2', 'grok-2-latest', 'grok-vision-beta', 'grok-beta'],
    "deepseek": ['deepseek-chat', 'deepseek-reasoner']
}

# Initialize paths
SAVE_DIR = Path(__file__).parent / 'saved_chats'
EXPORT_DIR = Path(__file__).parent / 'exports'

# Ensure directories exist with proper permissions
SAVE_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
EXPORT_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)

# Rate limiting
request_times = {}
RATE_LIMIT = 60

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
    return process_chat_request({"provider": provider, "model": model, "message": message, "persona": persona})

# Add response caching with TTL
CACHE = {}
CACHE_TTL = 300  # 5 minutes

def cache_response(func):
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

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        provider = data.get('provider')
        if not provider:
            return jsonify({'error': 'Provider is required'}), 400

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

@cache_response
@async_response
def process_chat_request(data: Dict) -> Dict:
    provider = data['provider']
    model = data['model']
    message = data['message']
    persona = data.get('persona', '')

    if provider == 'anthropic':
        return process_anthropic_request(model, message, persona)
    elif provider == 'xai':
        return process_xai_request(model, message, persona)

    config = API_CONFIGS[provider]
    endpoint = config['endpoint']
    api_key = config['key']

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': f'Persona: {persona}'},
            {'role': 'user', 'content': message}
        ]
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
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
    except requests.RequestException as e:
        app.logger.error(f"API request error: {str(e)}")
        raise ValueError(f"Request failed: {str(e)}")

def process_anthropic_request(model: str, message: str, persona: str) -> Dict:
    api_key = API_CONFIGS['anthropic']['key']
    if not api_key:
        raise ValueError("Anthropic API key not found")

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = PERSONAS.get(persona, '')

    response = client.messages.create(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": message}],
        max_tokens=4096
    )

    response_text = response.content[0].text if response.content else ""
    if not response_text:
        raise ValueError("Empty response from Anthropic API")

    return {
        'response': {
            'text': response_text,
            'metadata': {'provider': 'anthropic', 'model': model, 'response_time': '1s'}
        }
    }

def process_xai_request(model: str, message: str, persona: str) -> Dict:
    xai_key = API_CONFIGS['xai']['key']
    app.logger.info(f"XAI_API_KEY in process_xai_request: '{xai_key[:6] if xai_key else 'EMPTY'}...'")

    if not xai_key:
        raise ValueError("X AI API key not found in configuration")

    if not xai_key.startswith('xai-'):
        app.logger.error(f"X AI key format invalid - missing xai- prefix. Loaded: '{xai_key[:6]}...'")
        raise ValueError("Invalid X AI key format - must start with 'xai-'")

    client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1")

    system_prompt = f"{PERSONAS.get(persona, '')} You are Grok, inspired by Hitchhiker's Guide to the Galaxy."
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        if not response.choices:
            raise ValueError("Empty response from X AI API")

        return {
            'response': {
                'text': response.choices[0].message.content,
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

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_file)
    wav_data = io.BytesIO()
    audio.export(wav_data, format="wav")
    wav_data.seek(0)

    with sr.AudioFile(wav_data) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return jsonify({'text': text})
        except sr.UnknownValueError:
            return jsonify({'error': 'Could not understand audio'}), 400

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

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads with crash recovery"""
    try:
        if 'files[]' not in request.files:
            return jsonify({'status': 'error', 'message': 'No files provided'}), 400

        files = request.files.getlist('files[]')
        results = []

        for file in files:
            try:
                PROCESSING_STATUS[file.filename] = {
                    'progress': 0,
                    'status': 'Starting...',
                    'recoverable': True
                }

                # Process file with error handling
                result = process_file_safely(file)
                results.append(result)

            except Exception as e:
                error_trace = traceback.format_exc()
                PROCESSING_ERRORS[file.filename] = {
                    'error': str(e),
                    'traceback': error_trace,
                    'timestamp': datetime.now().isoformat()
                }

                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'message': f'Processing failed: {str(e)}',
                    'recoverable': True
                })

        return jsonify({
            'status': 'success',
            'results': results,
            'stored_files': list(FILE_STORE.keys())
        })

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_file_safely(file):
    """Process a file with error recovery"""
    try:
        # Get file processor
        ext = file.filename.rsplit('.', 1)[-1].lower()
        processor = FileProcessor.get_processor(ext)

        if not processor:
            return {
                'filename': file.filename,
                'status': 'error',
                'message': 'Unsupported file type'
            }

        # Read file content safely
        file_content = file.read()
        if not file_content:
            raise ProcessingError("Empty file")

        # Process with progress updates
        PROCESSING_STATUS[file.filename]['status'] = 'Processing...'
        content = processor(file_content,
                          progress_callback=lambda p: update_processing_progress(file.filename, p))

        # Store result
        FILE_STORE[file.filename] = {
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

        PROCESSING_STATUS[file.filename].update({
            'progress': 100,
            'status': 'Complete'
        })

        return {
            'filename': file.filename,
            'status': 'success',
            'message': 'File processed successfully'
        }

    except ProcessingError as e:
        # Handle recoverable processing errors
        PROCESSING_STATUS[file.filename].update({
            'progress': 0,
            'status': f'Failed: {str(e)}',
            'recoverable': True
        })
        raise

    except Exception as e:
        # Handle unrecoverable errors
        PROCESSING_STATUS[file.filename].update({
            'progress': 0,
            'status': 'Failed: System Error',
            'recoverable': False
        })
        raise

def update_processing_progress(filename: str, progress: int):
    """Update file processing progress"""
    if filename in PROCESSING_STATUS:
        PROCESSING_STATUS[filename].update({
            'progress': progress,
            'status': 'Processing...' if progress < 100 else 'Complete'
        })

@app.route('/upload/status/<filename>')
def get_processing_status(filename):
    """Get detailed processing status"""
    if filename not in PROCESSING_STATUS:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    status = PROCESSING_STATUS[filename]
    error = PROCESSING_ERRORS.get(filename, None)

    return jsonify({
        'status': status['status'],
        'progress': status['progress'],
        'recoverable': status.get('recoverable', False),
        'error': error['error'] if error else None,
        'timestamp': error['timestamp'] if error else None
    })

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

        result = process_file_safely(file)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Retry failed: {str(e)}'
        }), 500

@app.route('/')
def home():
    return render_template('index.html', default_provider='groq')

if __name__ == '__main__':
    app.run(debug=False, threaded=True)