"""OpenAI provider implementation"""

import os

import openai

from .base import AIProviderInterface, ChatRequest, ChatResponse


class OpenAIProvider(AIProviderInterface):
    """OpenAI API provider implementation"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            # Create a dummy client for testing
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=api_key)
        self._models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    @property
    def name(self) -> str:
        return "openai"

    def get_models(self) -> list[str]:
        return self._models

    def is_available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using OpenAI API"""
        if not self.client:
            raise Exception("OpenAI client not initialized - API key missing")

        try:
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

            response = self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            return ChatResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                provider=self.name,
            )

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
