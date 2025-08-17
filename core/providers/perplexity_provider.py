"""Perplexity provider implementation"""

from openai import OpenAI
import os
from .base import AIProviderInterface, ChatRequest, ChatResponse

class PerplexityProvider(AIProviderInterface):
    """
    Perplexity API provider implementation for Sonar series models.
    Supports sonar-small, sonar-medium, sonar-large, sonar-pro.
    Allows advanced search via extra_body (web, domain, recency filters).
    """

    def __init__(self):
        api_key = os.getenv("PERPLEXITY_API_KEY", "")
        if not api_key:
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        self._models = [
            "sonar-small",
            "sonar-medium",
            "sonar-large",
            "sonar-pro"
        ]

    @property
    def name(self) -> str:
        return "perplexity"

    def get_models(self) -> list[str]:
        return self._models

    def is_available(self) -> bool:
        return bool(os.getenv("PERPLEXITY_API_KEY"))

    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """
        Process chat completion using Perplexity Sonar models.
        Validates model name and payload. Only sends extra_body if not None.
        """
        if not self.client:
            raise Exception("Perplexity client not initialized - API key missing")
        if request.model not in self._models:
            raise Exception(f"Invalid Perplexity model: {request.model}. Must be one of {self._models}")
        try:
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            payload = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature if request.temperature is not None else 0.7,
                "top_p": getattr(request, "top_p", 0.9),
                "max_tokens": request.max_tokens or 1000,
                "presence_penalty": getattr(request, "presence_penalty", 0),
                "frequency_penalty": getattr(request, "frequency_penalty", 0),
                "stream": False,
            }
            extra_body = getattr(request, "extra_body", None)
            if extra_body:
                payload["extra_body"] = extra_body
            response = self.client.chat.completions.create(**payload)
            content = response.choices[0].message.content if response.choices else ""
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                "completion_tokens": getattr(response.usage, "completion_tokens", None),
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }
            if hasattr(response, "search_results"):
                usage["search_results"] = response.search_results
            return ChatResponse(
                content=content,
                model=request.model,
                usage=usage,
                provider=self.name,
            )
        except Exception as e:
            raise Exception(f"Perplexity API error: {str(e)} | Model: {request.model} | Payload: {payload}") from e
