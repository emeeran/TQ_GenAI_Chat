# TQ GenAI Chat - Refactored & Optimized

A comprehensive multi-provider GenAI chat application with advanced file processing capabilities, built with Flask and supporting 10+ AI providers.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis (optional, for caching)
- uv or pip for dependency management

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd TQ_GenAI_Chat
```

2. Install dependencies:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the application:

```bash
# Using uv
uv run python -m app

# Or using python directly
python -m app
```

## 🏗️ Architecture

### Project Structure

```
TQ_GenAI_Chat/
├── app/                    # Application factory and blueprints
│   ├── api/               # REST API endpoints
│   └── web/               # Web interface routes
├── core/                  # Core business logic
│   ├── providers/         # AI provider implementations
│   ├── services/          # Service layer
│   └── utils/             # Utility functions
├── config/                # Configuration management
├── templates/             # HTML templates
├── static/                # Static assets
└── tests/                 # Test suite
```

### Key Components

- **Multi-Provider Support**: OpenAI, Anthropic, Groq, XAI/Grok, Mistral, and more
- **Advanced File Processing**: PDF, DOCX, CSV, images with vector search
- **Real-time Features**: WebSocket support, streaming responses
- **Performance Optimized**: Caching, async processing, connection pooling
- **Security Hardened**: Input validation, rate limiting, secret management

## 🔧 Configuration

### Environment Variables

```bash
# Core API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key
XAI_API_KEY=your_xai_key

# Optional Configuration
REDIS_URL=redis://localhost:6379/0
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Performance Settings
REQUEST_TIMEOUT=60
CACHE_TTL=300
MAX_RETRIES=3
```

### Provider Configuration

Each AI provider is configured in `core/providers/` with:

- Authentication handling
- Model selection
- Rate limiting
- Error recovery

## 📡 API Reference

### Chat Endpoints

#### POST /api/v1/chat

Send a message to an AI provider.

**Request:**

```json
{
  "message": "Hello, world!",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "context": "optional context"
}
```

**Response:**

```json
{
  "response": "AI response text",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "cached": false
}
```

### File Processing

#### POST /api/v1/files/upload

Upload and process files for chat context.

**Request:** Multipart form with files
**Response:**

```json
{
  "results": [
    {
      "filename": "document.pdf",
      "status": "completed",
      "document_id": "doc_123"
    }
  ]
}
```

### Provider Management

#### GET /api/v1/providers

List available AI providers and their status.

#### GET /api/v1/providers/{provider}/models

Get available models for a specific provider.

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_chat.py
```

### Test Structure

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for API endpoints
- `tests/performance/` - Performance and load tests

## 🔒 Security

### Security Features

- Input validation and sanitization
- Rate limiting (60 requests/minute by default)
- API key encryption and secure storage
- CORS configuration for web interface
- Security headers and CSP

### Security Scanning

```bash
# Run security scan
bandit -r .

# Check for dependency vulnerabilities
safety check
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or using the enhanced deployment script
python deploy_enhanced.py --docker
```

### Production Configuration

- Use environment-specific configuration
- Enable Redis for caching and sessions
- Configure reverse proxy (Nginx)
- Set up SSL/TLS certificates
- Monitor with health checks

## 📊 Performance

### Optimization Features

- Response caching (5-minute TTL)
- Connection pooling for API requests
- Async file processing for large uploads
- Vector search for document context
- Request rate limiting and throttling

### Monitoring

- Built-in performance monitoring
- Health check endpoints
- Detailed error logging
- Request/response timing metrics

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Install development dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `pytest`
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Use Black for code formatting
- Add type hints for new functions
- Write tests for new features
- Keep functions under 50 lines
- Document complex logic with comments

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Create an issue for bugs or feature requests
- Check the [documentation](docs/) for detailed guides
- Review [FAQ](docs/FAQ.md) for common questions

## 🙏 Acknowledgments

- Built with Flask, the lightweight Python web framework
- Integrates with major AI providers for maximum flexibility
- Uses modern Python async/await patterns for performance
- Implements enterprise-grade security and monitoring
