"""
TQ GenAI Chat - Refactored Main Application

Multi-provider GenAI chat application with modular architecture.
Supports 10+ AI providers with advanced file processing capabilities.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

import speech_recognition as sr
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from pydub import AudioSegment
from werkzeug.utils import secure_filename

from config.settings import ALLOWED_EXTENSIONS, EXPORT_DIR, SAVE_DIR, UPLOAD_DIR
from core.chat_handler import create_chat_handler
from core.file_processor import FileProcessor, status_tracker
from core.models import model_manager
from core.providers import provider_manager
from core.tts import tts_engine
from persona import PERSONAS
from services.file_manager import FileManager

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, verbose=True)

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

# Configure Flask
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.config.update(
    {
        "JSON_SORT_KEYS": False,
        "MAX_CONTENT_LENGTH": 64 * 1024 * 1024,  # 64MB
        "UPLOAD_FOLDER": str(Path(app.root_path) / "uploads"),
        "MAX_FILES": 10,
    }
)

# Initialize services
with app.app_context():
    file_manager = FileManager()
    chat_handler = create_chat_handler(file_manager)

# Ensure directories exist
for directory in [SAVE_DIR, EXPORT_DIR, UPLOAD_DIR]:
    directory.mkdir(mode=0o755, parents=True, exist_ok=True)

# Processing status tracking
PROCESSING_STATUS = status_tracker._statuses
PROCESSING_ERRORS = {}


@app.route("/")
def index():
    """Main chat interface"""
    return render_template("index.html")


# --- Persona Routes ---
@app.route("/get_personas")
def get_personas():
    """Get available personas"""
    return jsonify(list(PERSONAS.keys()))


@app.route("/get_persona_content/<persona_key>")
def get_persona_content(persona_key):
    """Get persona content"""
    content = PERSONAS.get(persona_key, "")
    return jsonify({"content": content})


# --- Model Management Routes ---
@app.route("/get_models/<provider>")
def get_models(provider):
    """Get available models for a provider"""
    try:
        if not provider_manager.is_provider_available(provider):
            return jsonify({"error": f"Provider {provider} not available"}), 404

        models = model_manager.get_models(provider)

        # Get the default model for this provider
        provider_instance = provider_manager.get_provider(provider)
        default_model = provider_instance.config.default_model if provider_instance else None

        return jsonify({"models": models, "default": default_model})
    except Exception as e:
        app.logger.error(f"Error getting models for {provider}: {str(e)}")
        return jsonify({"error": "Failed to get models"}), 500


@app.route("/update_models/<provider>", methods=["POST"])
def update_models(provider):
    """Update models for a provider"""
    try:
        data = request.get_json()
        if not data or "models" not in data:
            return jsonify({"error": "Models data required"}), 400

        models = data["models"]
        if not isinstance(models, list):
            return jsonify({"error": "Models must be a list"}), 400

        model_manager.update_models(provider, models)
        return jsonify({"message": f"Models updated for {provider}", "count": len(models)})
    except Exception as e:
        app.logger.error(f"Error updating models for {provider}: {str(e)}")
        return jsonify({"error": "Failed to update models"}), 500


# --- Chat Routes ---
@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        provider = data.get("provider")
        if not provider:
            return jsonify({"error": "Provider is required"}), 400

        if not provider_manager.is_provider_available(provider):
            return jsonify({"error": f"Provider {provider} not available or not configured"}), 401

        response = chat_handler.process_chat_request(data)
        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/search_context", methods=["POST"])
def search_context():
    """Search uploaded documents for relevant content"""
    try:
        data = request.get_json()
        query = data.get("message", "")

        if not query:
            return jsonify({"error": "No query provided"}), 400

        results = file_manager.search_documents(query)

        # Format results for response
        formatted_results = [
            {
                "filename": r["filename"],
                "excerpt": r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"],
                "similarity": r["similarity"],
            }
            for r in results
        ]

        return jsonify({"results": formatted_results})

    except Exception as e:
        app.logger.error(f"Context search error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# --- Document Management Routes ---
@app.route("/documents/list", methods=["GET"])
def list_documents():
    """Get list of all uploaded documents with statistics"""
    try:
        # Get pagination parameters
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", default=0, type=int)

        # Get documents and statistics
        documents = file_manager.get_all_documents(limit=limit, offset=offset)
        stats = file_manager.get_document_statistics()

        # Format documents for frontend
        formatted_documents = []
        for doc in documents:
            formatted_doc = {
                "id": doc["id"],
                "filename": doc["title"],
                "file_size": doc.get("file_size", 0),
                "timestamp": doc["timestamp"],
                "formatted_timestamp": doc.get("formatted_timestamp", ""),
                "type": doc["type"],
                "metadata": doc.get("metadata", {}),
            }
            formatted_documents.append(formatted_doc)

        return jsonify({"documents": formatted_documents, "stats": stats})

    except Exception as e:
        app.logger.error(f"Documents list error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/documents/delete/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    """Delete a document by ID"""
    try:
        from core.document_store import DocumentStore

        document_store = DocumentStore()

        success = document_store.delete_document(doc_id)
        if success:
            return jsonify({"message": "Document deleted successfully"})
        else:
            return jsonify({"error": "Document not found"}), 404

    except Exception as e:
        app.logger.error(f"Document deletion error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# --- TTS Routes ---
@app.route("/tts/voices", methods=["GET"])
def tts_voices():
    """Get available TTS voices"""
    try:
        voices = tts_engine.get_voices()
        return jsonify({"voices": [voice.to_dict() for voice in voices]})
    except Exception as e:
        app.logger.error(f"TTS voices error: {str(e)}")
        return jsonify({"error": "Failed to get TTS voices"}), 500


@app.route("/tts", methods=["POST"])
def tts():
    """Convert text to speech"""
    try:
        data = request.get_json()
        text = data.get("text", "")
        voice_id = data.get("voice_id")
        lang = data.get("lang", "en")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        audio_data, content_type = tts_engine.synthesize(text, voice_id, lang)
        return audio_data, 200, {"Content-Type": content_type}

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"TTS error: {str(e)}")
        return jsonify({"error": "TTS processing failed"}), 500


# --- File Upload Routes ---
@app.route("/upload", methods=["POST"])
def upload_files():
    """Upload and process files"""
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files selected"}), 400

        if len(files) > app.config["MAX_FILES"]:
            return (
                jsonify({"error": f'Too many files. Maximum {app.config["MAX_FILES"]} allowed'}),
                400,
            )

        # Process files asynchronously
        results = []
        for file in files:
            if file.filename == "":
                continue

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = Path(app.config["UPLOAD_FOLDER"]) / filename
                file.save(file_path)

                # Start async processing
                asyncio.create_task(process_file_async(filename, str(file_path)))
                results.append({"filename": filename, "status": "processing"})
            else:
                results.append(
                    {
                        "filename": file.filename,
                        "status": "error",
                        "message": "File type not allowed",
                    }
                )

        return jsonify({"results": results})

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Upload failed"}), 500


@app.route("/upload/status/<filename>")
def upload_status(filename):
    """Get file processing status"""
    try:
        status = PROCESSING_STATUS.get(filename, {})
        if filename in PROCESSING_ERRORS:
            status["error"] = PROCESSING_ERRORS[filename]
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"Status check error: {str(e)}")
        return jsonify({"error": "Failed to get status"}), 500


# --- Audio Processing Routes ---
@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    """Upload and transcribe audio files"""
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files["audio"]
        if audio_file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Save audio file temporarily
        filename = secure_filename(audio_file.filename)
        temp_path = Path(tempfile.gettempdir()) / filename
        audio_file.save(temp_path)

        # Convert to WAV if needed
        if not filename.lower().endswith(".wav"):
            audio = AudioSegment.from_file(temp_path)
            wav_path = temp_path.with_suffix(".wav")
            audio.export(wav_path, format="wav")
            temp_path.unlink()  # Remove original
            temp_path = wav_path

        # Transcribe audio
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(temp_path)) as source:
            audio_data = recognizer.record(source)
            transcript = recognizer.recognize_google(audio_data)

        # Cleanup
        temp_path.unlink()

        return jsonify({"transcript": transcript})

    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand audio"}), 400
    except sr.RequestError as e:
        return jsonify({"error": f"Speech recognition error: {str(e)}"}), 500
    except Exception as e:
        app.logger.error(f"Audio transcription error: {str(e)}")
        return jsonify({"error": "Audio processing failed"}), 500


# --- Save/Load/Export Routes ---
@app.route("/save_chat", methods=["POST"])
def save_chat():
    """Save chat history"""
    try:
        data = request.get_json()
        if not data or "history" not in data:
            return jsonify({"error": "No chat history provided"}), 400

        # Convert frontend format to backend format
        chat_data = {
            "title": data.get("title", ""),
            "timestamp": data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            "messages": [],
        }

        # Convert chat history to messages format
        for msg in data["history"]:
            chat_data["messages"].append(
                {
                    "role": "user" if msg.get("isUser", True) else "assistant",
                    "content": msg.get("content", ""),
                }
            )

        # Save using file manager
        filepath = file_manager.save_chat_history(chat_data)
        filename = os.path.basename(filepath)

        return jsonify({"filename": filename, "path": filepath})

    except Exception as e:
        app.logger.error(f"Save chat error: {str(e)}")
        return jsonify({"error": "Failed to save chat"}), 500


@app.route("/list_saved_chats")
def list_saved_chats():
    """Get list of saved chat files"""
    try:
        chats = file_manager.get_saved_chats()

        # Format for frontend
        formatted_chats = []
        for chat in chats:
            formatted_chats.append(
                {
                    "filename": chat["filename"],
                    "display_name": chat.get("title", chat["filename"]),
                    "modified": chat["created"],
                    "message_count": chat.get("message_count", 0),
                }
            )

        return jsonify({"chats": formatted_chats})

    except Exception as e:
        app.logger.error(f"List saved chats error: {str(e)}")
        return jsonify({"error": "Failed to list saved chats"}), 500


@app.route("/load_chat/<filename>")
def load_chat(filename):
    """Load a specific chat file"""
    try:
        # Sanitize filename for security
        filename = secure_filename(filename)
        filepath = SAVE_DIR / filename

        if not filepath.exists():
            return jsonify({"error": "Chat file not found"}), 404

        # Load chat data
        with open(filepath, encoding="utf-8") as f:
            chat_data = json.load(f)

        # Convert backend format to frontend format
        history = []
        for msg in chat_data.get("messages", []):
            history.append({"content": msg.get("content", ""), "isUser": msg.get("role") == "user"})

        return jsonify(
            {
                "history": history,
                "title": chat_data.get("title", ""),
                "timestamp": chat_data.get("timestamp", ""),
            }
        )

    except Exception as e:
        app.logger.error(f"Load chat error: {str(e)}")
        return jsonify({"error": "Failed to load chat"}), 500


@app.route("/export_chat", methods=["POST"])
def export_chat():
    """Export chat history"""
    try:
        data = request.get_json()
        if not data or "history" not in data:
            return jsonify({"error": "No chat history provided"}), 400

        export_format = data.get("format", "md").lower()

        # Convert frontend format to backend format
        chat_data = {
            "title": data.get("title", "Chat Export"),
            "timestamp": data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
            "messages": [],
        }

        # Convert chat history to messages format
        for msg in data["history"]:
            chat_data["messages"].append(
                {
                    "role": "user" if msg.get("isUser", True) else "assistant",
                    "content": msg.get("content", ""),
                }
            )

        # Export using file manager
        if export_format in ["md", "txt"]:
            filepath = file_manager.export_chat(chat_data, export_format=export_format)
        elif export_format == "json":
            # For JSON, save directly (FileManager doesn't handle JSON export)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            title = chat_data.get("title", "chat_export").lower().replace(" ", "_")
            title = secure_filename(title)
            filename = f"{title}_{timestamp}.json"
            filepath = EXPORT_DIR / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
        else:
            return jsonify({"error": "Unsupported export format"}), 400

        filename = os.path.basename(filepath)
        return jsonify({"filename": filename, "path": str(filepath)})

    except Exception as e:
        app.logger.error(f"Export error: {str(e)}")
        return jsonify({"error": "Export failed"}), 500


# --- Utility Functions ---
def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


async def process_file_async(filename, file_path):
    """Process uploaded file asynchronously"""
    try:
        processor = FileProcessor()
        content = await processor.process_file(file_path, filename)

        # Add to document store
        file_manager.add_document(filename, content)

        # Update status
        PROCESSING_STATUS[filename] = {
            "status": "completed",
            "timestamp": time.time(),
            "size": len(content),
        }

    except Exception as e:
        app.logger.error(f"File processing error for {filename}: {str(e)}")
        PROCESSING_ERRORS[filename] = str(e)
        PROCESSING_STATUS[filename] = {
            "status": "failed",
            "timestamp": time.time(),
            "error": str(e),
        }


# --- Health Check ---
@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "providers": provider_manager.list_providers(),
            "models_loaded": len(model_manager.get_all_models()),
            "documents": file_manager.total_documents
            if hasattr(file_manager, "total_documents")
            else 0,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
