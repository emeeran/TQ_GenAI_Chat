## TODO: Comprehensive Codebase Refactor, Optimization, and Modernization Plan

```markdown
- [ ] Audit and document all core modules, services, and API routes for clarity and maintainability.
- [ ] Refactor provider integration logic to ensure strict separation of concerns and DRY principles.
- [ ] Optimize async file processing and vector search for scalability (batching, concurrency, error handling).
- [ ] Modernize frontend: migrate to latest JS standards, improve state management, and enhance UX for file uploads and provider switching.
- [ ] Implement robust error handling and retry logic across all provider and file operations.
- [ ] Improve test coverage: add async tests, mock external APIs, and validate Redis/database integration.
- [ ] Review and update Docker, Redis, and Nginx configs for security, performance, and portability.
- [ ] Enhance caching and rate limiting strategies for high-traffic scenarios.
- [ ] Document environment variables, deployment steps, and troubleshooting in README and .env.example.
- [ ] Remove dead code, unused dependencies, and legacy patterns.
- [ ] Validate and optimize SQLite/TF-IDF vector search for large document sets.
- [ ] Ensure all code follows PEP8, type hints, and modern Python idioms.
- [ ] Add health checks, monitoring, and alerting for production reliability.
```
# TQ GenAI Chat - AI Agent Instructions

## Architecture Overview

This is a **multi-provider GenAI chat application** built with Flask, supporting 10+ AI providers (OpenAI, Anthropic, Groq, XAI/Grok, Mistral, etc.) with advanced file processing capabilities.

### Core Components

- **`app.py`**: Main Flask application (1,182 lines) - handles all HTTP routes, provider switching, file uploads
- **`config/settings.py`**: Centralized performance and connection settings (timeouts, cache TTL, rate limits)
- **`core/`**: Business logic modules (API services, document store, file processing)
- **`services/`**: Provider-specific implementations (XAI service, file manager with vector search)
- **`persona.py`**: Pre-defined AI assistant personalities/system prompts

### Critical Architecture Patterns

**Multi-Provider API Abstraction**: Each provider uses `API_CONFIGS` dict pattern:

```python
"openai": {
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "key": os.getenv("OPENAI_API_KEY", ""),
    "default": "gpt-4o-mini",
    "fallback": "gpt-3.5-turbo"
}
```

**Error Recovery Strategy**: Failed requests trigger retry modal allowing users to switch providers/models via `retryLast()` function.

**File Processing Pipeline**: Uses async `FileProcessor.process_file()` → `FileManager.add_document()` → SQLite storage with TF-IDF vector search.

## Development Workflows

### Testing Strategy

- Run: `python deploy_enhanced.py --test` (creates basic test suite if missing)
- Tests use pytest with async support (`@pytest.mark.asyncio`)
- Redis test database: `redis://localhost:6379/1`

### Enhanced Deployment

- Use `deploy_enhanced.py` for full setup automation
- Creates `.env` template, virtual environment, installs dependencies
- Generates Docker configuration with Redis and Nginx
- Health checks via `/health` endpoint

### Key Commands

```bash
# Setup everything
python deploy_enhanced.py --setup

# Run with enhanced deployment
python deploy_enhanced.py --start

# Docker deployment
python deploy_enhanced.py --docker && docker-compose up --build
```

## Provider Integration Patterns

### Adding New AI Providers

1. Add to `API_CONFIGS` in `app.py`
2. Add models to `MODEL_CONFIGS`
3. Handle special cases in `process_chat_request()` (see Anthropic/XAI examples)
4. Update frontend model selection in `static/script.js`

### Request Flow Pattern

```python
@cache_response  # 5-minute TTL caching
@async_response  # ThreadPoolExecutor wrapper
def process_chat_request(data: dict) -> dict:
```

### Rate Limiting

- Global: 60 requests/minute per provider
- Uses `rate_limit_check()` with sliding window
- Exponential backoff on 429 responses

## File Processing System

### Supported Types

- Documents: PDF, DOCX, CSV, XLSX, Markdown
- Images: PNG, JPG, JPEG (metadata extraction only)
- Max size: 16MB per file, 10 files per upload

### Processing Pipeline

```python
# Async processing with status tracking
content = await FileProcessor.process_file(file, filename)
file_manager.add_document(filename, content)  # Vector indexing
```

### Document Search

- TF-IDF vector similarity search in `FileManager`
- Context injection: Search results auto-added to chat prompts
- Relevance scoring with configurable threshold

## Critical Configurations

### Environment Variables (Required)

```bash
OPENAI_API_KEY=...      # Primary provider
GROQ_API_KEY=...        # Fast inference
ANTHROPIC_API_KEY=...   # Claude models
XAI_API_KEY=...         # Grok models
```

### Performance Tuning

- `REQUEST_TIMEOUT=60s` (increased for large responses)
- `CACHE_TTL=300s` (5-minute response caching)
- `MAX_RETRIES=3` with exponential backoff
- Connection pooling via `requests.Session`

### Redis Integration

- Optional but recommended for production
- Used for caching and session management
- Fallback to memory if unavailable

## Frontend Architecture

### Key JavaScript Patterns

- **Debounced messaging**: `sendMessage = debounce(async (message = null, isRetry = false) => {...})`
- **Provider switching**: Dynamic model loading via `/get_models/<provider>`
- **File upload progress**: Real-time status via `/upload/status/<filename>`
- **Retry mechanism**: Modal-based provider/model selection

### State Management

- Chat history in local arrays
- File processing status tracking
- Provider/model selection persistence

## Common Pitfalls & Solutions

1. **API Key Issues**: Check startup logs for key validation, use `.env.example` template
2. **File Upload Failures**: Monitor `/upload/status/<filename>` endpoint for processing errors
3. **Provider Timeouts**: Retry system allows switching to faster providers (Groq)
4. **Memory Issues**: Enable Redis for production deployments
5. **CORS Errors**: Already configured for `/api/*` routes

## Testing Patterns

- Use `with app.test_client() as client:` for route testing
- Mock external APIs in tests (providers can be expensive)
- Test file processing with sample files in `uploads/` directory
- Verify Redis connection separately: `redis-cli ping`
