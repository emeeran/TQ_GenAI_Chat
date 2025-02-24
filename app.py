# app.py
from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load environment variables from .env file
load_dotenv()

# API endpoints for different providers
API_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/v1/chat/completions",
    "mistral": "https://api.mistral.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/chat/completions"
}

# API keys for different providers
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "groq": os.getenv("GROQ_API_KEY"),
    "mistral": os.getenv("MISTRAL_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY")
}

# Add model endpoints
MODEL_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/models",
    "groq": "https://api.groq.com/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
    "deepseek": "https://api.deepseek.com/v1/models"
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    provider = data.get('provider')
    model = data.get('model')
    user_message = data.get('message')

    if not provider or not model or not user_message:
        return jsonify({'error': 'Missing required parameters'}), 400

    if provider not in API_ENDPOINTS or provider not in API_KEYS:
        return jsonify({'error': 'Invalid provider'}), 400

    api_url = API_ENDPOINTS[provider]
    api_key = API_KEYS[provider]

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_MESSAGE},
            {'role': 'user', 'content': user_message}
        ]
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        ai_response = response.json().get('choices')[0].get('message').get('content')
        return jsonify({'response': ai_response})
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_models/<provider>')
def get_models(provider):
    if provider not in MODEL_ENDPOINTS:
        return jsonify([])

    api_key = API_KEYS.get(provider)
    if not api_key:
        return jsonify({'error': 'API key not configured'}), 401

    headers = {'Authorization': f'Bearer {api_key}'}

    try:
        response = requests.get(MODEL_ENDPOINTS[provider], headers=headers)
        response.raise_for_status()

        # Handle provider-specific response formats
        if provider == 'openai':
            models = response.json()['data']
            return jsonify([model['id'] for model in models])

        elif provider == 'mistral':
            models = response.json()['data']
            return jsonify([model['id'] for model in models])

        elif provider == 'groq':
            models = response.json()['models']
            return jsonify([model['name'] for model in models])

        elif provider == 'anthropic':
            models = response.json()['models']
            return jsonify([model['id'] for model in models])

        elif provider == 'deepseek':
            models = response.json()['data']
            return jsonify([model['id'] for model in models])

    except requests.RequestException as e:
        # Fallback to default models if API call fails
        default_models = {
            'openai': ['gpt-4-turbo-preview', 'gpt-4', 'gpt-3.5-turbo'],
            'groq': ['mixtral-8x7b-32768', 'llama2-70b-4096'],
            'mistral': ['mistral-large-latest', 'mistral-medium-latest', 'mistral-small-latest'],
            'anthropic': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-2.1'],
            'deepseek': ['deepseek-coder', 'deepseek-chat']
        }
        return jsonify(default_models.get(provider, []))

if __name__ == '__main__':
    app.run(debug=True)
