# Core Module Documentation

## Overview

The `core/` directory contains the essential business logic modules that power the TQ GenAI Chat application. Each module follows the single responsibility principle and maintains clean interfaces for easy testing and maintenance.

## Module Architecture

```
core/
├── providers.py          # AI provider management (435 lines)
├── chat_handler.py       # Chat processing & context injection (315 lines)
├── models.py             # Model configuration & caching (285 lines)
├── tts.py                # Text-to-speech engine (245 lines)
├── api_services.py       # API utilities (180 lines)
├── document_store.py     # Document storage & search (320 lines)
├── file_processor.py     # File processing pipeline (295 lines)
└── ...
```

## Core Modules

### providers.py - AI Provider Management

**Purpose**: Centralized AI provider management with standardized interfaces

**Key Components**:
- `BaseProvider` (ABC): Abstract base class defining provider interface
- `ProviderConfig` (dataclass): Configuration structure for providers
- `OpenAICompatibleProvider`: Generic provider for OpenAI-compatible APIs
- `AnthropicProvider`: Specialized Anthropic/Claude integration
- `GeminiProvider`: Google Gemini integration
- `CohereProvider`: Cohere API integration

**Usage Example**:
```python
from core.providers import get_provider

provider = get_provider("openai")
response = await provider.chat_completion(
    messages=[{"role": "user", "content": "Hello!"}],
    model="gpt-4o-mini"
)
```

**Key Features**:
- Unified interface across all providers
- Automatic retry logic with exponential backoff
- Request/response validation
- Error handling and graceful degradation
- Connection pooling and session management

### chat_handler.py - Chat Processing

**Purpose**: Centralized chat processing with context injection and response verification

**Key Components**:
- `ChatHandler`: Main class for chat processing
- Context injection from document store
- Parameter validation and sanitization
- Response verification using secondary models

**Usage Example**:
```python
from core.chat_handler import ChatHandler

handler = ChatHandler(provider_manager, file_manager)
response = await handler.process_chat(
    message="Explain the uploaded document",
    provider="groq",
    model="llama-3.3-70b-versatile"
)
```

**Key Features**:
- Automatic context injection from relevant documents
- Smart parameter validation
- Response verification for accuracy
- Persona system integration
- Error recovery and retry mechanisms

### models.py - Model Management

**Purpose**: Model configuration management and intelligent caching

**Key Components**:
- `ModelManager`: Central model configuration management
- `DEFAULT_MODELS`: Comprehensive model definitions
- Intelligent caching with TTL
- Dynamic model discovery

**Usage Example**:
```python
from core.models import ModelManager

model_manager = ModelManager()
models = model_manager.get_models("openai")
await model_manager.update_models("groq")
```

**Key Features**:
- Centralized model definitions
- Automatic model discovery
- Intelligent caching (5-minute TTL)
- Fallback model configuration
- Performance optimization

### tts.py - Text-to-Speech Engine

**Purpose**: Text-to-speech engine abstraction and voice management

**Key Components**:
- `TTSEngine`: Main TTS processing class
- `TTSVoice` (dataclass): Voice configuration structure
- Support for pyttsx3 and gTTS engines
- Voice selection and management

**Usage Example**:
```python
from core.tts import TTSEngine

tts = TTSEngine()
audio_path = await tts.synthesize(
    text="Hello, world!",
    voice_id="en-us-male",
    engine="pyttsx3"
)
```

**Key Features**:
- Multi-engine support (pyttsx3, gTTS)
- Voice selection and customization
- Async processing
- Audio format conversion
- Error handling and fallbacks

## Design Patterns

### Abstract Base Classes
All core modules use ABC patterns for clean interfaces:
- `BaseProvider` for AI providers
- `BaseProcessor` for file processors
- `BaseEngine` for TTS engines

### Dataclasses
Modern Python dataclasses for configuration:
- `ProviderConfig`: Provider settings
- `TTSVoice`: Voice configuration
- `ProcessingResult`: File processing results

### Dependency Injection
Clean dependency management:
```python
class ChatHandler:
    def __init__(self, provider_manager, file_manager):
        self.provider_manager = provider_manager
        self.file_manager = file_manager
```

### Error Handling Strategy
Comprehensive error handling with:
- Specific exception types
- Graceful degradation
- Informative error messages
- Automatic retry logic

## Testing Guidelines

### Unit Testing
Each module has comprehensive unit tests:
```bash
pytest tests/core/test_providers.py -v
pytest tests/core/test_chat_handler.py -v
pytest tests/core/test_models.py -v
pytest tests/core/test_tts.py -v
```

### Mock Patterns
External dependencies are mocked:
```python
@patch('core.providers.requests.Session')
def test_provider_request(mock_session):
    # Test implementation
```

### Test Coverage
Target: >95% coverage for all core modules
```bash
pytest --cov=core --cov-report=html
```

## Performance Considerations

### Connection Pooling
All HTTP clients use connection pooling:
```python
self.session = requests.Session()
# Persistent connections for better performance
```

### Caching Strategy
Multi-level caching:
- Model configurations (5-minute TTL)
- Provider responses (configurable)
- File processing results (persistent)

### Async Processing
Key operations are async:
- File processing
- AI provider requests
- TTS synthesis

## Configuration Management

### Environment Variables
Core modules respect environment settings:
```env
REQUEST_TIMEOUT=60
MAX_RETRIES=3
CACHE_TTL=300
```

### Runtime Configuration
Dynamic configuration through Flask app config:
```python
app.config['PROVIDER_TIMEOUT'] = 30
app.config['ENABLE_CACHING'] = True
```

## Error Recovery

### Retry Logic
Exponential backoff for transient failures:
```python
for attempt in range(max_retries):
    try:
        return await self._make_request(...)
    except TemporaryError:
        await asyncio.sleep(2 ** attempt)
```

### Fallback Providers
Automatic failover to backup providers:
```python
if primary_provider.is_available():
    return await primary_provider.chat_completion(...)
else:
    return await fallback_provider.chat_completion(...)
```

## Extension Points

### Adding New Providers
1. Inherit from `BaseProvider`
2. Implement required methods
3. Register in provider registry
4. Add configuration to settings

### Custom File Processors
1. Inherit from `BaseProcessor`
2. Implement `process_file` method
3. Register with file manager
4. Add MIME type mapping

### TTS Engine Integration
1. Inherit from `BaseEngine`
2. Implement synthesis methods
3. Add to engine registry
4. Configure voice options

## Best Practices

### Code Organization
- Single responsibility per module
- Clear interfaces and contracts
- Minimal external dependencies
- Comprehensive error handling

### Type Safety
Full type annotations for better IDE support:
```python
async def chat_completion(
    self, 
    messages: list[dict], 
    model: str = None
) -> dict:
```

### Documentation
- Docstrings for all public methods
- Type hints for all parameters
- Usage examples in docstrings
- Clear error descriptions

### Testing
- Test all public methods
- Mock external dependencies
- Test error conditions
- Verify type safety

This modular architecture enables:
- **Easy maintenance**: Each module has a clear purpose
- **Simple testing**: Isolated units with clean interfaces
- **Performance optimization**: Targeted improvements per module
- **Extensibility**: Clean extension points for new features
