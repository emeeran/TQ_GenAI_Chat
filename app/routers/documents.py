"""
Document management routes for FastAPI application.
"""

import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasicCredentials

from app.dependencies import get_file_manager
from app.models.requests import ExportChatRequest, SaveChatRequest
from app.models.responses import (
    DocumentsResponse, LoadChatResponse,
    SavedChatsResponse, SuccessResponse
)
from app.routers.auth import require_auth
from app.utils import secure_filename
from config.settings import EXPORT_DIR, SAVE_DIR
from core.document_store import DocumentStore

router = APIRouter()


@router.get("/list", response_model=DocumentsResponse)
async def list_documents(
    limit: int = None,
    offset: int = 0,
    _: HTTPBasicCredentials = Depends(require_auth),
    file_manager = Depends(get_file_manager)
):
    """Get list of all uploaded documents with statistics"""
    try:
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

        return {"documents": formatted_documents, "stats": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{doc_id}")
async def delete_document(
    doc_id: str,
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Delete a document by ID"""
    try:
        document_store = DocumentStore()
        success = document_store.delete_document(doc_id)
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save_chat", response_model=SuccessResponse)
async def save_chat(
    request: SaveChatRequest,
    file_manager = Depends(get_file_manager)
):
    """Save chat history"""
    try:
        if not request.history:
            raise HTTPException(status_code=400, detail="No chat history provided")

        # Convert frontend format to backend format
        chat_data = {
            "title": request.title or "",
            "timestamp": request.timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages": [],
        }

        # Convert chat history to messages format
        for msg in request.history:
            chat_data["messages"].append({
                "role": "user" if msg.get("isUser", True) else "assistant",
                "content": msg.get("content", ""),
            })

        # Save using file manager
        filepath = file_manager.save_chat_history(chat_data)
        filename = Path(filepath).name

        return {"message": "Chat saved successfully", "filename": filename, "path": filepath}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save chat")


@router.get("/list_saved_chats", response_model=SavedChatsResponse)
async def list_saved_chats(
    file_manager = Depends(get_file_manager)
):
    """Get list of saved chat files"""
    try:
        chats = file_manager.get_saved_chats()

        # Format for frontend
        formatted_chats = []
        for chat in chats:
            formatted_chats.append({
                "filename": chat["filename"],
                "display_name": chat.get("title", chat["filename"]),
                "modified": chat["created"],
                "message_count": chat.get("message_count", 0),
            })

        return {"chats": formatted_chats}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list saved chats")


@router.get("/load_chat/{filename}", response_model=LoadChatResponse)
async def load_chat(filename: str):
    """Load a specific chat file"""
    try:
        # Sanitize filename for security
        filename = secure_filename(filename)
        filepath = SAVE_DIR / filename

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Chat file not found")

        # Load chat data
        with open(filepath, encoding="utf-8") as f:
            chat_data = json.load(f)

        # Convert backend format to frontend format
        history = []
        for msg in chat_data.get("messages", []):
            history.append({
                "content": msg.get("content", ""), 
                "isUser": msg.get("role") == "user"
            })

        return {
            "history": history,
            "title": chat_data.get("title", ""),
            "timestamp": chat_data.get("timestamp", ""),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load chat")


@router.post("/export_chat", response_model=SuccessResponse)
async def export_chat(request: ExportChatRequest):
    """Export chat history"""
    try:
        if not request.history:
            raise HTTPException(status_code=400, detail="No chat history provided")

        export_format = request.format.lower()

        # Convert frontend format to backend format
        chat_data = {
            "title": request.title or "Chat Export",
            "timestamp": request.timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages": [],
        }

        # Convert chat history to messages format
        for msg in request.history:
            chat_data["messages"].append({
                "role": "user" if msg.get("isUser", True) else "assistant",
                "content": msg.get("content", ""),
            })

        # Export using file manager or handle JSON directly
        if export_format in ["md", "txt"]:
            # Use file manager for md/txt exports
            file_manager = await get_file_manager()
            filepath = file_manager.export_chat(chat_data, export_format=export_format)
        elif export_format == "json":
            # Handle JSON export directly
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            title = chat_data.get("title", "chat_export").lower().replace(" ", "_")
            title = secure_filename(title)
            filename = f"{title}_{timestamp}.json"
            filepath = EXPORT_DIR / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

        filename = Path(filepath).name
        return {"message": "Chat exported successfully", "filename": filename, "path": str(filepath)}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Export failed")
