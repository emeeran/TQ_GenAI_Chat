import io
from datetime import datetime

import docx
import pandas as pd
import PyPDF2
from PIL import Image


class ProcessingError(Exception):
    pass

class FileStatus:
    def __init__(self):
        self._statuses = {}

    def start(self, filename: str):
        self._statuses[filename] = {
            'status': 'Processing',
            'progress': 0,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

    def update(self, filename: str, progress: int):
        if filename in self._statuses:
            self._statuses[filename].update({
                'progress': progress,
                'timestamp': datetime.now().isoformat()
            })

    def complete(self, filename: str):
        if filename in self._statuses:
            self._statuses[filename].update({
                'status': 'Complete',
                'progress': 100,
                'timestamp': datetime.now().isoformat()
            })

    def error(self, filename: str, error: str):
        if filename in self._statuses:
            self._statuses[filename].update({
                'status': 'Error',
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            })

    def get(self, filename: str) -> dict:
        return self._statuses.get(filename, {
            'status': 'Not Found',
            'progress': 0,
            'error': None
        })

# Global status tracker
status_tracker = FileStatus()

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md', 'csv', 'xlsx', 'jpg', 'jpeg', 'png'}

class FileProcessor:
    """Handle different file types with proper error handling"""

    @staticmethod
    async def process_file(file_obj, filename: str) -> str:
        """Process uploaded file and return its content"""
        try:
            status_tracker.start(filename)
            ext = filename.rsplit('.', 1)[1].lower()

            if ext not in ALLOWED_EXTENSIONS:
                raise ProcessingError(f'Unsupported file type: {ext}')

            content = file_obj.read()
            if not content:
                raise ProcessingError('Empty file')

            # Process based on file type
            if ext == 'pdf':
                text = await FileProcessor._process_pdf(content)
            elif ext == 'docx':
                text = await FileProcessor._process_docx(content)
            elif ext in ['txt', 'md']:
                text = await FileProcessor._process_text(content)
            elif ext == 'csv':
                text = await FileProcessor._process_csv(content)
            elif ext == 'xlsx':
                text = await FileProcessor._process_excel(content)
            elif ext in ['jpg', 'jpeg', 'png']:
                text = await FileProcessor._process_image(content)
            else:
                raise ProcessingError(f'Unexpected file type: {ext}')

            status_tracker.complete(filename)
            return text

        except Exception as e:
            status_tracker.error(filename, str(e))
            raise ProcessingError(f'Error processing {filename}: {str(e)}')

    @staticmethod
    async def _process_pdf(content: bytes) -> str:
        try:
            pdf = PyPDF2.PdfReader(io.BytesIO(content))
            return '\n\n'.join(page.extract_text() for page in pdf.pages)
        except Exception as e:
            raise ProcessingError(f'PDF processing error: {str(e)}')

    @staticmethod
    async def _process_docx(content: bytes) -> str:
        try:
            doc = docx.Document(io.BytesIO(content))
            return '\n\n'.join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as e:
            raise ProcessingError(f'DOCX processing error: {str(e)}')

    @staticmethod
    async def _process_text(content: bytes) -> str:
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return content.decode('latin-1')
            except Exception as e:
                raise ProcessingError(f'Text decoding error: {str(e)}')

    @staticmethod
    async def _process_csv(content: bytes) -> str:
        try:
            df = pd.read_csv(io.BytesIO(content))
            return df.to_string()
        except Exception as e:
            raise ProcessingError(f'CSV processing error: {str(e)}')

    @staticmethod
    async def _process_excel(content: bytes) -> str:
        try:
            df = pd.read_excel(io.BytesIO(content))
            return df.to_string()
        except Exception as e:
            raise ProcessingError(f'Excel processing error: {str(e)}')

    @staticmethod
    async def _process_image(content: bytes) -> str:
        try:
            img = Image.open(io.BytesIO(content))
            return f"Image: {img.format} {img.size}x{img.size} {img.mode}"
        except Exception as e:
            raise ProcessingError(f'Image processing error: {str(e)}')

# Make sure status_tracker is available for import
__all__ = ['FileProcessor', 'ProcessingError', 'status_tracker']
