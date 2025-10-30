"""
Async LiteLLM provider integration for multi-provider AI support.
"""

import asyncio
import logging
from typing import Any

import litellm

logger = logging.getLogger(__name__)


async def generate_llm_response(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4000,
    **kwargs: Any
) -> dict[str, Any]:
    """Unified async LLM response using LiteLLM"""
    try:
        # Use acompletion for async calls
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

<<<<<<< HEAD
        # Convert usage to serializable dict
        usage = response.get("usage", {})
        if usage:
            # Convert any non-serializable objects to dict
            usage_dict = {}
            for key, value in usage.items():
                if hasattr(value, '__dict__'):
                    # Convert object to dict
                    usage_dict[key] = value.__dict__
                elif hasattr(value, 'model_dump'):
                    # For Pydantic models
                    usage_dict[key] = value.model_dump()
=======

class OpenAICompatibleProvider(BaseProvider):
    """Enhanced provider for OpenAI-compatible APIs with better error handling"""

    def __init__(self, config: ProviderConfig, provider_name: str):
        super().__init__(config)
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, RequestHeaders, RequestPayload]:
        """Prepare OpenAI-compatible request with validation"""
        headers: RequestHeaders = {
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

        # Build messages with persona if provided
        messages = []
        if persona.strip():
            messages.append({"role": "system", "content": persona.strip()})
        messages.append({"role": "user", "content": message})

        payload: RequestPayload = {
            "model": model,
            "messages": messages,
            "temperature": max(0.0, min(2.0, temperature)),  # Clamp temperature
            "max_tokens": max(1, min(8192, max_tokens)),  # Clamp max_tokens
        }

        return self.config.endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        """Extract response with enhanced error checking"""
        try:
            # Alibaba (Qwen) response format fix
            if self.provider_name == "alibaba":
                # Qwen sometimes returns 'output' or 'result' keys
                if "output" in result and isinstance(result["output"], dict):
                    text = result["output"].get("text", "")
                    return APIResponse(
                        text=text,
                        metadata=self._create_metadata(model, response_time, fallback_used),
                    )
                elif "result" in result and isinstance(result["result"], dict):
                    text = result["result"].get("text", "")
                    return APIResponse(
                        text=text,
                        metadata=self._create_metadata(model, response_time, fallback_used),
                    )

            # Standard OpenAI-compatible response
            if not isinstance(result, dict):
                raise TypeError("Response is not a dictionary")

            if "choices" not in result or not result["choices"]:
                raise KeyError("No choices in response")

            choice = result["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                raise KeyError("Invalid message structure")

            text = choice["message"]["content"]
            if not isinstance(text, str):
                raise TypeError("Response text is not a string")

            # Extract usage information if available
            usage = result.get("usage", {})

            return APIResponse(
                text=text,
                metadata=self._create_metadata(model, response_time, fallback_used),
                usage=usage,
            )

        except (KeyError, IndexError, TypeError) as e:
            return APIResponse(
                text="",
                metadata=self._create_metadata(model, response_time, fallback_used),
                success=False,
                error=f"Invalid {self.provider_name} response structure: {str(e)}",
            )




class OpenRouterProvider(OpenAICompatibleProvider):
    """Provider for OpenRouter, which is OpenAI-compatible but with special headers."""

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, RequestHeaders, RequestPayload]:
        """Prepare OpenRouter-compatible request with additional headers."""
        endpoint, headers, payload = super()._prepare_request(
            model, message, persona, temperature, max_tokens
        )
        
        # Add OpenRouter-specific headers for analytics and routing
        headers["HTTP-Referer"] = "https://tqgenaichat.com"  # Replace with your app's URL
        headers["X-Title"] = "TQ GenAI Chat"  # Replace with your app's name
        
        return endpoint, headers, payload

class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider"""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        headers = {
            "x-api-key": self.config.key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": model,
            "system": persona,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": max_tokens,
        }

        return self.config.endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            if "content" in result and result["content"]:
                text = result["content"][0]["text"]
                return APIResponse(
                    text=text,
                    metadata=self._create_metadata(model, response_time, fallback_used),
                )
        except (KeyError, IndexError, TypeError):
            pass

        return APIResponse(
            text="",
            metadata={},
            success=False,
            error="Invalid Anthropic response structure",
        )


class GeminiProvider(BaseProvider):
    """Google Gemini provider"""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        endpoint = f"{self.config.endpoint}{model}:generateContent?key={self.config.key}"
        headers = {"Content-Type": "application/json"}

        payload = {"contents": [{"role": "user", "parts": [{"text": f"{persona}\n{message}"}]}]}

        return endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            candidates = result.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    text = parts[0]["text"]
                    return APIResponse(
                        text=text,
                        metadata=self._create_metadata(model, response_time, fallback_used),
                    )
        except (KeyError, IndexError, TypeError):
            pass

        return APIResponse(
            text="",
            metadata={},
            success=False,
            error="Invalid Gemini response structure",
        )


class CohereProvider(BaseProvider):
    """Cohere provider"""

    @property
    def provider_name(self) -> str:
        return "cohere"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        headers = {
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        return self.config.endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            text = result["message"]["content"][0]["text"]
            return APIResponse(
                text=text,
                metadata=self._create_metadata(model, response_time, fallback_used),
            )
        except (KeyError, IndexError, TypeError):
            return APIResponse(
                text="",
                metadata={},
                success=False,
                error="Invalid Cohere response structure",
            )


class HuggingFaceProvider(BaseProvider):
    """Hugging Face Inference API provider"""

    @property
    def provider_name(self) -> str:
        return "huggingface"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        # Hugging Face uses model-specific endpoints
        endpoint = f"{self.config.endpoint}{model}"
        headers = {
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

        # Build the prompt with persona if provided
        prompt = f"{persona}\n{message}" if persona.strip() else message

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        return endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            # Hugging Face returns different formats depending on the model
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    text = result[0]["generated_text"]
                elif "text" in result[0]:
                    text = result[0]["text"]
>>>>>>> 79dbc2301174a782477670b126d2c939f9a6e387
                else:
                    usage_dict[key] = value
        else:
            usage_dict = {}

        return {
            "success": True,
            "content": response["choices"][0]["message"]["content"],
            "model": model,
            "provider": "litellm",
            "usage": usage_dict,
        }
    except Exception as e:
        logger.error(f"LiteLLM error for model {model}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "provider": "litellm",
        }

<<<<<<< HEAD
=======
    def _create_provider(self, name: str, config: ProviderConfig) -> BaseProvider:
        """Factory method to create providers based on type"""
        if name == "openrouter":
            return OpenRouterProvider(config, name)
        
        match config.provider_type:
            case ProviderType.ANTHROPIC:
                return AnthropicProvider(config)
            case ProviderType.GEMINI:
                return GeminiProvider(config)
            case ProviderType.COHERE:
                return CohereProvider(config)
            case ProviderType.HUGGINGFACE:
                return HuggingFaceProvider(config)
            case ProviderType.OPENAI_COMPATIBLE:
                return OpenAICompatibleProvider(config, name)
            case _:  # Default fallback
                return OpenAICompatibleProvider(config, name)
>>>>>>> 79dbc2301174a782477670b126d2c939f9a6e387

def generate_llm_response_sync(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4000,
    **kwargs: Any
) -> dict[str, Any]:
    """Synchronous wrapper for backward compatibility"""
    try:
        # Get current event loop if it exists
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, create a new task
            return asyncio.create_task(
                generate_llm_response(model, messages, temperature, max_tokens, **kwargs)
            )
        else:
            # No event loop running, run in new loop
            return asyncio.run(
                generate_llm_response(model, messages, temperature, max_tokens, **kwargs)
            )
    except Exception as e:
        logger.error(f"Sync wrapper error for model {model}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "provider": "litellm",
        }