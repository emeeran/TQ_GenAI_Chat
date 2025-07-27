"""
Script to parse and normalize model lists from provider API responses or documentation.
- For OpenAI and Groq: expects JSON from their API endpoints.
- For Anthropic, XAI/Grok, Mistral: expects manual input or parsed doc lists.
"""
import json
import sys

def normalize_openai_models(api_response):
    models = {}
    for m in api_response.get('data', []):
        model_id = m.get('id')
        if not model_id:
            continue
        # Add more metadata extraction as needed
        models[model_id] = {'name': model_id}
    return models

def normalize_groq_models(api_response):
    models = {}
    for m in api_response.get('data', []):
        model_id = m.get('id')
        if not model_id:
            continue
        models[model_id] = {'name': model_id}
    return models

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 parse_models.py <provider> <input_json_file>")
        sys.exit(1)
    provider = sys.argv[1]
    input_file = sys.argv[2]
    with open(input_file) as f:
        data = json.load(f)
    if provider == 'openai':
        models = normalize_openai_models(data)
    elif provider == 'groq':
        models = normalize_groq_models(data)
    else:
        print(f"Provider {provider} not supported for auto-normalization.")
        sys.exit(1)
    print(json.dumps(models, indent=2))
