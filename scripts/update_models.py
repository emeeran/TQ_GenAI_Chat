import os
import requests
import json

# Fetch OpenAI models
def fetch_openai_models(api_key):
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# Fetch Groq models
def fetch_groq_models(api_key):
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    openai_key = os.getenv("OPENAI_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEY", "")
    if openai_key:
        print("Fetching OpenAI models...")
        openai_models = fetch_openai_models(openai_key)
        print(json.dumps(openai_models, indent=2))
    else:
        print("OPENAI_API_KEY not set.")
    if groq_key:
        print("Fetching Groq models...")
        groq_models = fetch_groq_models(groq_key)
        print(json.dumps(groq_models, indent=2))
    else:
        print("GROQ_API_KEY not set.")
