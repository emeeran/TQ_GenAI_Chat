"""
File Manager Service
Handles file operations, storage, and retrieval.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from config.settings import ALLOWED_EXTENSIONS, EXPORT_DIR, SAVE_DIR, UPLOAD_DIR

# Create a logger that doesn't require Flask context
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)


def secure_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for filesystem use.

    This is a simplified version of werkzeug's secure_filename.
    It removes any characters that might be problematic in filenames.

    Args:
        filename: The original filename

    Returns:
        A sanitized filename safe for use in filesystem operations
    """
    # Remove any non-ASCII characters
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Replace spaces and other separators with underscores
    filename = re.sub(r"[^\w\s.-]", "", filename)
    filename = re.sub(r"[-\s]+", "_", filename)

    # Remove leading/trailing dots and underscores
    filename = filename.strip("._")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"

    return filename


class FileManager:
    """Service for managing file operations in the application"""

    def __init__(self) -> None:
        """Initialize the file manager with proper directory structure"""
        self.upload_dir: Path = UPLOAD_DIR
        self.save_dir: Path = SAVE_DIR
        self.export_dir: Path = EXPORT_DIR
        self._document_store: Optional[Any] = None

        # Ensure all directories exist
        for directory in [self.upload_dir, self.save_dir, self.export_dir]:
            directory.mkdir(mode=0o755, parents=True, exist_ok=True)

    def get_document(self, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by filename (title)."""
        from core.document_store import DocumentStore

        if self._document_store is None:
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
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Add a document to the document store (proxy)."""
        from core.document_store import DocumentStore

        if self._document_store is None:
            self._document_store = DocumentStore()
        return self._document_store.add_document(
            content=content,
            title=filename,
            file_path=None,
            doc_type=doc_type,
            metadata=metadata,
            user_id=user_id,
        )

    def search_documents(self, query: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Proxy to DocumentStore.search_documents for context search."""
        from core.document_store import DocumentStore

        if self._document_store is None:
            self._document_store = DocumentStore()
        results = self._document_store.search_documents(query, limit=top_n)
        # Optionally add similarity score if not present
        for r in results:
            if "similarity" not in r:
                r["similarity"] = 1.0  # Placeholder if not calculated
            if "filename" not in r and "title" in r:
                r["filename"] = r["title"]
        return results

    def get_all_documents(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all documents from document store"""
        from core.document_store import DocumentStore

        if self._document_store is None:
            self._document_store = DocumentStore()
        return self._document_store.get_all_documents(limit=limit, offset=offset)

    def get_document_statistics(self) -> Dict[str, Any]:
        """Get document statistics"""
        from core.document_store import DocumentStore

        if self._document_store is None:
            self._document_store = DocumentStore()
        return self._document_store.get_statistics()

    def allowed_file(self, filename: str) -> bool:
        """Check if a file has an allowed extension"""
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    def save_uploaded_file(
        self, file: Any, custom_filename: Optional[str] = None
    ) -> str:
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
            filename = (
                f"{secure_filename(custom_filename)}_{int(datetime.now().timestamp())}"
            )
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

    def save_chat_history(self, chat_data: Dict[str, Any]) -> str:
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

    def export_chat(self, chat_data: Dict[str, Any], export_format: str = "md") -> str:
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

    def _export_to_markdown(self, chat_data: Dict[str, Any], filepath: str) -> None:
        """Export chat data to markdown format with clean formatting"""
        with open(filepath, "w", encoding="utf-8") as f:
            # Write header with proper metadata
            title = chat_data.get("title", "Chat Export")
            timestamp = chat_data.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            f.write(f"# {title}\n\n")
            f.write(f"**Exported:** {timestamp}\n")
            f.write("**Generated by:** TQ GenAI Chat\n\n")
            f.write("---\n\n")

            # Write messages with clean formatting
            for msg in chat_data.get("messages", []):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                # Clean up content if it's a response object
                if isinstance(content, dict):
                    # Extract text from response object
                    if "text" in content:
                        content = content["text"]
                    else:
                        content = str(content)
                elif isinstance(content, str) and content.startswith("{'text':"):
                    # Handle string representation of dict
                    try:
                        import ast

                        content_dict = ast.literal_eval(content)
                        if isinstance(content_dict, dict) and "text" in content_dict:
                            content = content_dict["text"]
                    except Exception:
                        # If parsing fails, clean up manually
                        if content.startswith("{'text': \""):
                            # Extract content between the quotes
                            start_idx = content.find("{'text': \"") + 10
                            end_idx = content.find("\", 'metadata':")
                            if end_idx > start_idx:
                                content = content[start_idx:end_idx]
                                # Unescape common escape sequences
                                content = (
                                    content.replace("\\n", "\n")
                                    .replace('\\"', '"')
                                    .replace("\\u202f", " ")
                                )

                # Format based on role
                if role == "user":
                    f.write(f"## 👤 User\n\n{content}\n\n---\n\n")
                elif role == "assistant":
                    f.write(f"## 🤖 Assistant\n\n{content}\n\n---\n\n")
                elif role == "system":
                    f.write(f"## ⚙️ System\n\n{content}\n\n---\n\n")
                else:
                    f.write(f"## {role.capitalize()}\n\n{content}\n\n---\n\n")

            # Remove the last separator
            f.seek(f.tell() - 6)
            f.truncate()
            f.write("\n\n")

            # Add footer
            f.write("---\n\n")
            f.write("*This conversation was exported from TQ GenAI Chat*\n")

    def _export_to_text(self, chat_data: Dict[str, Any], filepath: str) -> None:
        """Export chat data to plain text format with clean formatting"""
        with open(filepath, "w", encoding="utf-8") as f:
            # Write header
            title = chat_data.get("title", "Chat Export")
            timestamp = chat_data.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            f.write(f"{title}\n")
            f.write("=" * len(title) + "\n\n")
            f.write(f"Exported: {timestamp}\n")
            f.write("Generated by: TQ GenAI Chat\n\n")
            f.write("-" * 50 + "\n\n")

            # Write messages with clean formatting
            for msg in chat_data.get("messages", []):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                # Clean up content if it's a response object (same logic as markdown)
                if isinstance(content, dict):
                    if "text" in content:
                        content = content["text"]
                    else:
                        content = str(content)
                elif isinstance(content, str) and content.startswith("{'text':"):
                    try:
                        import ast

                        content_dict = ast.literal_eval(content)
                        if isinstance(content_dict, dict) and "text" in content_dict:
                            content = content_dict["text"]
                    except Exception:
                        if content.startswith("{'text': \""):
                            start_idx = content.find("{'text': \"") + 10
                            end_idx = content.find("\", 'metadata':")
                            if end_idx > start_idx:
                                content = content[start_idx:end_idx]
                                content = (
                                    content.replace("\\n", "\n")
                                    .replace('\\"', '"')
                                    .replace("\\u202f", " ")
                                )

                if role == "user":
                    f.write(f"👤 USER:\n{content}\n\n{'-' * 50}\n\n")
                elif role == "assistant":
                    f.write(f"🤖 ASSISTANT:\n{content}\n\n{'-' * 50}\n\n")
                elif role == "system":
                    f.write(f"⚙️ SYSTEM:\n{content}\n\n{'-' * 50}\n\n")
                else:
                    f.write(f"{role.upper()}:\n{content}\n\n{'-' * 50}\n\n")

            # Add footer
            f.write("\nThis conversation was exported from TQ GenAI Chat\n")

    def get_saved_chats(self) -> List[Dict[str, Any]]:
        """Get list of saved chat files with metadata"""
        chats: List[Dict[str, Any]] = []

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
                            "created": datetime.fromtimestamp(
                                item.stat().st_ctime
                            ).isoformat(),
                            "title": chat_data.get("title", item.name),
                            "message_count": len(chat_data.get("messages", [])),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error reading chat file {item}: {str(e)}")

        # Sort by creation date, newest first
        chats.sort(key=lambda x: x["created"], reverse=True)
        return chats

    def load_chat_history(self, filename: str) -> Dict[str, Any]:
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
