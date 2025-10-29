#!/usr/bin/env python3
"""
Update Models from Providers Script

Fetches the latest models from each provider's API/website and updates the model list.
Removes deprecated models and adds new ones including preview models.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
from core.models import model_manager



def fetch_openai_models():
    """Fetch models from OpenAI API"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)

        if response.status_code == 200:
            models_data = response.json()
            # Filter for chat models
            chat_models = [
                model["id"]
                for model in models_data["data"]
                if "gpt" in model["id"] and model["id"] not in ["gpt-3.5-turbo-instruct"]
            ]
            return sorted(chat_models)
    except Exception as e:
        print(f"Failed to fetch OpenAI models: {e}")
    return []


def fetch_anthropic_models():
    """Fetch models from Anthropic (using known model list as API doesn't provide public endpoint)"""
    return [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]


def fetch_gemini_models():
    """Fetch models from Google Gemini API"""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return []

        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            models_data = response.json()
            models = []
            for model in models_data.get("models", []):
                model_name = model["name"].replace("models/", "")
                if "gemini" in model_name.lower():
                    models.append(model_name)
            return sorted(models)
    except Exception as e:
        print(f"Failed to fetch Gemini models: {e}")
    return []


def fetch_groq_models():
    """Fetch models from Groq API"""
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.groq.com/openai/v1/models", headers=headers, timeout=10
        )

        if response.status_code == 200:
            models_data = response.json()
            models = [model["id"] for model in models_data["data"]]
            return sorted(models)
    except Exception as e:
        print(f"Failed to fetch Groq models: {e}")
    return []


def fetch_cerebras_models():
    """Fetch available models from Cerebras API"""
    try:
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            print("CEREBRAS_API_KEY not found")
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.cerebras.ai/v1/models", headers=headers, timeout=10
        )

        if response.status_code == 200:
            models_data = response.json()
            models = [model["id"] for model in models_data["data"]]
            return sorted(models)
    except Exception as e:
        print(f"Failed to fetch Cerebras models: {e}")
    return []


def fetch_provider_models(provider_name):
    """Fetch models for a specific provider"""
    print(f"Fetching models for {provider_name}...")

    if provider_name == "cerebras":
        return fetch_cerebras_models()
    elif provider_name == "openai":
        return fetch_openai_models()
    elif provider_name == "anthropic":
        return fetch_anthropic_models()
    elif provider_name == "gemini":
        return fetch_gemini_models()
    elif provider_name == "groq":
        return fetch_groq_models()
    else:
        # For other providers, return current models (no API available)
        return model_manager.get_models(provider_name)


def update_all_models():
    """Update models for all configured providers"""
    updated_providers = []

    for provider_name in ["openai", "groq", "anthropic", "mistral", "gemini", "cohere", "xai", "deepseek", "alibaba", "openrouter", "huggingface", "moonshot", "perplexity"]:
        try:
            new_models = fetch_provider_models(provider_name)
            if new_models:
                current_models = model_manager.get_models(provider_name)

                # Update models
                model_manager.update_models(provider_name, new_models)

                print(f"✅ Updated {provider_name}: {len(new_models)} models")
                print(f"   Added: {len(set(new_models) - set(current_models))} new models")
                print(f"   Removed: {len(set(current_models) - set(new_models))} deprecated models")

                updated_providers.append(provider_name)
            else:
                print(f"⚠️  No models fetched for {provider_name}")

        except Exception as e:
            print(f"❌ Failed to update {provider_name}: {e}")

    return updated_providers


def set_default_models():
    """Set latest and economic models as default for each provider"""
    defaults = {
        "cerebras": "llama-3.3-70b",  # Latest and economic
        "openai": "gpt-4o-mini",  # Economic choice
        "anthropic": "claude-3-5-sonnet-latest",  # Latest
        "gemini": "gemini-2.0-flash",  # Latest and economic
        "groq": "deepseek-r1-distill-llama-70b",  # Latest
        "mistral": "mistral-large-latest",  # Latest
        "xai": "grok-4-latest",  # Latest
        "deepseek": "deepseek-chat",  # Economic
        "cohere": "command-a-03-2025",  # Latest
        "alibaba": "qwen3-32b",  # Latest
        "openrouter": "openai/gpt-4o",  # Economic
        "huggingface": "Qwen/Qwen3-Coder-480B-A35B-Instruct",  # Latest
        "moonshot": "moonshot-v1-auto",  # Auto-selection
        "perplexity": "pplx-70b-chat",  # Latest
    }

    for provider_name, default_model in defaults.items():
        if model_manager.is_provider_available(provider_name):
            try:
                model_manager.set_default_model(provider_name, default_model)
                print(f"✅ Set default for {provider_name}: {default_model}")
            except Exception as e:
                print(f"⚠️  Could not set default for {provider_name}: {e}")


def main():
    """Main execution"""
    print("🔄 Updating models from providers...")
    print("=" * 50)

    # Update all models
    updated_providers = update_all_models()

    print("\n" + "=" * 50)
    print("🎯 Setting default models...")

    # Set default models
    set_default_models()

    print("\n" + "=" * 50)
    print("✅ Model update complete!")
    print(f"📊 Updated providers: {', '.join(updated_providers)}")
    print("💾 Models cached and defaults set")


if __name__ == "__main__":
    main()
