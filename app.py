# app.py
from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS
import speech_recognition as sr
from pydub import AudioSegment
import io
import subprocess
import markdown2
import time
from datetime import datetime
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()
# Load environment variables from .env file
# API endpoints for different providers

# Add default model configurations
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "groq": "deepseek-r1-distill-llama-70b",
    "mistral": "codestral-latest",
    "anthropic": "claude-3-5-sonnet-latest",
    "xai": "grok-2-latest",  # Changed from grok-latest
    "deepseek": "deepseek-r1-70b"
}

# Update API configurations with full model support
API_ENDPOINTS = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "models_endpoint": "https://api.openai.com/v1/models",
        "key": os.getenv("OPENAI_API_KEY"),
        "default_model": "gpt-4-turbo-preview",
        "dynamic_models": True
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY"),
        "default_model": "deepseek-r1-distill-llama-70b",
        "headers": lambda key: {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "key": os.getenv("MISTRAL_API_KEY"),
        "default_model": "codestral-latest"
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key": os.getenv("ANTHROPIC_API_KEY"),
        "default_model": "claude-3.5-haiku-20241022"
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "key": os.getenv("XAI_API_KEY"),
        "default_model": "grok-2-latest",  # Updated default model
        "headers": lambda key: {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.ai/v1/chat/completions",
        "key": os.getenv("DEEPSEEK_API_KEY"),
        "default_model": "deepseek-chat"
    }
}

MODEL_CONFIGS = {
    "openai": [
        # GPT-4 Models
        'gpt-4o',
        'gpt-4o-mini',
        'chatgpt-4o-latest',
        'o1',
        'o1-mini',
        'o3-mini',
        'o1-preview',
        'gpt-4o-realtime-preview',
        'gpt-4o-mini-realtime-preview',
        'gpt-4o-audio-preview',
        # Standard Models
        'gpt-4-turbo-preview',
        'gpt-4-0125-preview',
        'gpt-4',
        'gpt-4-32k',
        'gpt-3.5-turbo',
        'gpt-3.5-turbo-16k'
    ],
    "groq": [
        # Large Models
        'mixtral-8x7b-32768',
        'llama2-70b-4096',
        'llama-3.3-70b-versatile',
        'gemma2-9b-it',
        # Medium Models
        'gemma-7b-it',
        'llama-3.1-8b-instant',
        'llama3-8b-8192',
        'llama-guard-3-8b',
        'llama3-70b-8192',
        # Audio Models
        'whisper-large-v3',
        'whisper-large-v3-turbo',
        'distil-whisper-large-v3-en',
        # Preview Models
        'qwen-2.5-coder-32b',
        'qwen-2.5-32b',
        'deepseek-r1-distill-qwen-32b',
        'deepseek-r1-distill-llama-70b',
        'deepseek-r1-distill-llama-70b-specdec',
        'llama-3.3-70b-specdec',
        'llama-3.2-1b-preview',
        'llama-3.2-3b-preview',
        'llama-3.2-11b-vision-preview',
        'llama-3.2-90b-vision-preview'
    ],
    "mistral": [
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
        'mathstral',
        # Legacy Models
        'open-mixtral-8x7b',
        'open-mistral-7b',
        'open-mixtral-8x22b',
        'mistral-small-2402',
        'mistral-large-2402',
        'mistral-large-2407'
    ],
    "anthropic": [
        # Claude 3 Series
        'claude-3-opus-20240229',
        'claude-3-sonnet-20240229',
        'claude-3-haiku-20240307',
        # Claude 3.5 Series
        'claude-3-5-sonnet-latest',
        'claude-3-5-haiku-latest',
        'claude-3-5-sonnet-20241022',
        'claude-3-5-haiku-20241022',
        # Claude 3.7 Series
        'claude-3-7-sonnet-20240317'
    ],
    "xai": [
        # Grok 2 Models
        'grok-2-latest',
        'grok-2-1212',
        'grok-2',
        # Grok Vision Models
        'grok-2-vision-latest',
        'grok-2-vision-1212',
        'grok-2-vision',
        # Beta Models
        'grok-beta',
        'grok-vision-beta'
    ],
    "deepseek": [
        # Chat Models
        'deepseek-chat',
        'deepseek-coder',
        'deepseek-reasoner',
        'deepseek-math',
        'deepseek-english',
        # Large Models
        'deepseek-r1-70b',
        'deepseek-r1-70b-alpha',
        'deepseek-r1-70b-chat',
        'deepseek-r1-70b-instruct'
    ]
}

# System message
SYSTEM_MESSAGE = (
    "You are an expert developer skilled in multiple programming languages, including Python, HTML, CSS, JavaScript, Rust, TypeScript, Java, C++, and more. "
    "Your primary tasks are to write complete, functional code based on user descriptions and requirements, review and debug code, optimize performance, and provide clear explanations. "
    "Follow these guidelines:\n\n"
    "1. **Code Quality**:\n\n"
    "- Write clean, readable, and efficient code.\n\n"
    "- Follow language-specific best practices and style guidelines.\n\n"
    "- Include comments and docstrings for clarity.\n\n"
    "2. **Functional Code**:\n\n"
    "- Provide complete, functional code snippets or scripts.\n\n"
    "- Ensure code is ready to run and meets the user's requirements.\n\n"
    "- Include necessary imports and setup.\n\n"
    "3. **Error Handling**:\n\n"
    "- Implement robust error handling.\n\n"
    "- Use appropriate mechanisms (e.g., try-catch) to handle exceptions.\n\n"
    "- Validate inputs to prevent runtime errors.\n\n"
    "4. **Review and Debug**:\n\n"
    "- Review user-provided code for errors and inefficiencies.\n\n"
    "- Identify and correct bugs, syntax errors, and logical issues.\n\n"
    "- Provide detailed explanations of the issues found and the steps taken to resolve them.\n\n"
    "5. **Optimize Performance**:\n\n"
    "- Identify performance bottlenecks and inefficiencies.\n\n"
    "- Suggest and implement optimizations to improve execution speed and resource usage.\n\n"
    "- Explain the optimization techniques used.\n\n"
    "6. **Documentation**:\n\n"
    "- Provide clear explanations and step-by-step instructions.\n\n"
    "- Offer additional resources if needed.\n\n"
    "7. **Safety and Compliance**:\n\n"
    "- Avoid harmful, unethical, or illegal code.\n\n"
    "- Refrain from discussions related to hacking or malware.\n\n"
    "- Ensure compliance with legal standards.\n\n"
    "8. **User Assistance**:\n\n"
    "- Focus on solving the user's specific problem directly.\n\n"
    "- Ask clarifying questions if more context is needed.\n\n"
    "- Tailor responses to the user's expertise level.\n\n"
    "9. **Learning and Improvement**:\n\n"
    "- Use search capabilities to find solutions if needed.\n\n"
    "- Stay updated with the latest language developments.\n\n"
    "10. **Conciseness**:\n\n"
    "- Be concise while providing necessary details.\n\n"
    "- Avoid redundancy and focus on delivering value.\n\n"
    "11. **Professionalism**:\n\n"
    "- Maintain a respectful and patient tone.\n\n"
    "- Be understanding, especially with beginners.\n\n"
    "Your role is to assist users by writing, reviewing, debugging, optimizing, and explaining code across multiple programming languages. Always prioritize clarity, safety, and efficiency in your responses."
)

SAVE_DIR = Path("saved_chats")
EXPORT_DIR = Path("exports")

# Create necessary directories
SAVE_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        print("ERROR: ffmpeg is not installed. Audio features will not work.")
        print("Please install ffmpeg:")
        print("Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("CentOS/RHEL: sudo yum install ffmpeg ffmpeg-devel")
        print("MacOS: brew install ffmpeg")
        return False

def format_ai_response(content, provider, model, timing):
    """Format AI response with metadata"""
    return {
        'markdown': content,
        'html': markdown2.markdown(content, extras=[
            "fenced-code-blocks",
            "code-friendly",
            "break-on-newline",
            "tables",
            "smarty-pants"
        ]),
        'text': content,
        'metadata': {
            'provider': provider,
            'model': model,
            'generated_at': datetime.now().isoformat(),
            'response_time': f"{timing:.2f}s"
        }
    }

def get_response_content(response_data, provider):
    """Extract content from provider-specific response format"""
    if provider == "anthropic":
        return response_data['content'][0]['text']
    else:
        return response_data['choices'][0]['message']['content']

def build_chat_payload(provider, model, message, system_message=None):
    """Build provider-specific chat payload"""
    base_payload = {
        'model': model,
        'temperature': 0.7,
        'max_tokens': 4096
    }

    if provider == "anthropic":
        return {
            **base_payload,
            'messages': [{'role': 'user', 'content': message}],
            'system': system_message or SYSTEM_MESSAGE
        }
    elif provider == "groq":
        return {
            **base_payload,
            'messages': [
                {'role': 'system', 'content': system_message or SYSTEM_MESSAGE},
                {'role': 'user', 'content': message}
            ]
        }
    else:
        return {
            **base_payload,
            'messages': [
                {'role': 'system', 'content': system_message or SYSTEM_MESSAGE},
                {'role': 'user', 'content': message}
            ]
        }

def build_headers(provider, api_key):
    """Build headers for specific provider"""
    if provider == "groq":
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    elif provider == "anthropic":
        return {
            'x-api-key': api_key,
            'anthropic-version': '2024-01-01',
            'Content-Type': 'application/json'
        }
    else:
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

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

        if not all([provider, model, message]):
            return jsonify({'error': 'Missing required parameters'}), 400

        provider_config = API_ENDPOINTS.get(provider)
        if not provider_config:
            return jsonify({'error': f'Invalid provider: {provider}'}), 400

        api_key = provider_config['key']
        if not api_key:
            return jsonify({'error': f'Missing API key for {provider}'}), 401

        # Build headers and payload
        headers = build_headers(provider, api_key)
        payload = build_chat_payload(provider, model, message)

        # Make request
        response = requests.post(
            provider_config['endpoint'],
            headers=headers,
            json=payload,
            timeout=30
        )

        if not response.ok:
            error_content = response.json() if response.content else str(response)
            return jsonify({'error': f'API request failed: {error_content}'}), response.status_code

        # Extract and format response
        content = get_response_content(response.json(), provider)
        formatted_response = format_ai_response(
            content=content,
            provider=provider,
            model=model,
            timing=time.time() - start_time
        )

        return jsonify({'response': formatted_response})

    except requests.Timeout:
        return jsonify({'error': 'Request timed out'}), 504
    except requests.RequestException as e:
        return jsonify({'error': f'Request failed: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Handle transcription endpoint with better error handling"""
    if request.files:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        audio_file = request.files['audio']
    else:
        # Handle empty request for audio initialization check
        return jsonify({'status': 'Audio endpoint available'}), 200

    try:
        # Convert audio to WAV format
        audio = AudioSegment.from_file(audio_file)
        wav_data = io.BytesIO()
        audio.export(wav_data, format="wav")
        wav_data.seek(0)

        # Use speech recognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_data) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return jsonify({'text': text})
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return jsonify({'error': 'Failed to transcribe audio', 'details': str(e)}), 500

@app.route('/save_chat', methods=['POST'])
def save_chat():
    try:
        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'Invalid chat data'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"chat_{timestamp}.json"
        filepath = SAVE_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'message': 'Chat saved successfully',
            'filename': filename
        })
    except Exception as e:
        print(f"Save error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/list_saved_chats')
def list_saved_chats():
    try:
        chats = []
        for file in SAVE_DIR.glob('*.json'):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                preview = data['history'][0]['content'] if data['history'] else 'Empty chat'
                if isinstance(preview, dict):
                    preview = preview.get('text', 'No text available')
                preview = preview[:100]  # Limit preview length
                chats.append({
                    'filename': file.name,
                    'timestamp': data.get('timestamp', ''),
                    'preview': preview
                })
        return jsonify(sorted(chats, key=lambda x: x['timestamp'], reverse=True))
    except Exception as e:
        print(f"List error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/load_chat/<filename>')
def load_chat(filename):
    try:
        filepath = SAVE_DIR / filename
        if not filepath.exists():
            return jsonify({'error': 'Chat file not found'}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"Load error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def extract_chat_topic(history):
    """Extract a topic from chat history for file naming"""
    try:
        # Get first user message
        first_msg = next((msg for msg in history if msg.get('isUser')), None)
        if not first_msg:
            return None

        content = first_msg.get('content', '')

        # Extract text from content if it's a dict
        if isinstance(content, dict):
            content = content.get('text', '')

        # Clean and format topic
        topic = str(content).split('\n')[0]  # Get first line
        topic = ''.join(c for c in topic if c.isalnum() or c.isspace())  # Remove special chars
        topic = topic[:50].strip()  # Limit length
        return topic.replace(' ', '_').lower() if topic else None
    except Exception as e:
        print(f"Topic extraction error: {str(e)}")
        return None

@app.route('/export_chat', methods=['POST'])
def export_chat():
    try:
        data = request.get_json()
        if not data or 'history' not in data:
            return jsonify({'error': 'Invalid chat data'}), 400

        # Generate filename using topic
        topic = extract_chat_topic(data['history'])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"chat_{topic}_{timestamp}.md" if topic else f"chat_export_{timestamp}.md"
        filepath = EXPORT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            # Write chat metadata
            f.write(f"# Chat Export: {topic or 'Untitled'}\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Write messages
            for msg in data['history']:
                role = "User" if msg.get('isUser') else "Assistant"
                content = msg.get('content', '')

                # Handle different content formats
                if isinstance(content, dict):
                    # Extract metadata if available
                    metadata = content.get('metadata', {})
                    if metadata:
                        f.write(f"_{metadata.get('provider', 'Unknown')}/{metadata.get('model', 'Unknown')} "
                               f"({metadata.get('response_time', '0s')})_\n\n")

                    # Extract content text
                    text = content.get('text', content.get('markdown', str(content)))
                else:
                    text = str(content)

                # Write message
                f.write(f"## {role}\n\n{text}\n\n---\n\n")

        return jsonify({
            'message': 'Chat exported successfully',
            'filename': filename
        })
    except Exception as e:
        print(f"Export error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add new route for model listing
@app.route('/get_models/<provider>')
def get_models(provider):
    """Get available models for a specific provider"""
    if provider not in MODEL_CONFIGS:
        return jsonify([])

    try:
        models = MODEL_CONFIGS[provider]
        default_model = DEFAULT_MODELS.get(provider)
        return jsonify({
            'models': models,
            'default': default_model
        })
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {str(e)}")
        return jsonify({'models': [], 'default': None})

if __name__ == '__main__':
    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg:
        print("Starting without audio support...")
    app.run(debug=True)
