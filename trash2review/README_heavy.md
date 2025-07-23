# TQ GenAI Chat

A multi-provider GenAI chat application with advanced file processing capabilities.

## Features

- **Multi-Provider Support**: OpenAI, Groq, Anthropic, Mistral, and XAI/Grok
- **Advanced File Processing**: Handle multiple file types including PDF, Word, Excel, Markdown, and images
- **Chat History Management**: Save, export, and reload chat sessions
- **Custom Personas**: Configure different assistant personalities
- **Efficient Document Storage**: SQLite-based document storage with search capabilities
- **Rate Limiting & Caching**: Optimized API usage with built-in rate limiting and response caching

## Project Structure

```
├── ai_models.py           # AI model definitions and configurations
├── app.py                 # Main Flask application
├── config/
│   └── settings.py        # Application configuration settings
├── core/
│   ├── api_services.py    # Unified API client for multiple providers
│   ├── document_store.py  # Document storage and retrieval functionality
│   ├── file_processor.py  # File processing and conversion utilities
│   └── utilities.py       # General utility functions
├── services/
│   ├── file_manager.py    # File management services
│   └── xai_service.py     # XAI/Grok API integration
├── static/                # Static assets (CSS, JavaScript)
├── templates/             # HTML templates
├── uploads/               # File upload directory
└── utils/                 # Legacy utility functions
```

## Setup & Installation

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
pip install -e .
```

4. **Configure API Keys**

Create a `.env` file in the project root with your API keys:

```
OPENAI_API_KEY=your_openai_key_here
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
MISTRAL_API_KEY=your_mistral_key_here
XAI_API_KEY=your_xai_key_here
```

5. **Run the application**

```bash
python app.py
```

The application will be available at http://localhost:5000

## Usage

### Chat Interface

1. Access the web interface at http://localhost:5000
2. Select an AI provider and model
3. Choose a persona for the assistant
4. Type your message or upload files for analysis
5. View and interact with the AI response

### File Processing

The application supports processing of:
- PDFs (`.pdf`)
- Word documents (`.docx`)
- Excel spreadsheets (`.xlsx`)
- CSV files (`.csv`)
- Markdown (`.md`)
- Images (`.jpg`, `.jpeg`, `.png`)

### Chat Management

- **Save Chats**: Save your current chat session
- **Export Chats**: Export conversations as markdown
- **Load Chats**: Reload previous conversations

## Development

### Running Tests

```bash
pytest
```

### Code Style

The project follows PEP 8 style guidelines. Run linting checks with:

```bash
flake8
```

## License

MIT License

## Acknowledgements

- Flask - Web framework
- OpenAI, Groq, Anthropic, Mistral - AI providers
- Bootstrap - UI framework
