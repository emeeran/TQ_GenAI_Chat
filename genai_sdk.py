"""
Minimal unified GenAI SDK for chat completions across multiple providers.
Supports: OpenAI, Anthropic, Groq, Alibaba, Hugging Face, Moonshot, Perplexity, Gemini, Mistral
"""
import os
import requests

class GenAI:
    def __init__(self):
        self.configs = {
            "openai": {
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "key": os.getenv("OPENAI_API_KEY", ""),
            },
            "anthropic": {
                "endpoint": "https://api.anthropic.com/v1/messages",
                "key": os.getenv("ANTHROPIC_API_KEY", ""),
            },
            "groq": {
                "endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "key": os.getenv("GROQ_API_KEY", ""),
            },
            "alibaba": {
                "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "key": os.getenv("ALIBABA_API_KEY", ""),
            },
            "huggingface": {
                "endpoint": "https://api-inference.huggingface.co/models/",
                "key": os.getenv("HUGGINGFACE_API_KEY", ""),
            },
            "moonshot": {
                "endpoint": "https://api.moonshot.cn/v1/chat/completions",
                "key": os.getenv("MOONSHOT_API_KEY", ""),
            },
            "perplexity": {
                "endpoint": "https://api.perplexity.ai/chat/completions",
                "key": os.getenv("PERPLEXITY_API_KEY", ""),
            },
            "gemini": {
                "endpoint": "https://generativelanguage.googleapis.com/v1/models/",
                "key": os.getenv("GEMINI_API_KEY", ""),
            },
            "mistral": {
                "endpoint": "https://api.mistral.ai/v1/chat/completions",
                "key": os.getenv("MISTRAL_API_KEY", ""),
            },
            "cerebras": {
                "endpoint": "https://api.cerebras.ai/v1/chat/completions",
                "key": os.getenv("CEREBRAS_API_KEY", ""),
            },
        }

    def chat(self, provider, model, message, persona="", temperature=0.7, max_tokens=4000):
        cfg = self.configs.get(provider)
        if not cfg or not cfg["key"]:
            raise ValueError(f"Provider {provider} not configured or missing API key.")
        endpoint = cfg["endpoint"]
        headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
        # Provider-specific payloads
        if provider in ["openai", "groq", "mistral", "moonshot", "perplexity"]:
            payload = {
                "model": model,
                "messages": ([{"role": "system", "content": persona}] if persona else []) + [{"role": "user", "content": message}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        elif provider == "anthropic":
            payload = {
                "model": model,
                "system": persona,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        elif provider == "alibaba":
            payload = {
                "model": model,
                "input": {
                    "messages": ([{"role": "system", "content": persona}] if persona else []) + [{"role": "user", "content": message}],
                },
                "parameters": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            }
        elif provider == "huggingface":
            endpoint = f"{endpoint}{model}"
            payload = {
                "inputs": f"{persona}\n{message}" if persona else message,
                "parameters": {"temperature": temperature, "max_new_tokens": max_tokens, "return_full_text": False},
            }
        elif provider == "gemini":
            endpoint = f"{endpoint}{model}:generateContent?key={cfg['key']}"
            payload = {"contents": [{"role": "user", "parts": [{"text": f"{persona}\n{message}"}]}]}
        else:
            raise ValueError(f"Provider {provider} not supported.")
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
