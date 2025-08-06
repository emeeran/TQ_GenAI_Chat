"""
Dynamic Model Fetcher Service
Fetches the latest model lists from various AI providers' APIs.
"""

import os
import time

import aiohttp
from flask import current_app


class DynamicModelFetcher:
    """Fetches model lists dynamically from AI provider APIs."""

    def __init__(self):
        """Initialize with API credentials and endpoints."""
        self.api_keys = {
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "gemini": os.getenv("GEMINI_API_KEY", ""),
            "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
            "mistral": os.getenv("MISTRAL_API_KEY", ""),
            "cohere": os.getenv("COHERE_API_KEY", ""),
            "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
            "huggingface": os.getenv("HUGGINGFACE_API_KEY", ""),
            "xai": os.getenv("XAI_API_KEY", ""),
            "groq": os.getenv("GROQ_API_KEY", ""),
            "alibaba": os.getenv("ALIBABA_API_KEY", ""),
            "moonshot": os.getenv("MOONSHOT_API_KEY", ""),
        }

        self.model_endpoints = {
            "openai": "https://api.openai.com/v1/models",
            "anthropic": None,  # Anthropic doesn't have a public models endpoint
            "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
            "deepseek": "https://api.deepseek.com/models",
            "mistral": "https://api.mistral.ai/v1/models",
            "cohere": None,  # Cohere uses fixed model names
            "openrouter": "https://openrouter.ai/api/v1/models",
            "huggingface": None,  # HuggingFace has too many models, we'll use curated list
            "xai": "https://api.x.ai/v1/models",
            "groq": "https://api.groq.com/openai/v1/models",
            "alibaba": None,  # Alibaba uses fixed model names
            "moonshot": "https://api.moonshot.cn/v1/models",
        }

        # Fallback models for providers without dynamic endpoints
        self.fallback_models = {
            "openai": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo",
                "o1-preview",
                "o1-mini",
            ],
            "anthropic": [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "deepseek": [
                "deepseek-chat",
                "deepseek-coder",
                "deepseek-r1-distill-llama-70b",
                "deepseek-r1",
            ],
            "mistral": [
                "mistral-large-2411",
                "mistral-small",
                "mistral-nemo",
                "codestral-2405",
                "mixtral-8x7b-instruct",
            ],
            "openrouter": [
                "anthropic/claude-3.5-sonnet",
                "openai/gpt-4o",
                "google/gemini-2.0-flash-exp",
                "meta-llama/llama-3.1-405b-instruct",
                "mistralai/mistral-large",
            ],
            "xai": [
                "grok-2-1212",
                "grok-2-vision-1212",
                "grok-beta",
            ],
            "groq": [
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ],
            "moonshot": [
                "moonshot-v1-8k",
                "moonshot-v1-32k",
                "moonshot-v1-128k",
            ],
            "cohere": [
                "command-r-plus-08-2024",
                "command-r-08-2024",
                "command-r-plus",
                "command-r",
                "command-light",
            ],
            "huggingface": [
                "Qwen/Qwen3-235B-A22B-Instruct-2507",
                "meta-llama/Llama-3.3-70B-Instruct",
                "microsoft/DialoGPT-large",
                "google/flan-t5-large",
            ],
            "alibaba": [
                "qwen3-235b-a22b-instruct",
                "qwen-max",
                "qwen-plus",
                "qwen-turbo",
            ],
        }

    async def fetch_openai_models(self) -> list[str]:
        """Fetch models from OpenAI API."""
        if not self.api_keys["openai"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("openai", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['openai']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["openai"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        # Filter for chat completion models
                        chat_models = [
                            m
                            for m in models
                            if any(x in m for x in ["gpt", "o1", "chatgpt"])
                            and "embed" not in m
                            and "tts" not in m
                            and "whisper" not in m
                            and "dall-e" not in m
                        ]
                        return sorted(chat_models)
                    else:
                        current_app.logger.error(f"OpenAI API error: {response.status}")
                        return []
        except Exception as e:
            current_app.logger.error(f"Error fetching OpenAI models: {str(e)}")
            return []

    async def fetch_gemini_models(self) -> list[str]:
        """Fetch models from Google Gemini API."""
        if not self.api_keys["gemini"]:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                params = {"key": self.api_keys["gemini"]}

                async with session.get(
                    self.model_endpoints["gemini"],
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = []
                        for model in data.get("models", []):
                            model_name = model.get("name", "").replace("models/", "")
                            # Filter for generation models (not embedding, etc.)
                            if "generateContent" in model.get("supportedGenerationMethods", []):
                                models.append(model_name)
                        return sorted(models)
                    else:
                        current_app.logger.error(f"Gemini API error: {response.status}")
                        return []
        except Exception as e:
            current_app.logger.error(f"Error fetching Gemini models: {str(e)}")
            return []

    async def fetch_deepseek_models(self) -> list[str]:
        """Fetch models from DeepSeek API."""
        if not self.api_keys["deepseek"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("deepseek", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['deepseek']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["deepseek"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        return sorted(models)
                    else:
                        current_app.logger.error(f"DeepSeek API error: {response.status}")
                        return self.fallback_models.get("deepseek", [])
        except Exception as e:
            current_app.logger.error(f"Error fetching DeepSeek models: {str(e)}")
            return self.fallback_models.get("deepseek", [])

    async def fetch_mistral_models(self) -> list[str]:
        """Fetch models from Mistral AI API."""
        if not self.api_keys["mistral"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("mistral", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['mistral']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["mistral"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        return sorted(models)
                    else:
                        current_app.logger.error(f"Mistral API error: {response.status}")
                        return self.fallback_models.get("mistral", [])
        except Exception as e:
            current_app.logger.error(f"Error fetching Mistral models: {str(e)}")
            return self.fallback_models.get("mistral", [])

    async def fetch_openrouter_models(self) -> list[str]:
        """Fetch models from OpenRouter API."""
        if not self.api_keys["openrouter"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("openrouter", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['openrouter']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["openrouter"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        return sorted(models)
                    else:
                        current_app.logger.error(f"OpenRouter API error: {response.status}")
                        return self.fallback_models.get("openrouter", [])
        except Exception as e:
            current_app.logger.error(f"Error fetching OpenRouter models: {str(e)}")
            return self.fallback_models.get("openrouter", [])

    async def fetch_xai_models(self) -> list[str]:
        """Fetch models from X AI API."""
        if not self.api_keys["xai"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("xai", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['xai']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["xai"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        return sorted(models)
                    else:
                        current_app.logger.error(f"XAI API error: {response.status}")
                        return self.fallback_models.get("xai", [])
        except Exception as e:
            current_app.logger.error(f"Error fetching XAI models: {str(e)}")
            return self.fallback_models.get("xai", [])

    async def fetch_groq_models(self) -> list[str]:
        """Fetch models from Groq API."""
        if not self.api_keys["groq"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("groq", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['groq']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["groq"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        return sorted(models)
                    else:
                        current_app.logger.error(f"Groq API error: {response.status}")
                        return self.fallback_models.get("groq", [])
        except Exception as e:
            current_app.logger.error(f"Error fetching Groq models: {str(e)}")
            return self.fallback_models.get("groq", [])

    async def fetch_moonshot_models(self) -> list[str]:
        """Fetch models from Moonshot API."""
        if not self.api_keys["moonshot"]:
            # Use fallback models when no API key is available
            return self.fallback_models.get("moonshot", [])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_keys['moonshot']}",
                    "Content-Type": "application/json",
                }

                async with session.get(
                    self.model_endpoints["moonshot"],
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model["id"] for model in data.get("data", [])]
                        return sorted(models)
                    else:
                        current_app.logger.error(f"Moonshot API error: {response.status}")
                        return self.fallback_models.get("moonshot", [])
        except Exception as e:
            current_app.logger.error(f"Error fetching Moonshot models: {str(e)}")
            return self.fallback_models.get("moonshot", [])

    def get_fallback_models(self, provider: str) -> list[str]:
        """Get fallback models for providers without dynamic endpoints."""
        return self.fallback_models.get(provider, [])

    async def fetch_models_for_provider(self, provider: str) -> tuple[list[str], bool]:
        """
        Fetch models for a specific provider.
        Returns (models_list, is_dynamic) where is_dynamic indicates if fetched from API.
        """
        provider = provider.lower()

        try:
            if provider == "openai":
                models = await self.fetch_openai_models()
                return models, True
            elif provider == "gemini":
                models = await self.fetch_gemini_models()
                return models, True
            elif provider == "deepseek":
                models = await self.fetch_deepseek_models()
                return models, True
            elif provider == "mistral":
                models = await self.fetch_mistral_models()
                return models, True
            elif provider == "openrouter":
                models = await self.fetch_openrouter_models()
                return models, True
            elif provider == "xai":
                models = await self.fetch_xai_models()
                return models, True
            elif provider == "groq":
                models = await self.fetch_groq_models()
                return models, True
            elif provider == "moonshot":
                models = await self.fetch_moonshot_models()
                return models, True
            else:
                # Use fallback models for providers without dynamic endpoints
                models = self.get_fallback_models(provider)
                return models, False

        except Exception as e:
            current_app.logger.error(f"Error fetching models for {provider}: {str(e)}")
            # Return fallback models on error
            models = self.get_fallback_models(provider)
            return models, False

    async def fetch_all_models(self) -> dict[str, dict]:
        """
        Fetch models for all providers.
        Returns a dictionary with provider names as keys and model info as values.
        """
        providers = [
            "openai",
            "anthropic",
            "gemini",
            "deepseek",
            "mistral",
            "cohere",
            "openrouter",
            "huggingface",
            "xai",
            "groq",
            "alibaba",
            "moonshot",
        ]

        results = {}

        for provider in providers:
            try:
                models, is_dynamic = await self.fetch_models_for_provider(provider)

                # Categorize models
                preview_models = [m for m in models if "preview" in m.lower()]
                stable_models = [m for m in models if "preview" not in m.lower()]

                results[provider] = {
                    "models": models,
                    "count": len(models),
                    "preview_models": preview_models,
                    "stable_models": stable_models,
                    "preview_count": len(preview_models),
                    "stable_count": len(stable_models),
                    "has_preview_models": len(preview_models) > 0,
                    "is_dynamic": is_dynamic,
                    "last_updated": int(time.time()),
                }

                current_app.logger.info(
                    f"Fetched {len(models)} models for {provider} (dynamic: {is_dynamic})"
                )

            except Exception as e:
                current_app.logger.error(f"Failed to fetch models for {provider}: {str(e)}")
                results[provider] = {
                    "models": [],
                    "count": 0,
                    "preview_models": [],
                    "stable_models": [],
                    "preview_count": 0,
                    "stable_count": 0,
                    "has_preview_models": False,
                    "is_dynamic": False,
                    "error": str(e),
                    "last_updated": int(time.time()),
                }

        return results


# Global instance
model_fetcher = DynamicModelFetcher()
