"""
File Manager Service
Handles file operations, storage, and retrieval.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from werkzeug.utils import secure_filename

from flask import current_app
from config.settings import ALLOWED_EXTENSIONS, SAVE_DIR, EXPORT_DIR, UPLOAD_DIR


class FileManager:
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
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def save_uploaded_file(self, file, custom_filename: Optional[str] = None) -> str:
        """Save an uploaded file to the upload directory with secure naming"""
        if not file:
            raise ValueError("No file provided")
            
        original_filename = secure_filename(file.filename)
        if not original_filename:
            raise ValueError("Invalid filename")
            
        if not self.allowed_file(original_filename):
            raise ValueError(f"File type not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Use custom filename if provided, otherwise use timestamp + original
        if custom_filename:
            filename = f"{secure_filename(custom_filename)}_{int(datetime.now().timestamp())}"
            # Preserve original extension
            if '.' in original_filename:
                filename += f".{original_filename.rsplit('.', 1)[1].lower()}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{original_filename}"
        
        filepath = os.path.join(self.upload_dir, filename)
        file.save(filepath)
        current_app.logger.info(f"Saved file: {filepath}")
        
        return filepath
        
    def save_chat_history(self, chat_data: Dict) -> str:
        """Save chat history to a JSON file"""
        if not chat_data:
            raise ValueError("No chat data provided")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_id = chat_data.get("id", str(hash(str(chat_data)))[1:8])
        filename = f"chat_{timestamp}_{chat_id}.json"
        
        filepath = os.path.join(self.save_dir, filename)
        
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
        current_app.logger.info(f"Saved chat history: {filepath}")
        return filepath
        
    def export_chat(self, chat_data: Dict, format: str = "md") -> str:
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
        filename = f"{title}_{timestamp}.{format}"
        
        filepath = os.path.join(self.export_dir, filename)
        
        if format == "md":
            self._export_to_markdown(chat_data, filepath)
        else:
            raise ValueError(f"Export format '{format}' not supported")
            
        current_app.logger.info(f"Exported chat: {filepath}")
        return filepath
        
    def _export_to_markdown(self, chat_data: Dict, filepath: str) -> None:
        """Export chat data to markdown format"""
        with open(filepath, 'w', encoding='utf-8') as f:
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
    
    def get_saved_chats(self) -> List[Dict]:
        """Get list of saved chat files with metadata"""
        chats = []
        
        for item in self.save_dir.glob("chat_*.json"):
            if item.is_file():
                try:
                    import json
                    with open(item, 'r', encoding='utf-8') as f:
                        chat_data = json.load(f)
                    
                    # Extract basic metadata
                    chats.append({
                        "filename": item.name,
                        "path": str(item),
                        "created": datetime.fromtimestamp(item.stat().st_ctime).isoformat(),
                        "title": chat_data.get("title", item.name),
                        "message_count": len(chat_data.get("messages", [])),
                    })
                except Exception as e:
                    current_app.logger.error(f"Error reading chat file {item}: {str(e)}")
        
        # Sort by creation date, newest first
        chats.sort(key=lambda x: x["created"], reverse=True)
        return chats
