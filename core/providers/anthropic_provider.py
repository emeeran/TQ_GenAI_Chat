"""Anthropic provider implementation"""

import os

import anthropic

from .base import AIProviderInterface, ChatRequest, ChatResponse


class AnthropicProvider(AIProviderInterface):
    """Anthropic Claude API provider implementation"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            # Create a dummy client for testing
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=api_key)
        self._models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
        ]

    @property
    def name(self) -> str:
        return "anthropic"

    def get_models(self) -> list[str]:
        return self._models

    def is_available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using Anthropic API"""
        if not self.client:
            raise Exception("Anthropic client not initialized - API key missing")

        try:
            # Extract system message if present
            system_message = ""
            messages = []

            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    messages.append({"role": msg.role, "content": msg.content})

            response = self.client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens or 4000,
                temperature=request.temperature,
                system=system_message,
                messages=messages,
            )

            return ChatResponse(
                content=response.content[0].text,
                model=request.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                provider=self.name,
            )

        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
