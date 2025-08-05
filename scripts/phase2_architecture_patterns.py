#!/usr/bin/env python3
"""
Phase 2: Architectural Patterns & Service Layer Implementation
- Strategy Pattern for AI Providers
- Repository Pattern for Data Access
- Service Layer with Dependency Injection
- Enhanced Error Handling & Validation
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List


class RefactorPhase2:
    def __init__(self, root_path: str = "."):
        self.root = Path(root_path)
        self.backup_dir = self.root / "refactor_backup/phase2"
        
    def run(self):
        """Execute Phase 2 refactoring"""
        print("🚀 Starting Phase 2: Architectural Patterns & Service Layer")
        
        self.create_backup()
        self.create_strategy_patterns()
        self.create_service_layer()
        self.create_repository_layer()
        self.create_validation_layer()
        self.create_enhanced_error_handling()
        self.update_core_modules()
        
        print("✅ Phase 2 completed successfully!")
        print("\nNext steps:")
        print("- Run: uv run python -m app")
        print("- Test new provider strategy pattern")
        print("- Verify enhanced error handling")
        
    def create_backup(self):
        """Create backup of current state"""
        print("📦 Creating Phase 2 backup...")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup key files that will be modified
        backup_items = ["app/__init__.py", "core/api_services.py"]
        
        for file_path in backup_items:
            src = self.root / file_path
            if src.exists():
                dst = self.backup_dir / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        
        # Backup services directory if it exists
        services_src = self.root / "services"
        if services_src.exists():
            services_dst = self.backup_dir / "services"
            shutil.copytree(services_src, services_dst, dirs_exist_ok=True)
    
    def create_strategy_patterns(self):
        """Create strategy pattern for AI providers"""
        print("🎯 Creating AI Provider Strategy Pattern...")
        
        # Base provider interface
        provider_interface = '''"""Base provider interface for strategy pattern"""
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
'''
        
        provider_file = self.root / "core/providers/base.py"
        provider_file.parent.mkdir(parents=True, exist_ok=True)
        provider_file.write_text(provider_interface)
        
        # OpenAI provider implementation
        openai_provider = '''"""OpenAI provider implementation"""
import os
from typing import List, Dict, Any
import openai
from .base import AIProviderInterface, ChatRequest, ChatResponse, ChatMessage


class OpenAIProvider(AIProviderInterface):
    """OpenAI API provider implementation"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self._models = [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]
    
    @property
    def name(self) -> str:
        return "openai"
    
    def get_models(self) -> List[str]:
        return self._models
    
    def is_available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))
    
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using OpenAI API"""
        try:
            messages = [
                {"role": msg.role, "content": msg.content} 
                for msg in request.messages
            ]
            
            response = self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            return ChatResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                provider=self.name
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
'''
        
        openai_file = self.root / "core/providers/openai_provider.py"
        openai_file.write_text(openai_provider)
        
        # Anthropic provider implementation
        anthropic_provider = '''"""Anthropic provider implementation"""
import os
from typing import List, Dict, Any
import anthropic
from .base import AIProviderInterface, ChatRequest, ChatResponse, ChatMessage


class AnthropicProvider(AIProviderInterface):
    """Anthropic Claude API provider implementation"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )
        self._models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229"
        ]
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    def get_models(self) -> List[str]:
        return self._models
    
    def is_available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Process chat completion using Anthropic API"""
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
                messages=messages
            )
            
            return ChatResponse(
                content=response.content[0].text,
                model=request.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                provider=self.name
            )
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
'''
        
        anthropic_file = self.root / "core/providers/anthropic_provider.py"
        anthropic_file.write_text(anthropic_provider)
        
        # Provider factory
        provider_factory = '''"""Provider factory for managing AI providers"""
from typing import Dict, List, Optional
from .base import AIProviderInterface
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


class ProviderFactory:
    """Factory for creating and managing AI providers"""
    
    def __init__(self):
        self._providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        providers = [
            OpenAIProvider(),
            AnthropicProvider(),
        ]
        
        for provider in providers:
            if provider.is_available():
                self._providers[provider.name] = provider
    
    def get_provider(self, name: str) -> Optional[AIProviderInterface]:
        """Get provider by name"""
        return self._providers.get(name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self._providers.keys())
    
    def get_models_for_provider(self, provider_name: str) -> List[str]:
        """Get models for specific provider"""
        provider = self.get_provider(provider_name)
        return provider.get_models() if provider else []
    
    def get_all_models(self) -> Dict[str, List[str]]:
        """Get all models grouped by provider"""
        return {
            name: provider.get_models() 
            for name, provider in self._providers.items()
        }
'''
        
        factory_file = self.root / "core/providers/factory.py"
        factory_file.write_text(provider_factory)
        
        # Provider __init__.py
        provider_init = '''"""AI Provider module initialization"""
from .base import AIProviderInterface, ChatRequest, ChatResponse, ChatMessage
from .factory import ProviderFactory
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

__all__ = [
    "AIProviderInterface",
    "ChatRequest", 
    "ChatResponse",
    "ChatMessage",
    "ProviderFactory",
    "OpenAIProvider",
    "AnthropicProvider"
]
'''
        
        init_file = self.root / "core/providers/__init__.py"
        init_file.write_text(provider_init)
    
    def create_service_layer(self):
        """Create service layer with dependency injection"""
        print("🎯 Creating Service Layer...")
        
        # Chat service
        chat_service = '''"""Chat service with business logic"""
from typing import List, Dict, Any, Optional
from core.providers import ProviderFactory, ChatRequest, ChatMessage, ChatResponse
from core.validation import ChatRequestValidator
from core.context import ContextManager


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self, provider_factory: ProviderFactory, context_manager: ContextManager):
        self.provider_factory = provider_factory
        self.context_manager = context_manager
        self.validator = ChatRequestValidator()
    
    def process_chat_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
                max_tokens=data.get("max_tokens")
            )
            
            # Process request
            response = provider.chat_completion(chat_request)
            
            return {
                "success": True,
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": provider_name if 'provider_name' in locals() else "unknown"
            }
    
    def _build_messages(self, data: Dict[str, Any]) -> List[ChatMessage]:
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
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return self.provider_factory.get_available_providers()
    
    def get_models_for_provider(self, provider: str) -> List[str]:
        """Get models for specific provider"""
        return self.provider_factory.get_models_for_provider(provider)
'''
        
        service_file = self.root / "core/services/chat_service.py" 
        service_file.parent.mkdir(parents=True, exist_ok=True)
        service_file.write_text(chat_service)
        
        # Service container for dependency injection
        service_container = '''"""Service container for dependency injection"""
from typing import Dict, Any, TypeVar, Type, Optional
from core.providers import ProviderFactory
from core.context import ContextManager
from .chat_service import ChatService


T = TypeVar('T')


class ServiceContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._initialize_core_services()
    
    def _initialize_core_services(self):
        """Initialize core services"""
        # Register factory functions
        self.register("provider_factory", lambda: ProviderFactory())
        self.register("context_manager", lambda: ContextManager())
        self.register("chat_service", lambda: ChatService(
            self.get("provider_factory"),
            self.get("context_manager")
        ))
    
    def register(self, name: str, factory_func):
        """Register a service factory function"""
        self._services[name] = factory_func
    
    def get(self, name: str) -> Any:
        """Get service instance (singleton pattern)"""
        if name not in self._singletons:
            if name not in self._services:
                raise ValueError(f"Service {name} not registered")
            self._singletons[name] = self._services[name]()
        return self._singletons[name]
    
    def clear(self):
        """Clear all singleton instances"""
        self._singletons.clear()


# Global service container instance
container = ServiceContainer()


def get_service(name: str) -> Any:
    """Get service from global container"""
    return container.get(name)
'''
        
        container_file = self.root / "core/services/container.py"
        container_file.write_text(service_container)
        
        # Services __init__.py
        services_init = '''"""Services module initialization"""
from .chat_service import ChatService
from .container import ServiceContainer, get_service

__all__ = ["ChatService", "ServiceContainer", "get_service"]
'''
        
        services_init_file = self.root / "core/services/__init__.py"
        services_init_file.write_text(services_init)
    
    def create_repository_layer(self):
        """Create repository pattern for data access"""
        print("🎯 Creating Repository Layer...")
        
        # Base repository interface
        base_repo = '''"""Base repository interface"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseRepository(ABC):
    """Abstract base repository"""
    
    @abstractmethod
    def save(self, data: Dict[str, Any]) -> str:
        """Save data and return ID"""
        pass
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find by ID"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Dict[str, Any]]:
        """Find all records"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete by ID"""
        pass
'''
        
        repo_file = self.root / "core/repository/base.py"
        repo_file.parent.mkdir(parents=True, exist_ok=True)
        repo_file.write_text(base_repo)
        
        # Chat history repository
        chat_repo = '''"""Chat history repository implementation"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import BaseRepository


class ChatHistoryRepository(BaseRepository):
    """Repository for chat history management"""
    
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    model TEXT,
                    provider TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                )
            """)
    
    def save(self, data: Dict[str, Any]) -> str:
        """Save chat session"""
        session_id = data.get("id", self._generate_id())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO chat_sessions 
                (id, title, metadata, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                data.get("title", "New Chat"),
                json.dumps(data.get("metadata", {})),
                datetime.now()
            ))
        
        return session_id
    
    def save_message(self, session_id: str, message: Dict[str, Any]) -> str:
        """Save individual message"""
        message_id = self._generate_id()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO chat_messages
                (id, session_id, role, content, model, provider)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                session_id,
                message["role"],
                message["content"],
                message.get("model", ""),
                message.get("provider", "")
            ))
        
        return message_id
    
    def find_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find chat session by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get session
            session = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ?", 
                (session_id,)
            ).fetchone()
            
            if not session:
                return None
            
            # Get messages
            messages = conn.execute("""
                SELECT role, content, model, provider, created_at
                FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY created_at
            """, (session_id,)).fetchall()
            
            return {
                "id": session["id"],
                "title": session["title"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "metadata": json.loads(session["metadata"]),
                "messages": [dict(msg) for msg in messages]
            }
    
    def find_all(self) -> List[Dict[str, Any]]:
        """Find all chat sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sessions = conn.execute("""
                SELECT id, title, created_at, updated_at
                FROM chat_sessions 
                ORDER BY updated_at DESC
            """).fetchall()
            
            return [dict(session) for session in sessions]
    
    def delete(self, session_id: str) -> bool:
        """Delete chat session and its messages"""
        with sqlite3.connect(self.db_path) as conn:
            # Delete messages first
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            # Delete session
            result = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return result.rowcount > 0
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
'''
        
        chat_repo_file = self.root / "core/repository/chat_repository.py"
        chat_repo_file.write_text(chat_repo)
        
        # Repository __init__.py
        repo_init = '''"""Repository module initialization"""
from .base import BaseRepository
from .chat_repository import ChatHistoryRepository

__all__ = ["BaseRepository", "ChatHistoryRepository"]
'''
        
        repo_init_file = self.root / "core/repository/__init__.py"
        repo_init_file.write_text(repo_init)
    
    def create_validation_layer(self):
        """Create validation layer with Pydantic"""
        print("🎯 Creating Validation Layer...")
        
        validation_code = '''"""Request validation using Pydantic"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass


class ChatMessageModel(BaseModel):
    """Chat message validation model"""
    role: str = Field(..., regex=r"^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=50000)


class ChatRequestModel(BaseModel):
    """Chat request validation model"""
    message: Optional[str] = Field(None, max_length=50000)
    provider: str = Field(default="openai", regex=r"^[a-zA-Z0-9_-]+$")
    model: str = Field(default="", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0, le=100000)
    persona: Optional[str] = Field(None, max_length=10000)
    history: List[ChatMessageModel] = Field(default_factory=list)
    
    @validator('history')
    def validate_history_length(cls, v):
        if len(v) > 100:  # Reasonable limit
            raise ValueError("Chat history too long")
        return v


@dataclass
class ValidationResult:
    """Validation result container"""
    is_valid: bool
    errors: List[str]
    data: Optional[Dict[str, Any]] = None


class ChatRequestValidator:
    """Validator for chat requests"""
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate chat request data"""
        try:
            model = ChatRequestModel(**data)
            return ValidationResult(
                is_valid=True,
                errors=[],
                data=model.dict()
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)]
            )


class FileUploadValidator:
    """Validator for file uploads"""
    
    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'xlsx', 'csv', 'txt', 'md',
        'png', 'jpg', 'jpeg', 'gif'
    }
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    
    def validate_file(self, filename: str, file_size: int) -> ValidationResult:
        """Validate uploaded file"""
        errors = []
        
        # Check extension
        if not self._allowed_file(filename):
            errors.append(f"File type not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}")
        
        # Check size
        if file_size > self.MAX_FILE_SIZE:
            errors.append(f"File too large. Max size: {self.MAX_FILE_SIZE // (1024*1024)}MB")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
'''
        
        validation_file = self.root / "core/validation.py"
        validation_file.write_text(validation_code)
    
    def create_enhanced_error_handling(self):
        """Create enhanced error handling system"""
        print("🎯 Creating Enhanced Error Handling...")
        
        error_handling = '''"""Enhanced error handling system"""
import logging
import traceback
from typing import Dict, Any, Optional
from functools import wraps
from flask import jsonify


class APIError(Exception):
    """Base API exception"""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationError(APIError):
    """Validation error"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 400, details)


class ProviderError(APIError):
    """AI Provider error"""
    
    def __init__(self, message: str, provider: str, details: Optional[Dict] = None):
        super().__init__(message, 503, details)
        self.provider = provider


class RateLimitError(APIError):
    """Rate limit error"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429)


class ErrorHandler:
    """Centralized error handling"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_api_error(self, error: APIError) -> Dict[str, Any]:
        """Handle API errors"""
        self.logger.error(f"API Error: {error.message}", extra=error.details)
        
        return {
            "success": False,
            "error": error.message,
            "status_code": error.status_code,
            "details": error.details
        }
    
    def handle_unexpected_error(self, error: Exception) -> Dict[str, Any]:
        """Handle unexpected errors"""
        self.logger.exception("Unexpected error occurred")
        
        return {
            "success": False,
            "error": "An unexpected error occurred",
            "status_code": 500,
            "details": {
                "type": type(error).__name__,
                "traceback": traceback.format_exc() if self.logger.level <= logging.DEBUG else None
            }
        }


def handle_errors(func):
    """Decorator for consistent error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            error_handler = ErrorHandler()
            return jsonify(error_handler.handle_api_error(e)), e.status_code
        except Exception as e:
            error_handler = ErrorHandler()
            return jsonify(error_handler.handle_unexpected_error(e)), 500
    return wrapper


def setup_logging(app):
    """Setup application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    
    # Set Flask logger level
    app.logger.setLevel(logging.INFO)
'''
        
        error_file = self.root / "core/errors.py"
        error_file.write_text(error_handling)
    
    def update_core_modules(self):
        """Update core modules to use new architecture"""
        print("🎯 Updating Core Modules...")
        
        # Update context manager
        context_manager = '''"""Enhanced context manager for document processing"""
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


class ContextManager:
    """Manages document context and retrieval"""
    
    def __init__(self, db_path: str = "documents.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize context database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def add_document(self, filename: str, content: str, metadata: Dict[str, Any] = None):
        """Add document to context"""
        doc_id = self._generate_id()
        metadata = metadata or {}
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO documents (id, filename, content, metadata)
                VALUES (?, ?, ?, ?)
            """, (doc_id, filename, content, json.dumps(metadata)))
        
        return doc_id
    
    def get_relevant_context(self, query: str, limit: int = 3) -> Optional[str]:
        """Get relevant context for query"""
        with sqlite3.connect(self.db_path) as conn:
            # Simple text search - could be enhanced with vector similarity
            docs = conn.execute("""
                SELECT filename, content FROM documents
                WHERE content LIKE ? 
                ORDER BY created_at DESC
                LIMIT ?
            """, (f"%{query}%", limit)).fetchall()
            
            if not docs:
                return None
            
            context_parts = []
            for filename, content in docs:
                # Take first 500 chars of relevant content
                snippet = content[:500] + "..." if len(content) > 500 else content
                context_parts.append(f"From {filename}: {snippet}")
            
            return "\\n\\n".join(context_parts)
    
    def has_context(self) -> bool:
        """Check if any documents are available"""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            return count > 0
    
    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid
        return str(uuid.uuid4())
'''
        
        context_file = self.root / "core/context.py"
        context_file.write_text(context_manager)


if __name__ == "__main__":
    refactor = RefactorPhase2()
    refactor.run()
