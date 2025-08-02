# API Documentation

## Overview

The TQ GenAI Chat API provides RESTful endpoints for interacting with multiple AI providers, managing files, and handling text-to-speech operations. All endpoints return JSON responses and follow consistent error handling patterns.

## Base URL

```
http://localhost:5000  # Development
https://your-domain.com  # Production
```

## Authentication

Currently, the API uses API keys configured server-side through environment variables. No client-side authentication is required for basic operations.

## Content Types

- **Request**: `application/json` or `multipart/form-data` (for file uploads)
- **Response**: `application/json`
- **Audio**: `audio/mpeg`, `audio/wav`, `audio/ogg`

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "error_code": "PROVIDER_ERROR",
  "timestamp": "2025-01-27T10:30:00Z"
}
```

## Core Endpoints

### 1. Chat Completion

Send a message to an AI provider and receive a response.

**Endpoint**: `POST /chat`

**Request Body**:
```json
{
  "message": "What is machine learning?",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "persona": "helpful_assistant",
  "temperature": 0.7,
  "max_tokens": 4000,
  "include_verification": true,
  "include_context": true
}
```

**Parameters**:
- `message` (string, required): The user's message
- `provider` (string, optional): AI provider name (default: "groq")
- `model` (string, optional): Model name (uses provider default if not specified)
- `persona` (string, optional): Persona/system prompt (default: "helpful_assistant")
- `temperature` (float, optional): Response randomness 0.0-1.0 (default: 0.7)
- `max_tokens` (integer, optional): Maximum response length (default: 4000)
- `include_verification` (boolean, optional): Enable response verification (default: true)
- `include_context` (boolean, optional): Include document context (default: true)

**Response**:
```json
{
  "success": true,
  "data": {
    "response": "Machine learning is a subset of artificial intelligence...",
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "tokens_used": 256,
    "processing_time": 1.2,
    "verification": {
      "verified": true,
      "confidence": 0.95,
      "verifier_model": "gemini-1.5-flash"
    },
    "context_used": [
      {
        "filename": "ml_basics.pdf",
        "relevance_score": 0.89,
        "excerpt": "Machine learning enables computers to learn..."
      }
    ],
    "persona_applied": "helpful_assistant"
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

**Error Codes**:
- `INVALID_PROVIDER`: Unknown provider specified
- `INVALID_MODEL`: Model not available for provider
- `PROVIDER_ERROR`: API error from AI provider
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `CONTEXT_TOO_LARGE`: Message + context exceeds model limits

### 2. File Upload

Upload and process documents for context injection.

**Endpoint**: `POST /upload`

**Request**: `multipart/form-data`
```
files: [file1.pdf, file2.docx, ...]
```

**Supported File Types**:
- **Documents**: PDF, DOCX, CSV, XLSX, TXT, MD
- **Images**: PNG, JPG, JPEG (metadata extraction only)

**File Limits**:
- Maximum file size: 16MB
- Maximum files per request: 10
- Total request size: 160MB

**Response**:
```json
{
  "success": true,
  "data": {
    "uploaded_files": [
      {
        "filename": "document.pdf",
        "size": 1024000,
        "type": "application/pdf",
        "status": "processed",
        "pages": 15,
        "word_count": 3500,
        "processing_time": 2.1
      }
    ],
    "total_files": 1,
    "total_size": 1024000,
    "processing_status": "completed"
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### 3. File Upload Status

Check the processing status of uploaded files.

**Endpoint**: `GET /upload/status/<filename>`

**Response**:
```json
{
  "success": true,
  "data": {
    "filename": "document.pdf",
    "status": "processing",
    "progress": 65,
    "estimated_completion": "2025-01-27T10:32:00Z",
    "error": null
  }
}
```

**Status Values**:
- `queued`: File is queued for processing
- `processing`: Currently being processed
- `completed`: Processing finished successfully
- `failed`: Processing failed with error

### 4. Text-to-Speech

Convert text to speech audio.

**Endpoint**: `POST /tts`

**Request Body**:
```json
{
  "text": "Hello, this is a test message",
  "engine": "pyttsx3",
  "voice": "en-us-male",
  "speed": 200,
  "format": "mp3"
}
```

**Parameters**:
- `text` (string, required): Text to convert to speech
- `engine` (string, optional): TTS engine ("pyttsx3" or "gtts", default: "pyttsx3")
- `voice` (string, optional): Voice identifier (default: system default)
- `speed` (integer, optional): Speech speed in WPM (default: 200)
- `format` (string, optional): Audio format ("mp3", "wav", "ogg", default: "mp3")

**Response**:
```json
{
  "success": true,
  "data": {
    "audio_url": "/static/audio/tts_20250127_103000.mp3",
    "duration": 3.2,
    "engine_used": "pyttsx3",
    "voice_used": "en-us-male",
    "text_length": 28
  }
}
```

### 5. Available Voices

Get list of available TTS voices.

**Endpoint**: `GET /tts/voices`

**Response**:
```json
{
  "success": true,
  "data": {
    "pyttsx3": [
      {
        "id": "en-us-male",
        "name": "Microsoft David",
        "language": "en-US",
        "gender": "male"
      },
      {
        "id": "en-us-female",
        "name": "Microsoft Zira", 
        "language": "en-US",
        "gender": "female"
      }
    ],
    "gtts": [
      {
        "id": "en",
        "name": "English",
        "language": "en",
        "region": "global"
      }
    ]
  }
}
```

## Provider Management

### 6. List Available Providers

Get all configured AI providers and their status.

**Endpoint**: `GET /providers`

**Response**:
```json
{
  "success": true,
  "data": {
    "providers": [
      {
        "name": "openai",
        "status": "active",
        "models_available": 12,
        "default_model": "gpt-4o-mini",
        "rate_limit": "60/minute",
        "cost": "paid"
      },
      {
        "name": "groq",
        "status": "active", 
        "models_available": 8,
        "default_model": "llama-3.3-70b-versatile",
        "rate_limit": "unlimited",
        "cost": "free"
      }
    ]
  }
}
```

### 7. Get Provider Models

List available models for a specific provider.

**Endpoint**: `GET /get_models/<provider>`

**Response**:
```json
{
  "success": true,
  "data": {
    "provider": "openai",
    "models": [
      {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "context_length": 128000,
        "cost_per_1k_tokens": {
          "input": 0.0025,
          "output": 0.01
        },
        "capabilities": ["text", "vision", "function_calling"]
      },
      {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "context_length": 128000,
        "cost_per_1k_tokens": {
          "input": 0.00015,
          "output": 0.0006
        },
        "capabilities": ["text", "vision", "function_calling"]
      }
    ],
    "default_model": "gpt-4o-mini",
    "cache_timestamp": "2025-01-27T10:00:00Z"
  }
}
```

### 8. Update Provider Models

Refresh the model list for a provider.

**Endpoint**: `POST /update_models/<provider>`

**Response**:
```json
{
  "success": true,
  "data": {
    "provider": "openai",
    "models_updated": 12,
    "new_models": ["gpt-4o-2024-11-20"],
    "removed_models": ["gpt-4-1106-preview"],
    "update_timestamp": "2025-01-27T10:30:00Z"
  }
}
```

## Document Management

### 9. Search Documents

Search uploaded documents for relevant content.

**Endpoint**: `POST /search`

**Request Body**:
```json
{
  "query": "machine learning algorithms",
  "limit": 5,
  "min_relevance": 0.5
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "filename": "ml_textbook.pdf",
        "relevance_score": 0.89,
        "excerpt": "Machine learning algorithms can be categorized into...",
        "page": 42,
        "word_count": 150
      }
    ],
    "total_results": 1,
    "search_time": 0.05
  }
}
```

### 10. List Documents

Get all uploaded documents.

**Endpoint**: `GET /documents`

**Response**:
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "filename": "ml_textbook.pdf",
        "upload_date": "2025-01-27T09:00:00Z",
        "size": 5242880,
        "pages": 250,
        "word_count": 75000,
        "status": "indexed"
      }
    ],
    "total_documents": 1,
    "total_size": 5242880
  }
}
```

### 11. Delete Document

Remove a document from the system.

**Endpoint**: `DELETE /documents/<filename>`

**Response**:
```json
{
  "success": true,
  "data": {
    "filename": "ml_textbook.pdf",
    "deleted": true,
    "freed_space": 5242880
  }
}
```

## Chat History

### 12. Save Chat

Save a chat conversation.

**Endpoint**: `POST /save_chat`

**Request Body**:
```json
{
  "title": "ML Discussion",
  "messages": [
    {
      "role": "user",
      "content": "What is machine learning?",
      "timestamp": "2025-01-27T10:00:00Z"
    },
    {
      "role": "assistant", 
      "content": "Machine learning is...",
      "timestamp": "2025-01-27T10:00:05Z",
      "provider": "groq",
      "model": "llama-3.3-70b-versatile"
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "chat_id": "chat_20250127_100000",
    "title": "ML Discussion",
    "message_count": 2,
    "saved_at": "2025-01-27T10:30:00Z"
  }
}
```

### 13. Load Chat

Load a saved chat conversation.

**Endpoint**: `GET /load_chat/<chat_id>`

**Response**:
```json
{
  "success": true,
  "data": {
    "chat_id": "chat_20250127_100000",
    "title": "ML Discussion",
    "messages": [ ... ],
    "created_at": "2025-01-27T10:00:00Z",
    "message_count": 2
  }
}
```

### 14. List Saved Chats

Get all saved chat conversations.

**Endpoint**: `GET /saved_chats`

**Response**:
```json
{
  "success": true,
  "data": {
    "chats": [
      {
        "chat_id": "chat_20250127_100000",
        "title": "ML Discussion", 
        "created_at": "2025-01-27T10:00:00Z",
        "message_count": 2,
        "last_message": "Machine learning is..."
      }
    ],
    "total_chats": 1
  }
}
```

## System Information

### 15. Health Check

Check system health and status.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "2.0.0",
    "uptime": 3600,
    "providers": {
      "openai": "connected",
      "groq": "connected", 
      "anthropic": "api_key_missing",
      "gemini": "rate_limited"
    },
    "database": "connected",
    "file_storage": "available",
    "memory_usage": "45%",
    "disk_usage": "23%"
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### 16. System Stats

Get detailed system statistics.

**Endpoint**: `GET /stats`

**Response**:
```json
{
  "success": true,
  "data": {
    "requests": {
      "total": 1547,
      "today": 89,
      "last_hour": 12
    },
    "providers": {
      "openai": {"requests": 523, "errors": 2},
      "groq": {"requests": 1024, "errors": 0}
    },
    "files": {
      "total_uploaded": 45,
      "total_size": 234567890,
      "processing_queue": 0
    },
    "performance": {
      "avg_response_time": 1.2,
      "cache_hit_rate": 0.78,
      "uptime_percentage": 99.9
    }
  }
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request format or parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: File upload too large
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Error Response Format

```json
{
  "success": false,
  "error": "Detailed error description",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional error details",
    "suggestion": "Try reducing the file size"
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### Common Error Codes

- `INVALID_INPUT`: Request validation failed
- `PROVIDER_ERROR`: AI provider API error
- `FILE_TOO_LARGE`: File exceeds size limits
- `UNSUPPORTED_FORMAT`: File format not supported
- `PROCESSING_FAILED`: File processing error
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `QUOTA_EXCEEDED`: Provider quota exceeded
- `TIMEOUT`: Request timeout
- `SERVICE_UNAVAILABLE`: Service temporarily down

## Rate Limiting

### Default Limits

- **Chat requests**: 60 per minute per IP
- **File uploads**: 10 per minute per IP
- **Model updates**: 5 per hour per IP
- **Search requests**: 100 per minute per IP

### Rate Limit Headers

Response headers include rate limit information:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706356200
```

## SDKs and Examples

### Python Example

```python
import requests

# Chat with AI
response = requests.post('http://localhost:5000/chat', json={
    'message': 'Explain quantum computing',
    'provider': 'groq',
    'model': 'llama-3.3-70b-versatile'
})

data = response.json()
if data['success']:
    print(data['data']['response'])
else:
    print(f"Error: {data['error']}")
```

### JavaScript Example

```javascript
// Chat with AI
const response = await fetch('/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        message: 'Explain quantum computing',
        provider: 'groq',
        model: 'llama-3.3-70b-versatile'
    })
});

const data = await response.json();
if (data.success) {
    console.log(data.data.response);
} else {
    console.error('Error:', data.error);
}
```

### cURL Examples

```bash
# Chat request
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is AI?",
    "provider": "groq"
  }'

# File upload
curl -X POST http://localhost:5000/upload \
  -F "files=@document.pdf" \
  -F "files=@presentation.pptx"

# Get models
curl http://localhost:5000/get_models/openai
```

This API documentation provides comprehensive coverage of all endpoints with detailed examples and error handling information for seamless integration.
