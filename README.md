# TQ GenAI Chat

A high-performance, multi-provider GenAI chat application with advanced file processing capabilities, built with a modern, scalable architecture.

## 🚀 Features

### Core Capabilities
- **Multi-Provider AI Support**: OpenAI, Anthropic, Groq, Mistral, and XAI/Grok with unified interface
- **Advanced File Processing**: Async pipeline supporting PDF, Word, Excel, CSV, Markdown, and images
- **Intelligent Document Search**: TF-IDF based search with fuzzy matching and relevance scoring
- **Chat History Management**: Save, export, and reload conversations with full metadata
- **Custom Personas**: Configurable assistant personalities with context awareness

### Performance & Scalability
- **Multi-Level Caching**: Memory, file, and optional Redis caching with intelligent invalidation
- **Async Processing**: Non-blocking file processing with progress tracking and cancellation
- **Connection Pooling**: Optimized HTTP client with circuit breaker patterns
- **Performance Monitoring**: Real-time metrics collection and alerting
- **Static Asset Optimization**: Compression, versioning, and lazy loading

### Developer Experience
- **Modular Architecture**: Clean separation of concerns with dependency injection
- **Comprehensive Testing**: Unit, integration, and performance tests with >90% coverage
- **Type Safety**: Full type annotations with mypy compatibility
- **Error Recovery**: Automatic retry logic and graceful degradation
- **Extensive Logging**: Structured logging with configurable levels

## 🏗️ Architecture Overview

The application follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Web Routes    │  │   API Routes    │  │  Static      │ │
│  │   (templates)   │  │   (REST/JSON)   │  │  Assets      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Chat Service  │  │  File Service   │  │  TTS Service │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                     Core Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  AI Providers   │  │ Document Store  │  │ File         │ │
│  │  (OpenAI, etc.) │  │                 │  │ Processor    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Configuration  │  │    Database     │  │   Caching    │ │
│  │                 │  │   (SQLite)      │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
├── app/                           # Flask application factory
│   ├── __init__.py               # App factory and configuration
│   ├── routes/                   # Modular route definitions
│   │   ├── chat.py              # Chat-related endpoints
│   │   ├── files.py             # File upload/management
│   │   ├── api.py               # REST API endpoints
│   │   └── tts.py               # Text-to-speech routes
│   └── services/                 # Business logic layer
│       ├── chat_service.py      # Chat orchestration
│       ├── file_service.py      # File management
│       └── tts_service.py       # Text-to-speech processing
├── core/                         # Core business logic
│   ├── providers/               # AI provider implementations
│   │   ├── base.py             # Base provider interface
│   │   ├── openai.py           # OpenAI integration
│   │   ├── anthropic.py        # Anthropic integration
│   │   ├── groq.py             # Groq integration
│   │   └── registry.py         # Provider registry
│   ├── file_processing/         # File processing pipeline
│   │   ├── pipeline.py         # Main processing pipeline
│   │   ├── processors/         # File type processors
│   │   ├── middleware.py       # Processing middleware
│   │   └── models.py           # Data models
│   ├── database/               # Database layer
│   │   ├── connection_pool.py  # Connection management
│   │   └── migrations.py       # Schema migrations
│   ├── document_store.py       # Document storage
│   ├── search_engine.py        # Search functionality
│   ├── cache.py                # Multi-level caching
│   └── http_client.py          # Async HTTP client
├── config/                      # Configuration management
│   ├── settings.py             # Application settings
│   └── models.py               # Model configurations
├── utils/                       # Utility modules
│   ├── logging.py              # Centralized logging
│   ├── validation.py           # Input validation
│   ├── decorators.py           # Common decorators
│   ├── performance_monitor.py  # Performance monitoring
│   ├── cache_warming.py        # Cache warming strategies
│   └── static_assets.py        # Asset optimization
├── tests/                       # Comprehensive test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── performance/            # Performance benchmarks
├── templates/                   # Jinja2 templates
├── static/                      # Static assets
└── main.py                     # Application entry point
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (3.10+ recommended)
- 4GB+ RAM for optimal performance
- Optional: Redis for distributed caching

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/username/TQ_GenAI_Chat.git
cd TQ_GenAI_Chat
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the project root:

```bash
# Required: At least one AI provider API key
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GROQ_API_KEY=your_groq_key_here
MISTRAL_API_KEY=your_mistral_key_here
XAI_API_KEY=your_xai_key_here

# Optional: Application configuration
FLASK_ENV=development
LOG_LEVEL=INFO
MAX_FILE_SIZE=64MB
CACHE_TYPE=memory  # memory, file, redis
REDIS_URL=redis://localhost:6379/0  # if using Redis

# Optional: Performance tuning
MAX_WORKERS=4
REQUEST_TIMEOUT=30
CACHE_TTL=3600
```

5. **Initialize the application**
```bash
python -c "from app import create_app; app = create_app(); app.app_context().push()"
```

6. **Run the application**
```bash
# Development mode
python main.py

# Production mode with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

The application will be available at http://localhost:5000

### Docker Setup (Alternative)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or with Docker directly
docker build -t tq-genai-chat .
docker run -p 5000:5000 --env-file .env tq-genai-chat
```

## 📖 Usage Guide

### Web Interface

1. **Access the application** at http://localhost:5000
2. **Select AI provider and model** from the dropdown menus
3. **Choose a persona** to customize the assistant's behavior
4. **Start chatting** by typing messages or uploading files
5. **Manage conversations** with save, load, and export features

### File Processing

The application supports intelligent processing of multiple file types:

| File Type | Extensions | Features |
|-----------|------------|----------|
| **PDF** | `.pdf` | Text extraction, OCR fallback, metadata preservation |
| **Word** | `.docx` | Full document parsing, formatting preservation |
| **Excel** | `.xlsx`, `.xls` | Sheet processing, formula evaluation, data extraction |
| **CSV** | `.csv` | Automatic delimiter detection, data type inference |
| **Text** | `.txt`, `.md` | Encoding detection, markdown parsing |
| **Images** | `.jpg`, `.png`, `.gif` | OCR text extraction, metadata analysis |

#### File Upload Process
1. **Drag and drop** files or click to browse
2. **Monitor progress** with real-time processing status
3. **Search content** using the intelligent search engine
4. **Reference files** in chat conversations automatically

### API Usage

#### REST API Endpoints

```bash
# Health check
GET /api/health

# Get available models
GET /api/models
GET /api/models?provider=openai

# Chat completion
POST /api/chat
{
  "message": "Hello, world!",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 150
}

# File upload
POST /api/files/upload
Content-Type: multipart/form-data

# Document search
POST /api/search
{
  "query": "artificial intelligence",
  "limit": 10
}

# Performance metrics
GET /api/performance/summary
GET /api/cache/metrics
```

#### Python SDK Example

```python
import requests

# Initialize client
base_url = "http://localhost:5000"
headers = {"Content-Type": "application/json"}

# Send chat message
response = requests.post(f"{base_url}/api/chat", 
    json={
        "message": "Explain quantum computing",
        "provider": "openai",
        "model": "gpt-4o-mini"
    },
    headers=headers
)

result = response.json()
print(result["response"])
```

### Advanced Features

#### Custom Personas
Create custom assistant personalities by modifying `persona.py`:

```python
PERSONAS = {
    "technical_expert": """You are a technical expert with deep knowledge 
    in software engineering, AI, and system architecture. Provide detailed, 
    accurate technical explanations with code examples when appropriate.""",
    
    "creative_writer": """You are a creative writing assistant. Help users 
    craft compelling stories, improve their writing style, and provide 
    creative inspiration."""
}
```

#### Performance Monitoring
Access real-time performance metrics:
- **Response times** for all endpoints
- **Memory and CPU usage** tracking
- **Cache hit rates** and efficiency metrics
- **Error rates** and failure analysis

Visit `/api/performance/dashboard` for the web interface.

#### Caching Strategies
The application uses intelligent multi-level caching:

```python
# Warm specific cache strategies
POST /api/cache/warm
{
  "strategy": "common_requests"  # or "popular_files", "recent_chats"
}

# Invalidate cache by tags
POST /api/cache/invalidate
{
  "tags": ["files", "documents"]
}
```

## 🛠️ Development

### Development Setup

1. **Install development dependencies**
```bash
pip install -r requirements-dev.txt
```

2. **Set up pre-commit hooks**
```bash
pre-commit install
```

3. **Run in development mode**
```bash
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
python main.py
```

### Testing

The project includes comprehensive testing at multiple levels:

#### Unit Tests
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=core --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_providers.py -v
```

#### Integration Tests
```bash
# Run integration tests
pytest tests/integration/ -v

# Test specific workflow
pytest tests/integration/test_chat_workflow.py::TestChatWorkflow::test_complete_chat_flow_openai -v
```

#### Performance Tests
```bash
# Run performance benchmarks
python tests/performance/run_benchmarks.py

# Quick performance check
python tests/performance/run_benchmarks.py --quick

# Custom test patterns
python tests/performance/run_benchmarks.py --tests "tests/performance/test_load_testing.py::TestChatPerformance"
```

### Code Quality

#### Linting and Formatting
```bash
# Format code with black
black .

# Sort imports
isort .

# Lint with flake8
flake8 .

# Type checking with mypy
mypy core/ app/

# Security scanning
bandit -r core/ app/
```

#### Code Coverage
```bash
# Generate coverage report
pytest --cov=core --cov=app --cov-report=html --cov-report=term

# View coverage in browser
open htmlcov/index.html
```

### Architecture Guidelines

#### Adding New AI Providers
1. **Create provider class** extending `BaseProvider`
2. **Implement required methods**: `generate_completion`, `get_available_models`
3. **Add configuration** to `config/settings.py`
4. **Register provider** in `core/providers/registry.py`
5. **Add comprehensive tests**

Example:
```python
# core/providers/new_provider.py
from .base import BaseProvider

class NewProvider(BaseProvider):
    @property
    def provider_name(self) -> str:
        return "new_provider"
    
    async def generate_completion(self, messages, model, **kwargs):
        # Implementation here
        pass
```

#### Adding File Processors
1. **Create processor class** extending `BaseFileProcessor`
2. **Define capabilities** and supported extensions
3. **Implement processing logic** with error handling
4. **Register processor** in the pipeline
5. **Add unit and integration tests**

#### Performance Considerations
- **Use async/await** for I/O operations
- **Implement caching** for expensive operations
- **Add progress tracking** for long-running tasks
- **Monitor memory usage** and implement cleanup
- **Use connection pooling** for external APIs

### Debugging

#### Logging Configuration
```python
# Enable debug logging
import logging
logging.getLogger('core').setLevel(logging.DEBUG)
logging.getLogger('app').setLevel(logging.DEBUG)
```

#### Performance Profiling
```bash
# Profile application startup
python -m cProfile -o profile.stats main.py

# Analyze profile
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# Memory profiling
python -m memory_profiler main.py
```

#### Database Debugging
```bash
# View SQLite database
sqlite3 documents.db ".tables"
sqlite3 documents.db "SELECT * FROM documents LIMIT 5;"

# Enable SQL query logging
export LOG_LEVEL=DEBUG
```

### Deployment

#### Production Configuration
```bash
# Set production environment
export FLASK_ENV=production
export LOG_LEVEL=WARNING
export CACHE_TYPE=redis
export REDIS_URL=redis://redis-server:6379/0

# Use production WSGI server
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 "app:create_app()"
```

#### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
```

#### Health Checks
```bash
# Application health
curl http://localhost:5000/api/health

# Performance metrics
curl http://localhost:5000/api/performance/summary

# Cache status
curl http://localhost:5000/api/cache/metrics
```

### Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the coding standards
4. **Add tests** for new functionality
5. **Run the test suite**: `pytest`
6. **Commit your changes**: `git commit -m 'Add amazing feature'`
7. **Push to the branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

#### Pull Request Guidelines
- Include a clear description of changes
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass
- Follow the existing code style
- Keep commits atomic and well-documented

## 📊 Performance Benchmarks

### Typical Performance Metrics
- **Chat Response Time**: < 2s average, < 5s 95th percentile
- **File Processing**: 1MB/s for text files, 500KB/s for PDFs
- **Search Queries**: < 100ms average, > 50 QPS
- **Cache Hit Rate**: > 80% for common operations
- **Memory Usage**: < 500MB baseline, < 2GB under load

### Optimization Tips
- **Enable Redis caching** for production deployments
- **Use SSD storage** for better file I/O performance
- **Configure connection pooling** for high-concurrency scenarios
- **Monitor memory usage** and tune garbage collection
- **Implement request queuing** for rate-limited APIs

## 🔧 Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Flask environment mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_FILE_SIZE` | `64MB` | Maximum file upload size |
| `CACHE_TYPE` | `memory` | Cache backend (memory, file, redis) |
| `REDIS_URL` | `None` | Redis connection URL |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `MAX_WORKERS` | `4` | Maximum worker processes |
| `CACHE_TTL` | `3600` | Default cache TTL in seconds |

### Provider Configuration
Each AI provider can be configured in `config/settings.py`:

```python
API_CONFIGS = {
    'openai': {
        'key': os.getenv('OPENAI_API_KEY'),
        'endpoint': 'https://api.openai.com/v1',
        'default': 'gpt-4o-mini',
        'rate_limit': 60,  # requests per minute
        'timeout': 30
    }
}
```

## 🐛 Troubleshooting

### Common Issues

#### "Provider not configured" Error
- Ensure API keys are set in `.env` file
- Check that the provider is enabled in configuration
- Verify API key format and permissions

#### File Processing Failures
- Check file size limits (`MAX_FILE_SIZE`)
- Verify file format is supported
- Review processing logs for specific errors
- Ensure sufficient disk space for temporary files

#### Performance Issues
- Monitor memory usage with `/api/performance/summary`
- Check cache hit rates with `/api/cache/metrics`
- Review slow query logs in debug mode
- Consider enabling Redis for better caching

#### Database Errors
- Check SQLite file permissions
- Verify database schema with migrations
- Monitor disk space for database growth
- Consider database cleanup for old records

### Getting Help
- Check the [Issues](https://github.com/username/TQ_GenAI_Chat/issues) page
- Review the [Wiki](https://github.com/username/TQ_GenAI_Chat/wiki) for detailed guides
- Join our [Discord](https://discord.gg/example) for community support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

### Core Technologies
- **[Flask](https://flask.palletsprojects.com/)** - Web framework
- **[aiohttp](https://docs.aiohttp.org/)** - Async HTTP client
- **[SQLite](https://www.sqlite.org/)** - Database engine
- **[Redis](https://redis.io/)** - Caching and session storage

### AI Providers
- **[OpenAI](https://openai.com/)** - GPT models and API
- **[Anthropic](https://www.anthropic.com/)** - Claude models
- **[Groq](https://groq.com/)** - High-performance inference
- **[Mistral AI](https://mistral.ai/)** - Open-source models
- **[xAI](https://x.ai/)** - Grok models

### Development Tools
- **[pytest](https://pytest.org/)** - Testing framework
- **[black](https://black.readthedocs.io/)** - Code formatting
- **[mypy](https://mypy.readthedocs.io/)** - Type checking
- **[pre-commit](https://pre-commit.com/)** - Git hooks

### Special Thanks
- Contributors and community members
- Open-source projects that made this possible
- Beta testers and early adopters

---

**Built with ❤️ by the TQ GenAI Chat team**
