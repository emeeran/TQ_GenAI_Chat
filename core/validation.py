"""Request validation using Pydantic"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatMessageModel(BaseModel):
    """Chat message validation model"""

    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=50000)


class ChatRequestModel(BaseModel):
    """Chat request validation model"""

    message: str | None = Field(None, max_length=50000)
    provider: str = Field(default="openai", pattern=r"^[a-zA-Z0-9_-]+$")
    model: str = Field(default="", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, gt=0, le=100000)
    persona: str | None = Field(None, max_length=10000)
    history: list[ChatMessageModel] = Field(default_factory=list)

    @field_validator("history")
    @classmethod
    def validate_history_length(cls, v):
        if len(v) > 100:  # Reasonable limit
            raise ValueError("Chat history too long")
        return v


@dataclass
class ValidationResult:
    """Validation result container"""

    is_valid: bool
    errors: list[str]
    data: dict[str, Any] | None = None


class ChatRequestValidator:
    """Validator for chat requests"""

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate chat request data"""
        try:
            model = ChatRequestModel(**data)
            return ValidationResult(is_valid=True, errors=[], data=model.dict())
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[str(e)])


class FileUploadValidator:
    """Validator for file uploads"""

    ALLOWED_EXTENSIONS = {
        "pdf",
        "docx",
        "xlsx",
        "csv",
        "txt",
        "md",
        "png",
        "jpg",
        "jpeg",
        "gif",
    }
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

    def validate_file(self, filename: str, file_size: int) -> ValidationResult:
        """Validate uploaded file"""
        errors = []

        # Check extension
        if not self._allowed_file(filename):
            errors.append(f"File type not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}")

        # Check size
        if file_size > self.MAX_FILE_SIZE:
            errors.append(f"File too large. Max size: {self.MAX_FILE_SIZE // (1024*1024)}MB")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return "." in filename and filename.rsplit(".", 1)[1].lower() in self.ALLOWED_EXTENSIONS
