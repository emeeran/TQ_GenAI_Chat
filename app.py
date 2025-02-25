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
import anthropic
import json
from pathlib import Path
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

# Initialize Flask and logging
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Reusable session for connection pooling
session = requests.Session()

# Configure retry strategy
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=2,  # exponential backoff
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "POST"]
)

# Update session with retry strategy
session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

# API configuration
API_CONFIG = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "models_endpoint": "https://api.openai.com/v1/models",
        "key": os.getenv("OPENAI_API_KEY"),
        "default_model": "gpt-4o-mini",
        "dynamic_models": True,
        "models": [
            'gpt-4-turbo-preview',
            'gpt-4-0125-preview',
            'gpt-4-1106-preview',
            'gpt-4-vision-preview',
            'gpt-4',
            'gpt-4-32k',
            'gpt-3.5-turbo',
            'gpt-3.5-turbo-16k',
            'gpt-3.5-turbo-instruct'
        ]
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY"),
        "default_model": "deepseek-r1-distill-llama-70b",
        "models": [
            # Large Models
            'mixtral-8x7b-32768',
            'llama2-70b-4096',
            'llama-3.3-70b-versatile',
            # Medium Models
            'gemma-7b-it',
            'llama-3.1-8b-instant',
            'llama3-8b-8192',
            # Specialized Models
            'llama-guard-3-8b',
            'llama3-70b-8192',
            # Audio Models
            'whisper-large-v3',
            'whisper-large-v3-turbo',
            'distil-whisper-large-v3-en',
            # DeepSeek Models
            'deepseek-r1-distill-qwen-32b',
            'deepseek-r1-distill-llama-70b',
            'deepseek-r1-distill-llama-70b-specdec',
            # Preview/Beta Models
            'qwen-2.5-coder-32b',
            'qwen-2.5-32b',
            'llama-3.3-70b-specdec',
            'llama-3.2-1b-preview',
            'llama-3.2-3b-preview',
            'llama-3.2-11b-vision-preview',
            'llama-3.2-90b-vision-preview'
        ]
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "key": os.getenv("MISTRAL_API_KEY"),
        "default_model": "codestral-latest",
        "models": [
            # Latest Models
            'mistral-large-latest',
            'mistral-medium-latest',
            'mistral-small-latest',
            'mistral-tiny-latest',
            # Specialized Models
            'codestral-latest',
            'pixtral-large-latest',
            'mistral-embed',
            'mistral-moderation-latest',
            'mistral-saba-latest',
            # Edge Models
            'ministral-8b-latest',
            'ministral-3b-latest',
            # Research Models
            'open-mistral-nemo',
            'open-codestral-mamba',
            # Dated Versions
            'mistral-large-2402',
            'mistral-large-2407',
            'mistral-medium-2312',
            'mistral-small-2402',
            'codestral-2405',
            # Legacy Models
            'open-mixtral-8x7b',
            'open-mistral-7b',
            'open-mixtral-8x22b'
        ]
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key": os.getenv("ANTHROPIC_API_KEY"),
        "default_model": "claude-3.5-hiaku-20241022",
        "models": [
            # Claude 3 Models
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307',
            # Claude 3.5/3.7 Models
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022',
            'claude-3-7-sonnet-20240317',
            # Legacy Models
            'claude-2-1',
            'claude-2-0',
            'claude-instant-1-2',
            # AWS/GCP Variants
            'claude-3-sonnet@20240229',
            'claude-3-haiku@20240307'
        ]
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "key": os.getenv("XAI_API_KEY"),
        "models": [
            # Latest Models
            'grok-2-vision-latest',
            'grok-2-latest',
            'grok-vision-beta',
            'grok-beta',
            # Dated Versions
            'grok-2-vision-1212',
            'grok-2-1212'
        ]
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.ai/v1/chat/completions",
        "key": os.getenv("DEEPSEEK_API_KEY"),
        "models": [
            'deepseek-chat',
            'deepseek-coder',
            'deepseek-reasoner',
            'deepseek-math',
            'deepseek-english'
        ]
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
    if provider == 'anthropic':
        return {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': message
                        }
                    ]
                }
            ],
            'system': SYSTEM_MESSAGE,
            'max_tokens': 4096
        }
    else:
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': SYSTEM_MESSAGE},
                {'role': 'user', 'content': message}
            ]
        }
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

# Update TIMEOUT_CONFIG
TIMEOUT_CONFIG = {
    'default': 15,
    'xai': {
        'connect': 10,
        'read': 60,  # Increased read timeout for X AI
        'retries': 3
    },
    'anthropic': {
        'connect': 5,
        'read': 30,
        'retries': 2
    },
    'groq': {
        'connect': 5,
        'read': 30,
        'retries': 2
    }
}

def get_provider_timeout(provider: str) -> tuple:
    """Get provider-specific timeout settings"""
    config = TIMEOUT_CONFIG.get(provider, {})
    if isinstance(config, dict):
        return (config.get('connect', 5), config.get('read', TIMEOUT_CONFIG['default']))
    return (5, config)

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
    start_time = time.time()
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
        if provider == 'anthropic':
            client = anthropic.Anthropic(api_key=config['key'])
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": message}
                ],
                system=SYSTEM_MESSAGE
            )
            content = response.content[0].text
        else:
            headers = build_headers(provider)
            payload = build_payload(provider, model, message)
            connect_timeout, read_timeout = get_provider_timeout(provider)

            try:
                response = session.post(
                    config['endpoint'],
                    headers=headers,
                    json=payload,
                    timeout=(connect_timeout, read_timeout)
                )
                response.raise_for_status()
                json_response = response.json()
                content = json_response.get('choices', [{}])[0].get('message', {}).get('content', '')

            except requests.Timeout as e:
                logger.error(f"Timeout error for {provider}: {str(e)}")
                return jsonify({
                    'error': f'Request to {provider} timed out after {read_timeout}s. The service might be experiencing high load.'
                }), 504

            except requests.RequestException as e:
                logger.error(f"Request error for {provider}: {str(e)}")
                error_details = str(e.response.text) if hasattr(e, 'response') else str(e)
                return jsonify({
                    'error': f'Error communicating with {provider}: {error_details}'
                }), 502

        # Calculate execution time
        execution_time = round(time.time() - start_time, 2)

        # Add metadata to the response
        metadata = f"\n\n---\n*Generated by {provider}/{model} in {execution_time}s*"
        content = content + metadata if content else metadata

        # Format the response
        formatted_response = format_response(content)
        return jsonify({
            'response': formatted_response,
            'metadata': {
                'provider': provider,
                'model': model,
                'execution_time': execution_time
            }
        })

    except Exception as e:
        logger.exception(f"Unexpected error with {provider}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

SAVED_CHATS_DIR = Path(__file__).parent / 'saved_chats'
EXPORTS_DIR = Path(__file__).parent / 'exports'

# Ensure directories exist
SAVED_CHATS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

@app.route('/save_chat', methods=['POST'])
def save_chat():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'Invalid chat data'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"chat_{timestamp}.json"
        filepath = SAVED_CHATS_DIR / filename

        # Ensure the directory exists
        SAVED_CHATS_DIR.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Chat saved successfully as {filename}")
        return jsonify({
            'status': 'success',
            'filename': filename,
            'filepath': str(filepath)
        })

    except Exception as e:
        logger.error(f"Error saving chat: {str(e)}")
        return jsonify({'error': f'Failed to save chat: {str(e)}'}), 500

@app.route('/list_saved_chats')
def list_saved_chats():
    try:
        files = sorted(SAVED_CHATS_DIR.glob('*.json'), reverse=True)
        chats = []
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                chats.append({
                    'filename': file.name,
                    'timestamp': data.get('timestamp', ''),
                    'preview': data['history'][0]['content'][:100] if data['history'] else ''
                })
        return jsonify(chats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/load_chat/<filename>')
def load_chat(filename):
    try:
        with open(SAVED_CHATS_DIR / filename, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def clean_markdown_content(content):
    """Clean and format content as proper markdown"""
    if isinstance(content, dict):
        # If it's a response object with markdown, use that
        if 'markdown' in content:
            content = content['markdown']
        elif 'text' in content:
            content = content['text']
        else:
            content = str(content)

    # Remove HTML artifacts and convert to proper markdown
    content = content.replace('&quot;', '"').replace('&apos;', "'")
    content = content.replace('&lt;', '<').replace('&gt;', '>')
    content = content.replace('&amp;', '&')

    # Remove HTML tags while preserving markdown
    content = content.replace('<h3>', '### ').replace('</h3>', '\n')
    content = content.replace('<h2>', '## ').replace('</h2>', '\n')
    content = content.replace('<h1>', '# ').replace('</h1>', '\n')
    content = content.replace('<strong>', '**').replace('</strong>', '**')
    content = content.replace('<em>', '_').replace('</em>', '_')
    content = content.replace('<ul>', '').replace('</ul>', '')
    content = content.replace('<ol>', '').replace('</ol>', '')
    content = content.replace('<li>', '- ').replace('</li>', '')
    content = content.replace('<p>', '').replace('</p>', '\n')
    content = content.replace('<br />', '\n')
    content = content.replace('<code>', '`').replace('</code>', '`')

    # Fix multiple newlines
    content = '\n'.join(line for line in content.splitlines() if line.strip())

    return content

@app.route('/export_chat', methods=['POST'])
def export_chat():
    try:
        data = request.get_json()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Get the first user message as topic
        topic = "chat"
        for msg in data['history']:
            if msg['isUser']:
                topic = msg['content'].strip().lower()
                topic = ''.join(c if c.isalnum() or c.isspace() else '_' for c in topic)
                topic = topic.replace(' ', '_')[:30]
                break

        filename = f"{topic}_{timestamp}.md"

        # Build markdown content
        markdown = [f"# Chat Export: {topic.replace('_', ' ').title()}\n"]

        for msg in data['history']:
            role = "User" if msg['isUser'] else "Assistant"
            content = clean_markdown_content(msg['content'])

            # Add role header and content
            markdown.extend([
                f"\n## {role}\n",
                f"{content}\n",
                "---\n"
            ])

        # Write the file with proper markdown formatting
        with open(EXPORTS_DIR / filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown))

        return jsonify({'status': 'success', 'filename': filename})
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)