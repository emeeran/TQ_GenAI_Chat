"""
File Manager Service
Handles file operations, storage, and retrieval.
"""
import json
import logging
import os
from datetime import datetime

from werkzeug.utils import secure_filename

from config.settings import ALLOWED_EXTENSIONS, EXPORT_DIR, SAVE_DIR, UPLOAD_DIR

# Create a logger that doesn't require Flask context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)


class FileManager:
    def get_document(self, filename: str):
        """Retrieve a document by filename (title)."""
        from core.document_store import DocumentStore

        if not hasattr(self, "_document_store"):
            self._document_store = DocumentStore()
        # Search for document by title (filename)
        docs = self._document_store.search_documents(filename, limit=1)
        if docs:
            return docs[0]
        return None

    def add_document(
        self,
        filename: str,
        content: str,
        doc_type: str = "text",
        metadata: dict = None,
        user_id: str = None,
    ):
        """Add a document to the document store (proxy)."""
        from core.document_store import DocumentStore

        if not hasattr(self, "_document_store"):
            self._document_store = DocumentStore()
        return self._document_store.add_document(
            content=content,
            title=filename,
            file_path=None,
            doc_type=doc_type,
            metadata=metadata,
            user_id=user_id,
        )

    def search_documents(self, query, top_n=3):
        """Proxy to DocumentStore.search_documents for context search."""
        from core.document_store import DocumentStore

        if not hasattr(self, "_document_store"):
            self._document_store = DocumentStore()
        results = self._document_store.search_documents(query, limit=top_n)
        # Optionally add similarity score if not present
        for r in results:
            if "similarity" not in r:
                r["similarity"] = 1.0  # Placeholder if not calculated
            if "filename" not in r and "title" in r:
                r["filename"] = r["title"]
        return results

    def get_all_documents(self, limit: int = None, offset: int = 0):
        """Get all documents from document store"""
        from core.document_store import DocumentStore

        if not hasattr(self, "_document_store"):
            self._document_store = DocumentStore()
        return self._document_store.get_all_documents(limit=limit, offset=offset)

    def get_document_statistics(self):
        """Get document statistics"""
        from core.document_store import DocumentStore

        if not hasattr(self, "_document_store"):
            self._document_store = DocumentStore()
        return self._document_store.get_statistics()

    """Service for managing file operations in the application"""

    def __init__(self):
        """Initialize the file manager with proper directory structure"""
        self.upload_dir = UPLOAD_DIR
        self.save_dir = SAVE_DIR
        self.export_dir = EXPORT_DIR

        # Ensure all directories exist
        for directory in [self.upload_dir, self.save_dir, self.export_dir]:
            directory.mkdir(mode=0o755, parents=True, exist_ok=True)

    def allowed_file(self, filename: str) -> bool:
        """Check if a file has an allowed extension"""
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_uploaded_file(self, file, custom_filename: str | None = None) -> str:
        """Save an uploaded file to the upload directory with secure naming"""
        if not file:
            raise ValueError("No file provided")

        original_filename = secure_filename(file.filename)
        if not original_filename:
            raise ValueError("Invalid filename")

        if not self.allowed_file(original_filename):
            raise ValueError(
                f"File type not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Use custom filename if provided, otherwise use timestamp + original
        if custom_filename:
            filename = f"{secure_filename(custom_filename)}_{int(datetime.now().timestamp())}"
            # Preserve original extension
            if "." in original_filename:
                filename += f".{original_filename.rsplit('.', 1)[1].lower()}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{original_filename}"

        filepath = os.path.join(self.upload_dir, filename)
        file.save(filepath)
        logger.info(f"Saved file: {filepath}")

        return filepath

    def save_chat_history(self, chat_data: dict) -> str:
        """Save chat history to a JSON file"""
        if not chat_data:
            raise ValueError("No chat data provided")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_id = chat_data.get("id", str(hash(str(chat_data)))[1:8])
        filename = f"chat_{timestamp}_{chat_id}.json"

        filepath = os.path.join(self.save_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved chat history: {filepath}")
        return filepath

    def export_chat(self, chat_data: dict, export_format: str = "md") -> str:
        """Export chat to a specific format (markdown, text, etc.)"""
        if not chat_data:
            raise ValueError("No chat data provided")

        # Get chat title or generate one from first message
        title = chat_data.get("title", "chat")
        if not title and "messages" in chat_data and chat_data["messages"]:
            first_msg = chat_data["messages"][0].get("content", "")
            # Create title from first message (limited to 30 chars)
            title = "_".join(first_msg[:30].split())

        # Sanitize title for filename
        title = secure_filename(title.lower().replace(" ", "_"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{title}_{timestamp}.{export_format}"

        filepath = os.path.join(self.export_dir, filename)

        if export_format == "md":
            self._export_to_markdown(chat_data, filepath)
        elif export_format == "txt":
            self._export_to_text(chat_data, filepath)
        else:
            raise ValueError(f"Export format '{export_format}' not supported")

        logger.info(f"Exported chat: {filepath}")
        return filepath

    def _export_to_markdown(self, chat_data: dict, filepath: str) -> None:
        """Export chat data to markdown format"""
        with open(filepath, "w", encoding="utf-8") as f:
            # Write header
            title = chat_data.get("title", "Chat Export")
            f.write(f"# {title}\n\n")
            f.write(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

            # Write messages
            for msg in chat_data.get("messages", []):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if role == "user":
                    f.write(f"## User\n\n{content}\n\n")
                elif role == "assistant":
                    f.write(f"## Assistant\n\n{content}\n\n")
                elif role == "system":
                    f.write(f"## System\n\n{content}\n\n")
                else:
                    f.write(f"## {role.capitalize()}\n\n{content}\n\n")

    def _export_to_text(self, chat_data: dict, filepath: str) -> None:
        """Export chat data to plain text format"""
        with open(filepath, "w", encoding="utf-8") as f:
            # Write header
            title = chat_data.get("title", "Chat Export")
            f.write(f"{title}\n")
            f.write("=" * len(title) + "\n\n")
            f.write(f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Write messages
            for msg in chat_data.get("messages", []):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if role == "user":
                    f.write(f"USER: {content}\n\n")
                elif role == "assistant":
                    f.write(f"ASSISTANT: {content}\n\n")
                elif role == "system":
                    f.write(f"SYSTEM: {content}\n\n")
                else:
                    f.write(f"{role.upper()}: {content}\n\n")

    def get_saved_chats(self) -> list[dict]:
        """Get list of saved chat files with metadata"""
        chats = []

        for item in self.save_dir.glob("chat_*.json"):
            if item.is_file():
                try:
                    import json

                    with open(item, encoding="utf-8") as f:
                        chat_data = json.load(f)

                    # Extract basic metadata
                    chats.append(
                        {
                            "filename": item.name,
                            "path": str(item),
                            "created": datetime.fromtimestamp(item.stat().st_ctime).isoformat(),
                            "title": chat_data.get("title", item.name),
                            "message_count": len(chat_data.get("messages", [])),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error reading chat file {item}: {str(e)}")

        # Sort by creation date, newest first
        chats.sort(key=lambda x: x["created"], reverse=True)
        return chats

    def load_chat_history(self, filename: str) -> dict:
        """Load a specific chat file"""
        # Sanitize filename for security
        filename = secure_filename(filename)
        filepath = self.save_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Chat file not found: {filename}")

        try:
            import json

            with open(filepath, encoding="utf-8") as f:
                chat_data = json.load(f)

            logger.info(f"Loaded chat history: {filepath}")
            return chat_data

        except Exception as e:
            logger.error(f"Error loading chat file {filepath}: {str(e)}")
            raise ValueError(f"Failed to load chat file: {str(e)}") from e
