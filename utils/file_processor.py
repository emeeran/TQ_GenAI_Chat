from typing import Callable, Optional, Dict
from datetime import datetime
import traceback
import fitz  # PyMuPDF
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import docx
import pandas as pd
from PIL import Image
import io
import pytesseract
import markdown
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from pathlib import Path
import time

class ProcessingError(Exception):
    pass

class FileStatus:
    """File processing status tracker"""
    def __init__(self):
        self.status = {}
        self.errors = {}

    def start_processing(self, filename: str):
        self.status[filename] = {
            'status': 'processing',
            'progress': 0,
            'timestamp': datetime.now().isoformat(),
            'recoverable': True
        }

    def update_progress(self, filename: str, progress: int):
        if filename in self.status:
            self.status[filename].update({
                'progress': progress,
                'status': 'complete' if progress >= 100 else 'processing'
            })

    def set_error(self, filename: str, error: Exception, recoverable: bool = True):
        self.errors[filename] = {
            'error': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
        if filename in self.status:
            self.status[filename].update({
                'status': 'error',
                'progress': 0,
                'recoverable': recoverable
            })

    def get_status(self, filename: str) -> Dict:
        if filename not in self.status:
            raise FileNotFoundError(f'No status found for: {filename}')

        status = self.status[filename]
        error = self.errors.get(filename)

        return {
            'status': status['status'],
            'progress': status['progress'],
            'recoverable': status.get('recoverable', False),
            'error': error['error'] if error else None,
            'timestamp': error['timestamp'] if error else status['timestamp']
        }

# Initialize global status tracker
status_tracker = FileStatus()

class FileProcessor:
    """Unified file processor with optimized handling"""

    _executor = ThreadPoolExecutor(max_workers=4)
    _supported_formats = {
        'pdf': 'process_pdf',
        'epub': 'process_epub',
        'docx': 'process_docx',
        'xlsx': 'process_excel',
        'csv': 'process_excel',
        'md': 'process_markdown',
        'jpg': 'process_image',
        'jpeg': 'process_image',
        'png': 'process_image'
    }

    @classmethod
    def get_processor(cls, ext: str) -> Optional[Callable]:
        """Get appropriate processor for file type"""
        method_name = cls._supported_formats.get(ext.lower())
        return getattr(cls, method_name) if method_name else None

    @staticmethod
    async def process_pdf(content: bytes, progress_callback: Callable = None) -> str:
        """Process PDF files with optimized memory usage"""
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            total_pages = len(doc)
            text_parts = []

            for i, page in enumerate(doc):
                text_parts.append(page.get_text())
                if progress_callback:
                    progress_callback(int((i + 1) * 100 / total_pages))

            return "\n".join(text_parts)
        except Exception as e:
            raise ProcessingError(f"PDF processing error: {str(e)}")

    @staticmethod
    async def process_epub(content: bytes, progress_callback: Callable = None) -> str:
        """Process EPUB files with improved handling"""
        try:
            # Write bytes to temporary file first
            temp_file = Path(__file__).parent / f"temp_{int(time.time())}.epub"
            try:
                # Write content to temp file
                temp_file.write_bytes(content)

                # Process EPUB from file
                book = epub.read_epub(str(temp_file))
                text_parts = []
                total_items = len(list(book.get_items()))
                processed = 0

                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        try:
                            soup = BeautifulSoup(item.get_content(), 'html.parser')
                            clean_text = soup.get_text(separator='\n', strip=True)
                            if clean_text:  # Only add non-empty content
                                text_parts.append(clean_text)
                        except Exception as e:
                            current_app.logger.warning(f"Error processing EPUB item: {str(e)}")

                        processed += 1
                        if progress_callback:
                            progress_callback(int(processed * 100 / total_items))

                # Join with proper spacing
                result = "\n\n".join(filter(None, text_parts))
                return result or "No readable content found in EPUB"

            finally:
                # Clean up temp file
                if temp_file.exists():
                    temp_file.unlink()

        except Exception as e:
            current_app.logger.error(f"EPUB processing error: {str(e)}")
            raise ProcessingError(f"EPUB processing error: {str(e)}")

    @staticmethod
    async def process_docx(content: bytes, progress_callback: Callable = None) -> str:
        """Process DOCX files"""
        try:
            doc = docx.Document(io.BytesIO(content))
            text_parts = []
            total_paras = len(doc.paragraphs)

            for i, para in enumerate(doc.paragraphs):
                text_parts.append(para.text)
                if progress_callback:
                    progress_callback(int((i + 1) * 100 / total_paras))

            return "\n".join(text_parts)
        except Exception as e:
            raise ProcessingError(f"DOCX processing error: {str(e)}")

    @staticmethod
    async def process_excel(content: bytes, progress_callback: Callable = None) -> str:
        """Process Excel files"""
        try:
            df = pd.read_excel(io.BytesIO(content)) if content[-4:] == b'xlsx' else pd.read_csv(io.BytesIO(content))
            if progress_callback:
                progress_callback(50)

            # Convert to markdown table for better formatting
            result = df.to_markdown(index=False)
            if progress_callback:
                progress_callback(100)

            return result
        except Exception as e:
            raise ProcessingError(f"Excel processing error: {str(e)}")

    @staticmethod
    async def process_markdown(content: bytes, progress_callback: Callable = None) -> str:
        """Process Markdown files"""
        try:
            text = content.decode('utf-8')
            if progress_callback:
                progress_callback(50)

            # Convert to HTML then strip tags for plain text
            html = markdown.markdown(text)
            soup = BeautifulSoup(html, 'html.parser')
            if progress_callback:
                progress_callback(100)

            return soup.get_text()
        except Exception as e:
            raise ProcessingError(f"Markdown processing error: {str(e)}")

    @staticmethod
    async def process_image(content: bytes, progress_callback: Callable = None) -> str:
        """Process images with OCR"""
        try:
            image = Image.open(io.BytesIO(content))
            if progress_callback:
                progress_callback(50)

            text = pytesseract.image_to_string(image)
            if progress_callback:
                progress_callback(100)

            return text
        except Exception as e:
            raise ProcessingError(f"Image processing error: {str(e)}")

    @classmethod
    async def process_file(cls, file, filename: str) -> str:
        """Process file with improved error handling"""
        try:
            current_app.logger.info(f"Processing file: {filename}")
            status_tracker.start_processing(filename)

            if not file:
                raise ProcessingError("Empty file")

            ext = filename.rsplit('.', 1)[1].lower()
            processor = cls.get_processor(ext)

            if not processor:
                raise ProcessingError(f'Unsupported file type: {ext}')

            content = await processor(
                file.read(),
                progress_callback=lambda p: status_tracker.update_progress(filename, p)
            )

            if not content:
                raise ProcessingError("Processing resulted in empty content")

            status_tracker.update_progress(filename, 100)
            current_app.logger.info(f"Successfully processed file: {filename}")
            return content

        except Exception as e:
            current_app.logger.error(f"File processing error for {filename}: {str(e)}")
            status_tracker.set_error(filename, e)
            raise

# Make sure status_tracker is available for import
__all__ = ['FileProcessor', 'ProcessingError', 'status_tracker']
