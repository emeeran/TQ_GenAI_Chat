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
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import speech_recognition as sr

    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_cors import CORS
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from config.settings import ALLOWED_EXTENSIONS, EXPORT_DIR, SAVE_DIR, UPLOAD_DIR
from core.chat_handler import create_chat_handler
from core.file_processor import FileProcessor, status_tracker
from core.models import model_manager

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
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey123')

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

# Flask-Login config
BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "changeme")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = id
        self.password = BASIC_AUTH_PASSWORD

    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    if user_id == BASIC_AUTH_USERNAME:
        return User(user_id)
    return None

# Thread pool for async file processing
thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FileProcessor")

# Ensure directories exist
for directory in [SAVE_DIR, EXPORT_DIR, UPLOAD_DIR]:
    directory.mkdir(mode=0o755, parents=True, exist_ok=True)

# Processing status tracking
PROCESSING_STATUS = status_tracker._statuses
PROCESSING_ERRORS = {}


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == BASIC_AUTH_USERNAME and password == BASIC_AUTH_PASSWORD:
            user = User(username)
            login_user(user)
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials."
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    """Main chat interface"""
    return render_template("index.html")


# --- Persona Routes ---
@app.route("/get_personas")
def get_personas():
    """Get available personas"""
    personas_list = []
    for persona_id, persona_content in PERSONAS.items():
        display_name = persona_id.replace("_", " ").title()
        if isinstance(persona_content, dict):
            personas_list.append({
                "id": persona_id,
                "name": persona_content.get("name", display_name),
                "content": persona_content.get("system_prompt", "")
            })
        else:
            personas_list.append({
                "id": persona_id,
                "name": display_name,
                "content": persona_content
            })
    return jsonify({"personas": personas_list})


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
        models = model_manager.get_models(provider)

    # No provider_instance needed; use provider/model directly with generate_llm_response
        default_model = models[0] if models else None

        return jsonify({"models": models, "default": default_model})
    except Exception as e:
        app.logger.error(f"Error getting models for {provider}: {str(e)}")
        return jsonify({"error": "Failed to get models"}), 500


@app.route("/update_models/<provider>", methods=["POST"])
def update_models(provider):
    """Update models for a provider by fetching from their API"""
    try:
        # Import the update script functionality
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent / "scripts"))

        from update_models_from_providers import fetch_provider_models

        # Fetch latest models from provider
        new_models = fetch_provider_models(provider)

        if not new_models:
            return jsonify({"error": f"Failed to fetch models for {provider}"}), 500

        # Update the model manager
        model_manager.update_models(provider, new_models)

        # Get the default model for this provider
        # provider_instance = provider_manager.get_provider(provider)
        # default_model = provider_instance.config.default_model if provider_instance else None
    # No provider_instance needed; use provider/model directly with generate_llm_response
        default_model = new_models[0] if new_models else None

        return jsonify(
            {
                "success": True,
                "message": f"Successfully updated {len(new_models)} models for {provider}",
                "models": new_models,
                "default": default_model,
                "count": len(new_models),
            }
        )

    except Exception as e:
        app.logger.error(f"Error updating models for {provider}: {str(e)}")
        return jsonify({"error": f"Failed to update models: {str(e)}"}), 500


@app.route("/set_default_model/<provider>", methods=["POST"])
def set_default_model(provider):
    """Set default model for a provider"""
    try:
        data = request.get_json()
        if not data or "model" not in data:
            return jsonify({"error": "Model is required"}), 400

        model = data["model"]

        # Verify model exists for provider
        if not model_manager.is_model_available(provider, model):
            return jsonify({"error": f"Model {model} not available for {provider}"}), 400

        # Set as default
        model_manager.set_default_model(provider, model)

        return jsonify(
            {
                "success": True,
                "message": f"Set {model} as default for {provider}",
                "provider": provider,
                "model": model,
            }
        )

    except Exception as e:
        app.logger.error(f"Error setting default model for {provider}: {str(e)}")
        return jsonify({"error": f"Failed to set default model: {str(e)}"}), 500


# --- Chat Routes ---
@app.route("/chat", methods=["POST"])
@login_required
def chat():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        provider = data.get("provider")
        if not provider:
            return jsonify({"error": "Provider is required"}), 400

    # Assume provider is available; handle errors from LiteLLM at response time
        response = chat_handler.process_chat_request(data)
        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/search_context", methods=["POST"])
@login_required
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
                "excerpt": (
                    r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"]
                ),
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
@login_required
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
@login_required
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
@login_required
def upload_files():
    """Upload and process files"""
    try:
        app.logger.info(f"Upload request received from {request.remote_addr}")
        app.logger.debug(f"Request files keys: {list(request.files.keys())}")
        app.logger.debug(f"Request form keys: {list(request.form.keys())}")
        
        if "files" not in request.files and "files[]" not in request.files:
            app.logger.warning("No files provided in upload request")
            return jsonify({"error": "No files provided"}), 400

        # Support both 'files' and 'files[]' naming conventions
        files = request.files.getlist("files") or request.files.getlist("files[]")
        if not files:
            app.logger.warning("No files selected in upload request")
            return jsonify({"error": "No files selected"}), 400

        if len(files) > app.config["MAX_FILES"]:
            app.logger.warning(f"Too many files: {len(files)} > {app.config['MAX_FILES']}")
            return (
                jsonify({"error": f'Too many files. Maximum {app.config["MAX_FILES"]} allowed'}),
                400,
            )

        # Process files asynchronously
        results = []
        for file in files:
            if file.filename == "":
                continue

            app.logger.info(f"Processing file: {file.filename}")
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = Path(app.config["UPLOAD_FOLDER"]) / filename
                
                try:
                    # Ensure upload directory exists
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file.save(file_path)
                    app.logger.info(f"File saved: {file_path}")
                    
                    # Start async processing using thread pool
                    thread_pool.submit(process_file_sync, filename, str(file_path))
                    results.append({"filename": filename, "status": "success"})
                    app.logger.info(f"File processing started: {filename}")
                    
                except Exception as save_error:
                    app.logger.error(f"Error saving file {filename}: {str(save_error)}")
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "message": f"Failed to save file: {str(save_error)}"
                    })
            else:
                app.logger.warning(f"File type not allowed: {file.filename}")
                results.append(
                    {
                        "filename": file.filename,
                        "status": "error",
                        "message": "File type not allowed",
                    }
                )

        app.logger.info(f"Upload request completed with {len(results)} results")
        return jsonify({"results": results})

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route("/upload/status/<filename>")
@login_required
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
    if not SPEECH_RECOGNITION_AVAILABLE:
        return (
            jsonify(
                {"error": "Speech recognition not available - missing speech_recognition module"}
            ),
            503,
        )

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
    if not filename or "." not in filename:
        app.logger.warning(f"Invalid filename format: {filename}")
        return False
    
    extension = filename.rsplit(".", 1)[1].lower()
    is_allowed = extension in ALLOWED_EXTENSIONS
    
    if not is_allowed:
        app.logger.warning(f"File extension '{extension}' not in allowed extensions: {ALLOWED_EXTENSIONS}")
    
    return is_allowed


async def process_file_async(filename, file_path):
    """Process uploaded file asynchronously"""
    try:
        processor = FileProcessor()
        
        # Read file content as bytes
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Process the file content
        extracted_content = await processor.process_file(content, filename)
        app.logger.info(f"Successfully extracted {len(extracted_content)} characters from {filename}")

        # Add to document store
        try:
            doc_id = file_manager.add_document(filename, extracted_content)
            app.logger.info(f"Successfully added document to store with ID: {doc_id}")
        except Exception as doc_error:
            app.logger.error(f"Failed to add document to store: {str(doc_error)}")
            raise doc_error

        # Update status
        PROCESSING_STATUS[filename] = {
            "status": "Complete",
            "timestamp": time.time(),
            "size": len(extracted_content),
        }

    except Exception as e:
        app.logger.error(f"File processing error for {filename}: {str(e)}")
        PROCESSING_ERRORS[filename] = str(e)
        PROCESSING_STATUS[filename] = {
            "status": "Failed",
            "timestamp": time.time(),
            "error": str(e),
        }


def process_file_sync(filename, file_path):
    """Synchronous wrapper for file processing that can run in thread pool"""
    try:
        app.logger.info(f"Starting file processing for: {filename}")
        
        # Initialize processing status
        PROCESSING_STATUS[filename] = {
            "status": "Processing",
            "timestamp": time.time(),
            "progress": 0,
        }
        
        # Run the async function in a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_file_async(filename, file_path))
            app.logger.info(f"File processing completed successfully: {filename}")
        finally:
            loop.close()
            
    except Exception as e:
        app.logger.error(f"File processing wrapper error for {filename}: {str(e)}", exc_info=True)
        PROCESSING_ERRORS[filename] = str(e)
        PROCESSING_STATUS[filename] = {
            "status": "Failed",
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
            "providers": ["openai", "groq", "anthropic", "mistral", "gemini", "cohere", "xai", "deepseek", "alibaba", "openrouter", "huggingface", "moonshot", "perplexity"],  # Static provider list
            "models_loaded": len(model_manager.get_all_models()),
            "documents": (
                file_manager.total_documents if hasattr(file_manager, "total_documents") else 0
            ),
        }
    )


if __name__ == "__main__":
    try:
        app.run(debug=True, host="0.0.0.0", port=5005)
    finally:
        # Clean up thread pool on shutdown
        thread_pool.shutdown(wait=True)
