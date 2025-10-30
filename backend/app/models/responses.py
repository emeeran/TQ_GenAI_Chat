"""
Response models for FastAPI endpoints.
"""

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Chat response model."""
    response: dict = Field(..., description="AI response with text and metadata")
    verification: dict | None = Field(None, description="Verification response")


class SearchContextResponse(BaseModel):
    """Search context response model."""
    results: list[dict] = Field(..., description="Search results")


class ModelsResponse(BaseModel):
    """Models response model."""
    models: list[str] = Field(..., description="Available models")
    default: str | None = Field(None, description="Default model")


class DocumentsResponse(BaseModel):
    """Documents response model."""
    documents: list[dict] = Field(..., description="Document list")
    stats: dict = Field(..., description="Document statistics")


class TTSVoicesResponse(BaseModel):
    """TTS voices response model."""
    voices: list[dict] = Field(..., description="Available voices")


class PersonasResponse(BaseModel):
    """Personas response model."""
    personas: list[dict] = Field(..., description="Available personas")


class SavedChatsResponse(BaseModel):
    """Saved chats response model."""
    chats: list[dict] = Field(..., description="Saved chat files")


class LoadChatResponse(BaseModel):
    """Load chat response model."""
    history: list[dict] = Field(..., description="Chat history")
    title: str = Field(..., description="Chat title")
    timestamp: str = Field(..., description="Chat timestamp")


class FileUploadResponse(BaseModel):
    """File upload response model."""
    results: list[dict] = Field(..., description="Upload results")


class FileStatusResponse(BaseModel):
    """File status response model."""
    status: str = Field(..., description="Processing status")
    timestamp: float | None = Field(None, description="Status timestamp")
    size: int | None = Field(None, description="Processed content size")
    error: str | None = Field(None, description="Error message if failed")


class SuccessResponse(BaseModel):
    """Generic success response model."""
    message: str = Field(..., description="Success message")
    filename: str | None = Field(None, description="Associated filename")
    path: str | None = Field(None, description="Associated file path")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    framework: str = Field(..., description="Framework name")
    providers: list[str] = Field(..., description="Available AI providers")
    documents: int = Field(..., description="Number of documents loaded")
