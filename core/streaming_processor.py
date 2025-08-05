"""
Streaming file processor with chunked processing for large files.
"""

import asyncio
import io
import logging
from collections.abc import AsyncIterator, Callable
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

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class StreamingFileProcessor:
    """
    Enhanced file processor with streaming capabilities for large files.
    """

    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size

    async def read_chunks(self, file_stream: io.BytesIO, chunk_size: int) -> AsyncIterator[bytes]:
        """
        Read file in chunks asynchronously.
        """
        while True:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            yield chunk
            # Yield control to event loop
            await asyncio.sleep(0)

    async def process_large_file(
        self,
        file_stream: io.BytesIO,
        filename: str,
        progress_callback: Callable[[int], None] = None,
    ) -> str:
        """
        Process large files in chunks to reduce memory usage.
        """
        file_extension = Path(filename).suffix.lower()
        total_size = file_stream.seek(0, 2)  # Get file size
        file_stream.seek(0)  # Reset to beginning

        if file_extension == ".pdf":
            return await self._process_large_pdf(file_stream, progress_callback, total_size)
        elif file_extension == ".csv":
            return await self._process_large_csv(file_stream, progress_callback, total_size)
        elif file_extension in [".xlsx", ".xls"]:
            return await self._process_large_excel(file_stream, progress_callback, total_size)
        else:
            # For other file types, use regular processing
            file_stream.seek(0)
            content = file_stream.read()
            return await self._process_regular_file(content, filename, progress_callback)

    async def _process_large_pdf(
        self, file_stream: io.BytesIO, progress_callback: Callable[[int], None], total_size: int
    ) -> str:
        """
        Process large PDF files page by page.
        """
        try:
            pdf_reader = PyPDF2.PdfReader(file_stream)
            total_pages = len(pdf_reader.pages)
            text_parts = []

            for i, page in enumerate(pdf_reader.pages):
                # Extract text from page
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(page_text)

                # Update progress
                progress = int((i + 1) / total_pages * 100)
                if progress_callback:
                    progress_callback(progress)

                # Yield control to event loop every few pages
                if i % 5 == 0:
                    await asyncio.sleep(0)

            text_content = "\n".join(text_parts)

            # If no text found, try OCR
            if not text_content.strip() and OCR_AVAILABLE:
                logger.info("No text found in PDF, attempting OCR")
                text_content = await self._ocr_pdf(file_stream, progress_callback)

            return text_content

        except Exception as e:
            logger.error(f"Error processing large PDF: {e}")
            raise

    async def _process_large_csv(
        self, file_stream: io.BytesIO, progress_callback: Callable[[int], None], total_size: int
    ) -> str:
        """
        Process large CSV files in chunks.
        """
        try:
            file_stream.seek(0)

            # Use pandas with chunking for large CSVs
            chunk_iter = pd.read_csv(
                file_stream,
                chunksize=1000,  # Process 1000 rows at a time
                encoding="utf-8",
                on_bad_lines="skip",
            )

            processed_chunks = []
            total_rows = 0

            for i, chunk in enumerate(chunk_iter):
                # Convert chunk to string representation
                chunk_text = chunk.to_string(index=False)
                processed_chunks.append(f"Chunk {i + 1}:\n{chunk_text}\n")

                total_rows += len(chunk)

                # Update progress (estimate)
                if progress_callback:
                    progress_callback(min(90, (i + 1) * 10))

                # Yield control to event loop
                await asyncio.sleep(0)

            result = "\n".join(processed_chunks)
            if progress_callback:
                progress_callback(100)

            return result

        except Exception as e:
            logger.error(f"Error processing large CSV: {e}")
            # Fallback to reading as text
            file_stream.seek(0)
            content = file_stream.read().decode("utf-8", errors="ignore")
            return content

    async def _process_large_excel(
        self, file_stream: io.BytesIO, progress_callback: Callable[[int], None], total_size: int
    ) -> str:
        """
        Process large Excel files sheet by sheet.
        """
        try:
            file_stream.seek(0)

            # Read Excel file
            excel_file = pd.ExcelFile(file_stream)
            sheet_names = excel_file.sheet_names
            processed_sheets = []

            for i, sheet_name in enumerate(sheet_names):
                try:
                    # Read sheet in chunks if it's large
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)

                    if len(df) > 10000:  # Large sheet, process in chunks
                        chunks = [df[i : i + 1000] for i in range(0, len(df), 1000)]
                        sheet_parts = []

                        for chunk in chunks:
                            chunk_text = chunk.to_string(index=False)
                            sheet_parts.append(chunk_text)
                            await asyncio.sleep(0)  # Yield control

                        sheet_content = "\n".join(sheet_parts)
                    else:
                        sheet_content = df.to_string(index=False)

                    processed_sheets.append(f"Sheet: {sheet_name}\n{sheet_content}\n")

                    # Update progress
                    progress = int((i + 1) / len(sheet_names) * 100)
                    if progress_callback:
                        progress_callback(progress)

                    await asyncio.sleep(0)

                except Exception as e:
                    logger.warning(f"Error processing sheet {sheet_name}: {e}")
                    continue

            return "\n".join(processed_sheets)

        except Exception as e:
            logger.error(f"Error processing large Excel: {e}")
            raise

    async def _ocr_pdf(
        self, file_stream: io.BytesIO, progress_callback: Callable[[int], None]
    ) -> str:
        """
        Perform OCR on PDF pages.
        """
        if not OCR_AVAILABLE:
            return ""

        try:
            file_stream.seek(0)

            # Convert PDF to images
            images = convert_from_bytes(file_stream.read())
            text_parts = []

            for i, image in enumerate(images):
                # Perform OCR on image
                text = pytesseract.image_to_string(image)
                if text.strip():
                    text_parts.append(text)

                # Update progress
                progress = int((i + 1) / len(images) * 100)
                if progress_callback:
                    progress_callback(progress)

                # Yield control to event loop
                await asyncio.sleep(0)

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return ""

    async def _process_regular_file(
        self, content: bytes, filename: str, progress_callback: Callable[[int], None]
    ) -> str:
        """
        Process regular-sized files using existing methods.
        """
        file_extension = Path(filename).suffix.lower()

        if progress_callback:
            progress_callback(25)

        try:
            if file_extension == ".docx":
                result = await self._process_docx(content)
            elif file_extension == ".txt" or file_extension == ".md":
                result = content.decode("utf-8", errors="ignore")
            elif file_extension in [".png", ".jpg", ".jpeg"]:
                result = await self._process_image(content)
            else:
                result = content.decode("utf-8", errors="ignore")

            if progress_callback:
                progress_callback(100)

            return result

        except Exception as e:
            logger.error(f"Error processing regular file: {e}")
            if progress_callback:
                progress_callback(100)
            return f"Error processing file: {str(e)}"

    async def _process_docx(self, content: bytes) -> str:
        """Process DOCX files."""
        try:
            doc_file = io.BytesIO(content)
            doc = docx.Document(doc_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error processing DOCX: {e}")
            return f"Error processing DOCX file: {str(e)}"

    async def _process_image(self, content: bytes) -> str:
        """Process image files with optional OCR."""
        try:
            image_file = io.BytesIO(content)
            image = Image.open(image_file)

            # Extract basic metadata
            metadata = {"format": image.format, "size": image.size, "mode": image.mode}

            result = f"Image metadata: {metadata}"

            # Attempt OCR if available
            if OCR_AVAILABLE:
                try:
                    ocr_text = pytesseract.image_to_string(image)
                    if ocr_text.strip():
                        result += f"\n\nExtracted text:\n{ocr_text}"
                except Exception as e:
                    logger.warning(f"OCR failed for image: {e}")

            return result

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return f"Error processing image file: {str(e)}"

    async def get_file_info(self, content: bytes, filename: str) -> dict[str, Any]:
        """
        Get file information without full processing.
        """
        file_path = Path(filename)
        file_size = len(content)

        info = {
            "filename": filename,
            "size": file_size,
            "extension": file_path.suffix.lower(),
            "processing_method": "regular",
        }

        # Determine processing method based on size and type
        if file_size > 10 * 1024 * 1024:  # 10MB
            info["processing_method"] = "streaming"

        # Additional file-specific info
        if file_path.suffix.lower() == ".pdf":
            try:
                pdf_file = io.BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                info["pages"] = len(pdf_reader.pages)
            except Exception:
                pass

        elif file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            try:
                image_file = io.BytesIO(content)
                image = Image.open(image_file)
                info["image_size"] = image.size
                info["image_format"] = image.format
            except Exception:
                pass

        return info
