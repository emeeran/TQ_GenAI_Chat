"""
Optimized file processor module.
Consolidates file processing functionality with improved error handling,
performance optimizations, and modern Python features.
"""

import asyncio
import io
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import docx
import pandas as pd
import PyPDF2
from PIL import Image

# OCR dependencies
try:
    import pytesseract
    from pdf2image import convert_from_bytes
except ImportError:
    pytesseract = None
    convert_from_bytes = None


class ProcessingError(Exception):
    """Custom exception for file processing errors."""

    def __init__(self, message: str, file_type: str | None = None, recoverable: bool = True):
        super().__init__(message)
        self.file_type = file_type
        self.recoverable = recoverable


class ProcessingStatus:
    """Thread-safe status tracker for file processing operations."""

    def __init__(self):
        self._statuses: dict[str, dict[str, Any]] = {}
        self._errors: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def start_processing(self, filename: str) -> None:
        """Initialize processing status for a file."""
        async with self._lock:
            self._statuses[filename] = {
                "status": "processing",
                "progress": 0,
                "timestamp": datetime.now().isoformat(),
                "recoverable": True,
            }

    async def update_progress(self, filename: str, progress: int) -> None:
        """Update processing progress."""
        async with self._lock:
            if filename in self._statuses:
                self._statuses[filename].update(
                    {
                        "progress": min(100, max(0, progress)),
                        "status": "complete" if progress >= 100 else "processing",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    async def set_error(self, filename: str, error: Exception) -> None:
        """Record processing error."""
        async with self._lock:
            self._errors[filename] = {
                "error": str(error),
                "type": type(error).__name__,
                "timestamp": datetime.now().isoformat(),
                "recoverable": getattr(error, "recoverable", False),
            }
            if filename in self._statuses:
                self._statuses[filename].update({"status": "error", "error": str(error)})

    def get_status(self, filename: str) -> dict[str, Any]:
        """Get current status for a file."""
        if filename not in self._statuses:
            raise FileNotFoundError(f"No status found for: {filename}")
        return self._statuses[filename].copy()

    def get_error(self, filename: str) -> dict[str, Any] | None:
        """Get error information for a file."""
        return self._errors.get(filename)


class FileProcessor:
    """
    Optimized file processor with async support and enhanced error handling.

    Supports: PDF, DOCX, TXT, CSV, XLSX, images (PNG, JPG, JPEG)
    """

    # Class-level processor mapping for better performance
    _PROCESSORS = {
        "pdf": "_process_pdf",
        "docx": "_process_docx",
        "txt": "_process_text",
        "md": "_process_text",
        "csv": "_process_csv",
        "xlsx": "_process_excel",
        "xls": "_process_excel",
        "png": "_process_image",
        "jpg": "_process_image",
        "jpeg": "_process_image",
    }

    def __init__(self):
        self.status_tracker = ProcessingStatus()

    @classmethod
    async def process_file(
        cls,
        content: bytes,
        filename: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Process file content and return extracted text.

        Args:
            content: File content as bytes
            filename: Original filename with extension
            progress_callback: Optional callback for progress updates

        Returns:
            Extracted text content

        Raises:
            ProcessingError: If file processing fails
        """
        processor = cls()
        return await processor._process_file_internal(content, filename, progress_callback)

    async def _process_file_internal(
        self,
        content: bytes,
        filename: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """Internal file processing implementation."""

        await self.status_tracker.start_processing(filename)

        try:
            # Validate input
            if not content:
                raise ProcessingError("Empty file content", recoverable=False)

            # Extract file extension
            ext = Path(filename).suffix.lstrip(".").lower()
            if not ext:
                raise ProcessingError("File has no extension", recoverable=False)

            # Get processor method
            processor_method = self._PROCESSORS.get(ext)
            if not processor_method:
                raise ProcessingError(
                    f"Unsupported file type: .{ext}", file_type=ext, recoverable=False
                )

            # Update progress
            if progress_callback:
                progress_callback(25)
            await self.status_tracker.update_progress(filename, 25)

            # Process file
            method = getattr(self, processor_method)
            result = await asyncio.get_event_loop().run_in_executor(None, method, content, filename)

            # Update progress
            if progress_callback:
                progress_callback(100)
            await self.status_tracker.update_progress(filename, 100)

            return result

        except Exception as e:
            await self.status_tracker.set_error(filename, e)
            if isinstance(e, ProcessingError):
                raise
            raise ProcessingError(f"Processing failed: {str(e)}", ext) from e

    def _process_pdf(self, content: bytes, filename: str) -> str:
        """Extract text from PDF files. Uses OCR fallback if no text is found."""
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            result = "\n\n".join(text_parts)
            if result.strip():
                return result
            # Fallback to OCR if no text found
            if pytesseract is None or convert_from_bytes is None:
                raise ProcessingError(
                    "PDF contains no extractable text and OCR dependencies are not installed."
                )
            images = convert_from_bytes(content)
            ocr_text = []
            for img in images:
                # Optional: preprocess image for better OCR (grayscale, threshold)
                img = img.convert("L")
                ocr_text.append(pytesseract.image_to_string(img))
            ocr_result = "\n\n".join(ocr_text)
            if not ocr_result.strip():
                raise ProcessingError("PDF contains no extractable text (even with OCR)")
            return ocr_result
        except Exception as e:
            raise ProcessingError(f"PDF processing error: {str(e)}") from e

    def _process_docx(self, content: bytes, filename: str) -> str:
        """Extract text from DOCX files."""
        try:
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)

            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            result = "\n\n".join(paragraphs)

            if not result.strip():
                raise ProcessingError("DOCX contains no extractable text")

            return result

        except Exception as e:
            raise ProcessingError(f"DOCX processing error: {str(e)}") from e

    def _process_text(self, content: bytes, filename: str) -> str:
        """Process plain text files with encoding detection."""
        encodings = ["utf-8", "utf-16", "iso-8859-1", "cp1252"]

        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue

        raise ProcessingError("Unable to decode text file with supported encodings")

    def _process_csv(self, content: bytes, filename: str) -> str:
        """Process CSV files."""
        try:
            csv_file = io.StringIO(content.decode("utf-8"))
            df = pd.read_csv(csv_file)
            return df.to_string(index=False)
        except Exception as e:
            raise ProcessingError(f"CSV processing error: {str(e)}") from e

    def _process_excel(self, content: bytes, filename: str) -> str:
        """Process Excel files."""
        try:
            excel_file = io.BytesIO(content)
            df = pd.read_excel(excel_file)
            return df.to_string(index=False)
        except Exception as e:
            raise ProcessingError(f"Excel processing error: {str(e)}") from e

    def _process_image(self, content: bytes, filename: str) -> str:
        """Process image files (basic metadata extraction)."""
        try:
            image_file = io.BytesIO(content)
            img = Image.open(image_file)
            return f"Image: {img.format} {img.size[0]}x{img.size[1]} {img.mode}"
        except Exception as e:
            raise ProcessingError(f"Image processing error: {str(e)}") from e


# Global status tracker instance
status_tracker = ProcessingStatus()
