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

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()
# Load environment variables from .env file
# API endpoints for different providers

# API endpoints for different providers
API_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "xai": "https://api.x.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.ai/v1/chat/completions"
}

# API keys for different providers
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "groq": os.getenv("GROQ_API_KEY"),
    "mistral": os.getenv("MISTRAL_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY")
}

# Add after API_KEYS
MODEL_CONFIGS = {
    "openai": [
        'gpt-4-turbo-preview',
        'gpt-4-0125-preview',
        'gpt-4',
        'gpt-4-32k',
        'gpt-3.5-turbo',
        'gpt-3.5-turbo-16k',
        'gpt-3.5-turbo-instruct'
    ],
    "groq": [
        'mixtral-8x7b-32768',
        'llama2-70b-4096',
        'llama-3.3-70b-versatile',
        'gemma-7b-it',
        'llama-3.1-8b-instant',
        'llama3-8b-8192',
        'deepseek-r1-distill-llama-70b',
        'deepseek-r1-distill-qwen-32b',
        'qwen-2.5-32b'
    ],
    "mistral": [
        'mistral-large-latest',
        'mistral-medium-latest',
        'mistral-small-latest',
        'mistral-tiny-latest',
        'codestral-latest',
        'pixtral-large-latest',
        'mistral-embed',
        'open-mistral-nemo',
        'open-mixtral-8x7b'
    ],
    "anthropic": [
        'claude-3-opus-20240229',
        'claude-3-sonnet-20240229',
        'claude-3-haiku-20240307',
        'claude-3-5-sonnet-20241022',
        'claude-3-5-haiku-20241022',
        'claude-3-7-sonnet-20240317'
    ],
    "xai": [
        'grok-2-vision-latest',
        'grok-2-latest',
        'grok-vision-beta',
        'grok-beta'
    ],
    "deepseek": [
        'deepseek-chat',
        'deepseek-coder',
        'deepseek-reasoner',
        'deepseek-math',
        'deepseek-english'
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    start_time = time.time()
    data = request.get_json()
    provider = data.get('provider')
    model = data.get('model')
    message = data.get('message')

    if not all([provider, model, message]):
        return jsonify({'error': 'Missing required parameters'}), 400

    if provider not in API_ENDPOINTS:
        return jsonify({'error': f'Invalid provider: {provider}'}), 400

    if model not in MODEL_CONFIGS.get(provider, []):
        return jsonify({'error': f'Invalid model for provider {provider}'}), 400

    api_key = API_KEYS.get(provider)
    if not api_key:
        return jsonify({'error': f'Missing API key for provider {provider}'}), 401

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    # Special handling for Anthropic
    if provider == 'anthropic':
        headers.update({
            'anthropic-version': '2024-01-01',
            'x-api-key': api_key
        })
        payload = {
            'model': model,
            'max_tokens': 4096,
            'messages': [
                {'role': 'user', 'content': message}
            ],
            'system': SYSTEM_MESSAGE
        }
    else:
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': SYSTEM_MESSAGE},
                {'role': 'user', 'content': message}
            ]
        }

    try:
        response = requests.post(
            API_ENDPOINTS[provider],
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        # Handle different response formats
        if provider == 'anthropic':
            content = response.json()['content'][0]['text']
        else:
            content = response.json()['choices'][0]['message']['content']

        # Format response with metadata
        formatted_response = format_ai_response(
            content=content,
            provider=provider,
            model=model,
            timing=time.time() - start_time
        )

        return jsonify({'response': formatted_response})
    except Exception as e:
        return jsonify({'error': f'API request failed: {str(e)}'}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']

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
        return jsonify({'error': 'Failed to transcribe audio'}), 500

# Add new route for model listing
@app.route('/get_models/<provider>')
def get_models(provider):
    """Get available models for a specific provider"""
    if provider not in MODEL_CONFIGS:
        return jsonify([])

    try:
        models = MODEL_CONFIGS[provider]
        return jsonify(models)
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg:
        print("Starting without audio support...")
    app.run(debug=True)
