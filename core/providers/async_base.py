"""Async base provider interface for high-performance operations"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import aiohttp


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
    stream: bool = False


@dataclass
class ChatResponse:
    """Standardized chat response format"""

    content: str
    model: str
    usage: dict[str, Any]
    provider: str
    response_time: float = 0.0
    cached: bool = False


class AsyncAIProviderInterface(ABC):
    """Async base class for AI providers with performance optimizations"""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._request_count = 0
        self._total_response_time = 0.0

    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    @abstractmethod
    async def get_models(self) -> list[str]:
        """Get available models for this provider"""
        pass

    @abstractmethod
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion request asynchronously"""
        pass

    @abstractmethod
    async def chat_completion_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Stream chat completion response"""
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

    @property
    def average_response_time(self) -> float:
        """Get average response time for this provider"""
        if self._request_count == 0:
            return 0.0
        return self._total_response_time / self._request_count

    def _record_response_time(self, response_time: float):
        """Record response time for performance monitoring"""
        self._request_count += 1
        self._total_response_time += response_time
