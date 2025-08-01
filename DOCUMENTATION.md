# TQ GenAI Chat - Comprehensive Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage Guide](#usage-guide)
6. [API Documentation](#api-documentation)
7. [Development](#development)
8. [Troubleshooting](#troubleshooting)
9. [Contributing](#contributing)
10. [Changelog](#changelog)

## 🎯 Overview

TQ GenAI Chat (AI Chatpal) is a sophisticated multi-provider AI chat application built with Flask, supporting 10+ AI providers with advanced file processing capabilities. It provides a unified interface for interacting with various AI models while maintaining conversation history and supporting file uploads for context-aware conversations.

### Key Highlights
- **Multi-Provider Support**: OpenAI, Anthropic, Groq, XAI, Mistral, and more
- **Advanced File Processing**: PDF, DOCX, images, spreadsheets with context injection
- **Real-time Chat Interface**: Responsive web UI with dark/light theme
- **Persistent Settings**: Provider and model preferences saved locally
- **Customizable Parameters**: Adjustable temperature and token limits
- **Export/Import**: Save and load conversation history

## ✨ Features

### Core Features
- 🤖 **Multi-AI Provider Support**
  - OpenAI (GPT-4, GPT-4o, O1 series)
  - Anthropic (Claude models)
  - Groq (Fast inference)
  - XAI (Grok models)
  - Mistral, Gemini, DeepSeek, and more

- 📁 **File Processing**
  - PDF documents
  - Word documents (.docx)
  - Excel spreadsheets (.xlsx)
  - Images (PNG, JPG, JPEG)
  - Text files (.txt, .md)
  - CSV files

- 🎨 **User Interface**
  - Responsive design with Bootstrap
  - Dark/Light theme toggle
  - Real-time typing indicators
  - Syntax highlighting for code
  - Copy response functionality

- ⚙️ **Advanced Settings**
  - Temperature control (0-1)
  - Max tokens limit (1K-12K)
  - Custom persona prompts
  - Provider/model persistence

### Technical Features
- 🔄 **Error Recovery**: Smart retry with provider switching
- 💾 **Caching**: Multi-layer response caching
- 🔍 **Search**: Vector-based document search
- 🎙️ **Audio**: Speech-to-text and text-to-speech
- 📊 **Analytics**: Usage tracking and performance monitoring

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Internet connection for API calls

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/emeeran/TQ_GenAI_Chat.git
   cd TQ_GenAI_Chat
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional but recommended)
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   ```
   http://localhost:5000
   ```

### Docker Installation

```bash
# Build and run with Docker
docker-compose up --build
```

### Advanced Setup

For production deployment, refer to the [deployment guide](deployment.md).

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# AI Provider API Keys (at least one required)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GROQ_API_KEY=your_groq_api_key_here
XAI_API_KEY=your_xai_api_key_here

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379

# Optional: Custom settings
MAX_FILE_SIZE=16777216  # 16MB
CACHE_TTL=300  # 5 minutes
REQUEST_TIMEOUT=60  # seconds
```

### Configuration Files

- `config/settings.py`: Performance and connection settings
- `requirements.txt`: Python dependencies
- `pyproject.toml`: Project metadata

## 📖 Usage Guide

### Basic Chat

1. **Select Provider**: Choose from available AI providers (Groq, OpenAI, etc.)
2. **Select Model**: Pick a specific model from the provider
3. **Choose Persona**: Select assistant personality or create custom
4. **Adjust Settings**: Set temperature and max tokens as needed
5. **Start Chatting**: Type your message and press Enter or click send

### File Upload

1. Click the **paperclip icon** next to the input field
2. Select files (PDF, DOCX, images, etc.)
3. Files are processed automatically
4. Context from files is injected into conversations

### Advanced Features

#### Custom Personas
- Select "Custom" from persona dropdown
- Enter your custom system prompt
- Persona applies to subsequent messages

#### Temperature Control
- **0.0**: Deterministic, focused responses
- **0.7**: Balanced creativity and consistency
- **1.0**: Maximum creativity and randomness

#### Max Tokens
- Controls response length
- Range: 1K-12K tokens
- Higher values allow longer responses

#### Voice Features
- **Speech-to-Text**: Click microphone to record
- **Text-to-Speech**: Click speaker icon to hear responses

### Conversation Management

#### Save Conversations
1. Click **Save** button in sidebar
2. Enter a filename
3. Conversation saved to `saved_chats/`

#### Load Conversations
1. Click **Load** button
2. Select from saved conversations
3. Chat history restored

#### Export Options
- **Markdown**: Formatted text export
- **JSON**: Structured data export

## 🔌 API Documentation

### Core Endpoints

#### Chat Endpoint
```http
POST /chat
Content-Type: application/json

{
  "message": "Hello, world!",
  "provider": "openai",
  "model": "gpt-4",
  "persona": "assistant",
  "temperature": 0.7,
  "max_tokens": 4000
}
```

#### File Upload
```http
POST /upload
Content-Type: multipart/form-data

files: [file1, file2, ...]
```

#### Model Management
```http
GET /get_models/{provider}
POST /update_models/{provider}
```

#### Document Search
```http
POST /search_context
Content-Type: application/json

{
  "message": "search query"
}
```

### Response Formats

#### Success Response
```json
{
  "response": {
    "text": "AI response text",
    "metadata": {
      "provider": "openai",
      "model": "gpt-4",
      "response_time": "1.23s"
    }
  }
}
```

#### Error Response
```json
{
  "error": "Error description",
  "code": "ERROR_CODE"
}
```

## 🛠️ Development

### Project Structure

```
TQ_GenAI_Chat/
├── app.py                    # Main Flask application
├── requirements.txt          # Dependencies
├── config/
│   └── settings.py          # Configuration
├── core/                    # Business logic
│   ├── api_services.py     # API client services
│   ├── document_store.py   # Document storage
│   └── file_processor.py   # File processing
├── services/               # Provider implementations
│   ├── file_manager.py    # File management
│   └── xai_service.py     # XAI specific logic
├── static/                # Frontend assets
│   ├── script.js         # JavaScript
│   └── styles.css        # CSS styles
├── templates/             # HTML templates
│   └── index.html        # Main UI
├── scripts/               # Utility scripts
│   ├── cleanup_project.py     # Project cleanup
│   └── dependency_checker.py  # Dependency verification
└── trash2review/          # Deprecated files
```

### Development Workflow

1. **Set up development environment**
   ```bash
   python scripts/dependency_checker.py --verbose
   ```

2. **Run cleanup (optional)**
   ```bash
   python scripts/cleanup_project.py --dry-run
   ```

3. **Start development server**
   ```bash
   python app.py
   ```

4. **Run tests**
   ```bash
   python scripts/test_*.py
   ```

### Adding New Providers

1. **Update API configuration** in `app.py`:
   ```python
   API_CONFIGS['new_provider'] = {
       'endpoint': 'https://api.provider.com/chat',
       'key': os.getenv('PROVIDER_API_KEY'),
       'default': 'model-name',
       'fallback': 'fallback-model'
   }
   ```

2. **Add models** to `MODEL_CONFIGS`
3. **Handle special cases** in `process_chat_request()`
4. **Update frontend** model selection

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and small

## 🔧 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
pip install -r requirements.txt
```

#### API key errors
- Check environment variables
- Verify API key validity
- Check provider-specific requirements

#### File upload failures
- Check file size limits (16MB max)
- Verify file format support
- Check disk space

#### Performance issues
- Enable Redis caching
- Reduce max token limits
- Use faster providers (Groq)

### Debug Mode

Enable verbose logging:
```bash
export FLASK_DEBUG=1
python app.py
```

### Health Check

Check system status:
```bash
curl http://localhost:5000/health
```

### Dependency Check

Verify all dependencies:
```bash
python scripts/dependency_checker.py --verbose --fix
```

## 🤝 Contributing

### Guidelines

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Setup

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Run tests before committing:
   ```bash
   python -m pytest
   ```

### Code Standards

- Write tests for new features
- Maintain backwards compatibility
- Update documentation
- Follow existing code patterns

## 📝 Changelog

### v2.0.0 (Current)
- ✅ Multi-provider AI support (10+ providers)
- ✅ Advanced file processing pipeline
- ✅ Real-time chat interface
- ✅ Persistent settings and preferences
- ✅ Temperature and token controls
- ✅ Copy response functionality
- ✅ Project organization scripts
- ✅ Comprehensive documentation

### v1.0.0
- Basic chat functionality
- OpenAI integration
- File upload support
- Simple web interface

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Flask, Bootstrap, and modern web technologies
- Integrates with multiple AI provider APIs
- Inspired by ChatGPT and Claude interfaces
- Community contributions and feedback

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/emeeran/TQ_GenAI_Chat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/emeeran/TQ_GenAI_Chat/discussions)
- **Documentation**: This comprehensive guide

---

**Made with ❤️ by the TQ GenAI Chat team**
