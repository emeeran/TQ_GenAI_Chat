import os
import io
import re
import logging
from pathlib import Path
import docx
import markdown
import json
import csv
from typing import Dict, Any, Tuple, List, Union, BinaryIO
import asyncio
import time

# Global status tracking dictionary
status_tracker = {}

class ProcessingError(Exception):
    """Exception raised for file processing errors."""
    pass

class FileProcessor:
    """Process uploaded files into text content."""

    logger = logging.getLogger(__name__)

    @classmethod
    async def process_file(cls, file: BinaryIO, filename: str) -> str:
        """Process a file and extract its text content.

        Args:
            file: File object
            filename: Name of the file

        Returns:
            str: Extracted text content

        Raises:
            ProcessingError: If file processing fails
        """
        # Update status to processing
        status_tracker[filename] = {'status': 'processing', 'progress': 0}

        try:
            # Determine file type from extension
            ext = Path(filename).suffix.lower()

            # Process based on file type
            if ext in ['.docx', '.doc']:
                content = await cls._process_docx(file, filename)
            elif ext in ['.pdf']:
                content = await cls._process_pdf(file, filename)
            elif ext in ['.md', '.markdown']:
                content = await cls._process_markdown(file, filename)
            elif ext in ['.txt']:
                content = await cls._process_text(file, filename)
            elif ext in ['.json']:
                content = await cls._process_json(file, filename)
            elif ext in ['.csv']:
                content = await cls._process_csv(file, filename)
            elif ext in ['.jpg', '.jpeg', '.png']:
                content = await cls._process_image(file, filename)
            else:
                raise ProcessingError(f"Unsupported file type: {ext}")

            # Update status to complete
            status_tracker[filename] = {'status': 'complete', 'progress': 100}
            return content

        except Exception as e:
            # Update status to failed
            cls.logger.error(f"Error processing file {filename}: {str(e)}")
            status_tracker[filename] = {
                'status': 'failed',
                'error': str(e),
                'progress': 0
            }
            raise ProcessingError(f"Failed to process {filename}: {str(e)}")

    @classmethod
    async def _process_docx(cls, file: BinaryIO, filename: str) -> str:
        """Process a DOCX file."""
        status_tracker[filename]['status'] = 'extracting text from DOCX'

        try:
            # Read the file into a BytesIO object
            file_bytes = io.BytesIO(file.read())

            # Use python-docx to extract text
            doc = docx.Document(file_bytes)

            # Extract text from paragraphs with progress updates
            paragraphs = []
            total_paras = len(doc.paragraphs)

            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    paragraphs.append(para.text)

                # Update progress every 10 paragraphs or at the end
                if i % 10 == 0 or i == total_paras - 1:
                    progress = min(95, int((i / total_paras) * 100))
                    status_tracker[filename]['progress'] = progress
                    status_tracker[filename]['status'] = f'extracting text ({progress}%)'
                    await asyncio.sleep(0.01)  # Yield to event loop

            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = ' | '.join(cell.text for cell in row.cells)
                    if row_text.strip():
                        paragraphs.append(row_text)

            return '\n\n'.join(paragraphs)

        except Exception as e:
            cls.logger.error(f"Error processing DOCX file {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process DOCX: {str(e)}")

    @classmethod
    async def _process_pdf(cls, file: BinaryIO, filename: str) -> str:
        """Process a PDF file."""
        status_tracker[filename]['status'] = 'extracting text from PDF'

        try:
            # For PDF processing, we'll need PyPDF2 or pdfminer.six
            # This is a placeholder - install the required package first
            raise ProcessingError("PDF processing requires additional packages. Install PyPDF2 or pdfminer.six")
        except ImportError:
            raise ProcessingError("PDF processing requires PyPDF2 or pdfminer.six")
        except Exception as e:
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
