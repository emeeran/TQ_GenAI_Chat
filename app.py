from core.providers import provider_manager
from core.models import model_manager
import os
from flask import Flask, request, jsonify
from flask_login import login_required, LoginManager, UserMixin
from werkzeug.utils import secure_filename
from pathlib import Path
import time
import json
import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor
try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False

# --- File Manager, TTS Engine, and Document Store ---
from core.file_processor import FileProcessor
from services import file_manager
try:
    from services import tts_engine
except ImportError:
    tts_engine = None

# --- Constants and Globals ---
ALLOWED_EXTENSIONS = {"pdf", "docx", "csv", "xlsx", "md", "txt", "png", "jpg", "jpeg"}
PROCESSING_STATUS = {}
PROCESSING_ERRORS = {}
EXPORT_DIR = Path("exports")
SAVE_DIR = Path("saved_chats")
thread_pool = ThreadPoolExecutor(max_workers=4)
from config.settings import config
from blueprints.chat import chat_bp
from blueprints.file import file_bp
from blueprints.auth import auth_bp
from blueprints.tts import tts_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config._app_config.secret_key
    app.config['MAX_CONTENT_LENGTH'] = config._app_config.max_content_length
    app.config['UPLOAD_FOLDER'] = config._app_config.upload_folder
    app.config['MAX_FILES'] = config._app_config.max_files
    app.config['JSON_SORT_KEYS'] = config._app_config.json_sort_keys
    app.config['CORS_ORIGINS'] = config._app_config.cors_origins
    app.register_blueprint(chat_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tts_bp)

    # --- Flask-Login Setup ---
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # You may want to change this to your login route

    # Dummy user class and loader for development/testing
    class User(UserMixin):
        def __init__(self, user_id):
            self.id = user_id
            self.name = f"user{user_id}"
            self.is_authenticated = True

    @login_manager.user_loader
    def load_user(user_id):
        return User(user_id)

    return app

app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)))


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
            "providers": provider_manager.list_providers(),
            "models_loaded": len(model_manager.get_all_models()),
            "documents": (
                file_manager.total_documents if hasattr(file_manager, "total_documents") else 0
            ),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)))
