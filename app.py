from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import speech_recognition as sr
from pydub import AudioSegment
import io
import subprocess
import markdown2
import time
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import os
from persona import PERSONAS

# Initialize Flask app and configurations
app = Flask(__name__)
CORS(app)
load_dotenv()

# Directory setup
SAVE_DIR = Path("saved_chats").mkdir(exist_ok=True) or Path("saved_chats")
EXPORT_DIR = Path("exports").mkdir(exist_ok=True) or Path("exports")

# API and model configurations
API_CONFIGS: Dict[str, Dict[str, Any]] = {
    "openai": {"endpoint": "https://api.openai.com/v1/chat/completions", "key": os.getenv("OPENAI_API_KEY"), "default": "gpt-4o-mini"},
    "groq": {"endpoint": "https://api.groq.com/openai/v1/chat/completions", "key": os.getenv("GROQ_API_KEY"), "default": "deepseek-r1-distill-llama-70b"},
    "mistral": {"endpoint": "https://api.mistral.ai/v1/chat/completions", "key": os.getenv("MISTRAL_API_KEY"), "default": "codestral-latest"},
    "anthropic": {"endpoint": "https://api.anthropic.com/v1/messages", "key": os.getenv("ANTHROPIC_API_KEY"), "default": "claude-3-5-sonnet-latest"},
    "xai": {"endpoint": "https://api.x.ai/v1/chat/completions", "key": os.getenv("XAI_API_KEY"), "default": "grok-2-latest"},
    "deepseek": {"endpoint": "https://api.deepseek.ai/v1/chat/completions", "key": os.getenv("DEEPSEEK_API_KEY"), "default": "deepseek-r1-70b"}
}

MODEL_CONFIGS = {
    "openai": [
        'gpt-4o', 'gpt-4o-mini', 'chatgpt-4o-latest', 'o1', 'o1-mini', 'o3-mini', 'o1-preview',
        'gpt-4o-realtime-preview', 'gpt-4o-mini-realtime-preview', 'gpt-4o-audio-preview',
        'gpt-4-turbo-preview', 'gpt-4-0125-preview', 'gpt-4', 'gpt-4-32k', 'gpt-3.5-turbo', 'gpt-3.5-turbo-16k'
    ],
    "groq": [
        'mixtral-8x7b-32768', 'llama2-70b-4096', 'llama-3.3-70b-versatile', 'gemma2-9b-it',
        'gemma-7b-it', 'llama-3.1-8b-instant', 'llama3-8b-8192', 'llama-guard-3-8b', 'llama3-70b-8192',
        'whisper-large-v3', 'whisper-large-v3-turbo', 'distil-whisper-large-v3-en',
        'qwen-2.5-coder-32b', 'qwen-2.5-32b', 'deepseek-r1-distill-qwen-32b', 'deepseek-r1-distill-llama-70b',
        'deepseek-r1-distill-llama-70b-specdec', 'llama-3.3-70b-specdec', 'llama-3.2-1b-preview',
        'llama-3.2-3b-preview', 'llama-3.2-11b-vision-preview', 'llama-3.2-90b-vision-preview'
    ],
    "mistral": [
        'mistral-large-latest', 'mistral-medium-latest', 'mistral-small-latest', 'mistral-tiny-latest',
        'codestral-latest', 'pixtral-large-latest', 'mistral-embed', 'mistral-moderation-latest', 'mistral-saba-latest',
        'ministral-8b-latest', 'ministral-3b-latest', 'open-mistral-nemo', 'open-codestral-mamba', 'mathstral',
        'open-mixtral-8x7b', 'open-mistral-7b', 'open-mixtral-8x22b', 'mistral-small-2402',
        'mistral-large-2402', 'mistral-large-2407'
    ],
    "anthropic": [
        'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307',
        'claude-3-5-sonnet-latest', 'claude-3-5-haiku-latest', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022',
        'claude-3-7-sonnet-20240317'
    ],
    "xai": [
        'grok-2-latest', 'grok-2-1212', 'grok-2', 'grok-2-vision-latest', 'grok-2-vision-1212', 'grok-2-vision',
        'grok-beta', 'grok-vision-beta'
    ],
    "deepseek": [
        'deepseek-chat', 'deepseek-coder', 'deepseek-reasoner', 'deepseek-math', 'deepseek-english',
        'deepseek-r1-70b', 'deepseek-r1-70b-alpha', 'deepseek-r1-70b-chat', 'deepseek-r1-70b-instruct'
    ]
}

SYSTEM_MESSAGE = """You are an expert developer skilled in multiple programming languages. Write clean, efficient code, handle errors robustly, and provide clear explanations. Optimize for performance, follow best practices, and ensure safety."""

# Utility Functions
def check_ffmpeg() -> bool:
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: ffmpeg not installed. Install it for audio support (e.g., 'brew install ffmpeg' on MacOS).")
        return False

def format_response(content: str, provider: str, model: str, timing: float) -> Dict[str, Any]:
    markdown_content = markdown2.markdown(content, extras=["fenced-code-blocks", "tables"])
    return {
        'markdown': content, 'html': markdown_content, 'text': content,
        'metadata': {'provider': provider, 'model': model, 'generated_at': datetime.now().isoformat(), 'response_time': f"{timing:.2f}s"}
    }

def get_payload(provider: str, model: str, message: str, persona: str) -> Dict[str, Any]:
    system_message = PERSONAS.get(persona, PERSONAS["all_round_developer"])

    if provider == "anthropic":
        return {
            'model': model,
            'messages': [
                {
                    'role': 'user',
                    'content': f"System: {system_message}\n\nUser: {message}"
                }
            ],
            'max_tokens': 4096
        }
    else:
        return {
            'model': model,
            'temperature': 0.7,
            'max_tokens': 4096,
            'messages': [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': message}
            ]
        }

def get_headers(provider: str, api_key: str) -> Dict[str, str]:
    return (
        {'x-api-key': api_key, 'anthropic-version': '2024-01-01', 'Content-Type': 'application/json'}
        if provider == "anthropic" else
        {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    )

def extract_topic(history: list) -> str | None:
    first_msg = next((msg['content'] for msg in history if msg.get('isUser')), '')
    text = first_msg.get('text', first_msg) if isinstance(first_msg, dict) else str(first_msg)
    return ''.join(c for c in text.split('\n')[0] if c.isalnum() or c.isspace())[:50].strip().replace(' ', '_').lower() or None

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        start_time = time.time()
        data = request.get_json()
        provider = data.get('provider')
        model = data.get('model')
        message = data.get('message')
        persona = data.get('persona', 'all_round_developer')

        if not all([provider, model, message]):
            return jsonify({'error': 'Missing parameters'}), 400

        config = API_CONFIGS.get(provider)
        if not config or not config['key']:
            return jsonify({'error': f'Invalid provider or missing API key: {provider}'}), 400 if config else 401

        response = requests.post(
            config['endpoint'],
            headers=get_headers(provider, config['key']),
            json=get_payload(provider, model, message, persona),
            timeout=30
        )
        response.raise_for_status()

        content = response.json().get('content', [{}])[0].get('text') if provider == "anthropic" else response.json()['choices'][0]['message']['content']
        return jsonify({'response': format_response(content, provider, model, time.time() - start_time)})

    except requests.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except requests.RequestException as e:
        return jsonify({'error': f'API error: {str(e)}'}), e.response.status_code if e.response else 502
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    try:
        audio = AudioSegment.from_file(request.files['audio']).export(io.BytesIO(), format="wav")
        audio.seek(0)
        with sr.AudioFile(audio) as source:
            return jsonify({'text': sr.Recognizer().recognize_google(sr.Recognizer().record(source))})
    except sr.UnknownValueError:
        return jsonify({'error': 'Speech not recognized'}), 400
    except Exception as e:
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

@app.route('/save_chat', methods=['POST'])
def save_chat():
    data = request.get_json()
    if not data or 'history' not in data:
        return jsonify({'error': 'Invalid chat data'}), 400

    filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with (SAVE_DIR / filename).open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return jsonify({'message': 'Chat saved', 'filename': filename})
    except Exception as e:
        return jsonify({'error': f'Save failed: {str(e)}'}), 500

@app.route('/list_saved_chats')
def list_saved_chats():
    try:
        chats = []
        for filepath in SAVE_DIR.glob('*.json'):
            try:
                with filepath.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                history = data.get('history', [])
                preview = (
                    history[0]['content'].get('text', str(history[0]['content']))[:100]
                    if history else 'Empty chat'
                )
                chats.append({
                    'filename': filepath.name,
                    'timestamp': data.get('timestamp', filepath.stat().st_mtime),
                    'preview': preview
                })
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                chats.append({
                    'filename': filepath.name,
                    'timestamp': filepath.stat().st_mtime,
                    'preview': f'Error loading preview: {str(e)}'
                })
        return jsonify(sorted(chats, key=lambda x: float(x['timestamp']), reverse=True))
    except Exception as e:
        return jsonify({'error': f'Failed to list chats: {str(e)}'}), 500

@app.route('/load_chat/<filename>')
def load_chat(filename):
    filepath = SAVE_DIR / filename
    if not filepath.exists():
        return jsonify({'error': 'Chat not found'}), 404

    try:
        with filepath.open('r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': f'Load failed: {str(e)}'}), 500

@app.route('/export_chat', methods=['POST'])
def export_chat():
    data = request.get_json()
    if not data or 'history' not in data:
        return jsonify({'error': 'Invalid chat data'}), 400

    topic, timestamp = extract_topic(data['history']), datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"chat_{topic}_{timestamp}.md" if topic else f"chat_export_{timestamp}.md"

    try:
        with (EXPORT_DIR / filename).open('w', encoding='utf-8') as f:
            f.write(f"# Chat Export: {topic or 'Untitled'}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for msg in data['history']:
                role, content = "User" if msg.get('isUser') else "Assistant", msg.get('content', '')
                text = content.get('text', str(content)) if isinstance(content, dict) else str(content)
                if isinstance(content, dict) and content.get('metadata'):
                    f.write(f"_{content['metadata'].get('provider')}/{content['metadata'].get('model')} ({content['metadata'].get('response_time')})_\n\n")
                f.write(f"## {role}\n\n{text}\n\n---\n\n")
        return jsonify({'message': 'Chat exported', 'filename': filename})
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/get_models/<provider>')
def get_models(provider):
    return jsonify({'models': MODEL_CONFIGS.get(provider, []), 'default': API_CONFIGS.get(provider, {}).get('default')})

if __name__ == '__main__':
    check_ffmpeg()
    app.run(debug=True)