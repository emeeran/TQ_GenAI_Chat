
import asyncio
import json
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from core.document_store import DocumentStore
from core.file_processor import FileProcessor
from services.file_manager import FileManager
from utils.auth import require_auth


file_manager = FileManager()
file_bp = Blueprint("file", __name__, url_prefix="/api/file")

# Upload endpoint
@file_bp.route("/upload", methods=["POST"])
@require_auth
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save to disk first (secured naming happens inside FileManager)
    saved_path = file_manager.save_uploaded_file(file)

    try:
        # Read saved bytes and extract text via FileProcessor
        with open(saved_path, "rb") as f:
            content_bytes = f.read()

        extracted_content = asyncio.run(
            FileProcessor.process_file(content_bytes, file.filename)
        )

        # Compose metadata and persist via DocumentStore through FileManager
        file_ext = Path(file.filename).suffix.lstrip(".").lower()
        metadata = {
            "source": "upload",
            "original_filename": file.filename,
            "file_extension": file_ext,
            "file_size": len(content_bytes),
        }

        doc_id = file_manager.add_document(
            filename=file.filename,
            content=extracted_content,
            doc_type=file_ext or "text",
            metadata=metadata,
        )

        # Summarize chunking outcome for clients
        summary = DocumentStore().chunk_manager.get_document_summary(doc_id)

        return jsonify(
            {
                "status": "success",
                "saved_path": saved_path,
                "document_id": doc_id,
                "chunk_summary": summary,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Upload processing failed: {str(e)}"}), 500

# Status endpoint (stub, as FileManager does not have get_file_status)
@file_bp.route("/status/<filename>", methods=["GET"])
@require_auth
def status(filename):
    # Implement status tracking if needed, else return success
    return jsonify({"filename": filename, "status": "unknown"})

# Document list
@file_bp.route("/documents/list", methods=["GET"])
@require_auth
def list_documents():
    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", default=0, type=int)
    documents = file_manager.get_all_documents(limit=limit, offset=offset)
    stats = file_manager.get_document_statistics()
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

# Document delete
@file_bp.route("/documents/delete/<doc_id>", methods=["DELETE"])
@require_auth
def delete_document(doc_id):
    document_store = DocumentStore()
    success = document_store.delete_document(doc_id)
    if success:
        return jsonify({"message": "Document deleted successfully"})
    else:
        return jsonify({"error": "Document not found"}), 404

# Search context
@file_bp.route("/search_context", methods=["POST"])
@require_auth
def search_context():
    data = request.get_json()
    query = data.get("message", "")
    if not query:
        return jsonify({"error": "No query provided"}), 400
    results = file_manager.search_documents(query)
    formatted_results = [
        {
            "filename": r["filename"],
            "excerpt": (r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"]),
            "similarity": r["similarity"],
        }
        for r in results
    ]
    return jsonify({"results": formatted_results})

# Save chat
@file_bp.route("/save_chat", methods=["POST"])
def save_chat():
    data = request.get_json()
    if not data or "history" not in data:
        return jsonify({"error": "No chat history provided"}), 400
    chat_data = {
        "title": data.get("title", ""),
        "timestamp": data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
        "messages": [],
    }
    for msg in data["history"]:
        chat_data["messages"].append({
            "role": "user" if msg.get("isUser", True) else "assistant",
            "content": msg.get("content", ""),
        })
    filepath = file_manager.save_chat_history(chat_data)
    filename = os.path.basename(filepath)
    return jsonify({"filename": filename, "path": filepath})

# List saved chats
@file_bp.route("/list_saved_chats", methods=["GET"])
def list_saved_chats():
    chats = file_manager.get_saved_chats()
    formatted_chats = []
    for chat in chats:
        formatted_chats.append({
            "filename": chat["filename"],
            "display_name": chat.get("title", chat["filename"]),
            "modified": chat["created"],
            "message_count": chat.get("message_count", 0),
        })
    return jsonify({"chats": formatted_chats})

# Load chat
@file_bp.route("/load_chat/<filename>", methods=["GET"])
def load_chat(filename):
    filename = secure_filename(filename)
    filepath = Path(file_manager.save_dir) / filename
    if not filepath.exists():
        return jsonify({"error": "Chat file not found"}), 404
    with open(filepath, encoding="utf-8") as f:
        chat_data = json.load(f)
    history = []
    for msg in chat_data.get("messages", []):
        history.append({"content": msg.get("content", ""), "isUser": msg.get("role") == "user"})
    return jsonify({
        "history": history,
        "title": chat_data.get("title", ""),
        "timestamp": chat_data.get("timestamp", ""),
    })

# Export chat
@file_bp.route("/export_chat", methods=["POST"])
def export_chat():
    data = request.get_json()
    if not data or "history" not in data:
        return jsonify({"error": "No chat history provided"}), 400
    export_format = data.get("format", "md").lower()
    chat_data = {
        "title": data.get("title", "Chat Export"),
        "timestamp": data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
        "messages": [],
    }
    for msg in data["history"]:
        chat_data["messages"].append({
            "role": "user" if msg.get("isUser", True) else "assistant",
            "content": msg.get("content", ""),
        })
    if export_format in ["md", "txt"]:
        filepath = file_manager.export_chat(chat_data, export_format=export_format)
    elif export_format == "json":
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        title = chat_data.get("title", "chat_export").lower().replace(" ", "_")
        title = secure_filename(title)
        filename = f"{title}_{timestamp}.json"
        filepath = Path(file_manager.export_dir) / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=2, ensure_ascii=False)
    else:
        return jsonify({"error": "Unsupported export format"}), 400
    filename = os.path.basename(filepath)
    return jsonify({"filename": filename, "path": str(filepath)})
