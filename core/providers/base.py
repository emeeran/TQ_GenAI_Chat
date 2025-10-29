"""Base provider interface for strategy pattern"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatMessage:
    """Standardized chat message format"""

    role: str
    content: str


@dataclass
class ChatRequest:
    """Standardized chat request format"""

    messages: list[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None


@dataclass
class ChatResponse:
    """Standardized chat response format"""

    content: str
    model: str
    usage: dict[str, Any]
    provider: str


class AIProviderInterface(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    def get_models(self) -> list[str]:
        """Get available models for this provider"""
        pass

    @abstractmethod
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion request"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
