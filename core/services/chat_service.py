"""Chat service with business logic"""

from typing import Any

from app.models.requests import ChatRequest
from core.context import ContextManager
from core.providers import ChatMessage, ProviderFactory
from core.validation import ChatRequestValidator


class ChatService:
    """Service for handling chat operations"""

    def __init__(self, provider_factory: ProviderFactory, context_manager: ContextManager):
        self.provider_factory = provider_factory
        self.context_manager = context_manager
        self.validator = ChatRequestValidator()

    def process_chat_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process chat request with validation and context injection"""
        try:
            # Validate request
            validation_result = self.validator.validate(data)
            if not validation_result.is_valid:
                raise ValueError(f"Invalid request: {validation_result.errors}")

            # Get provider
            provider_name = data.get("provider", "openai")
            provider = self.provider_factory.get_provider(provider_name)
            if not provider:
                raise ValueError(f"Provider {provider_name} not available")

            # Build chat request
            messages = self._build_messages(data)

            # Inject context if available
            if self.context_manager.has_context():
                context = self.context_manager.get_relevant_context(data.get("message", ""))
                if context:
                    messages.insert(-1, ChatMessage(role="system", content=f"Context: {context}"))

            chat_request = ChatRequest(
                messages=messages,
                model=data.get("model", provider.get_models()[0]),
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens"),
            )

            # Process request
            response = provider.chat_completion(chat_request)

            return {
                "success": True,
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": provider_name if "provider_name" in locals() else "unknown",
            }

    def _build_messages(self, data: dict[str, Any]) -> list[ChatMessage]:
        """Build messages from request data"""
        messages = []

        # Add persona/system message
        if data.get("persona"):
            messages.append(ChatMessage(role="system", content=data["persona"]))

        # Add chat history
        for msg in data.get("history", []):
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

        # Add current message
        if data.get("message"):
            messages.append(ChatMessage(role="user", content=data["message"]))

        return messages

    def get_available_providers(self) -> list[str]:
        """Get list of available providers"""
        return self.provider_factory.get_available_providers()

    def get_models_for_provider(self, provider: str) -> list[str]:
        """Get models for specific provider"""
        return self.provider_factory.get_models_for_provider(provider)
