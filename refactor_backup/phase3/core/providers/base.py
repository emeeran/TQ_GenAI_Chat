"""Base provider interface for strategy pattern"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """Standardized chat message format"""
    role: str
    content: str
    

@dataclass 
class ChatRequest:
    """Standardized chat request format"""
    messages: List[ChatMessage]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    

@dataclass
class ChatResponse:
    """Standardized chat response format"""
    content: str
    model: str
    usage: Dict[str, Any]
    provider: str


class AIProviderInterface(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def get_models(self) -> List[str]:
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
