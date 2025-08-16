"""
Request models for FastAPI endpoints.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model."""
    provider: str = Field(..., description="AI provider name")
    model: str = Field(..., description="Model name")
    message: str = Field(..., description="User message")
    persona: str | None = Field("", description="Persona key")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Temperature for generation")
    max_tokens: int = Field(4000, ge=100, le=12000, description="Maximum tokens to generate")
    output_language: str = Field("en", description="Output response language code")


class SearchContextRequest(BaseModel):
    """Search context request model."""
    message: str = Field(..., description="Search query")


class TTSRequest(BaseModel):
    """Text-to-speech request model."""
    text: str = Field(..., description="Text to convert to speech")
    voice_id: str | None = Field(None, description="Voice ID")
    lang: str = Field("en", description="Language code")


class SaveChatRequest(BaseModel):
    """Save chat request model."""
    title: str | None = Field("", description="Chat title")
    timestamp: str | None = Field(None, description="Chat timestamp")
    history: list[dict] = Field(..., description="Chat history")


class ExportChatRequest(BaseModel):
    """Export chat request model."""
    title: str | None = Field("Chat Export", description="Export title")
    timestamp: str | None = Field(None, description="Export timestamp")
    history: list[dict] = Field(..., description="Chat history")
    format: str = Field("md", description="Export format (md, txt, json)")


class SetDefaultModelRequest(BaseModel):
    """Set default model request."""
    model: str = Field(..., description="Model name to set as default")
