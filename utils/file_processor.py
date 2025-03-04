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
            cls.logger.error(f"Error processing PDF file {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process PDF: {str(e)}")

    @classmethod
    async def _process_markdown(cls, file: BinaryIO, filename: str) -> str:
        """Process a Markdown file."""
        status_tracker[filename]['status'] = 'processing Markdown'

        try:
            # Read the markdown content
            md_content = file.read().decode('utf-8')

            # Return the raw markdown and the HTML version
            html_content = markdown.markdown(md_content)

            # Extract text from HTML (simple approach)
            text_content = re.sub(r'<[^>]+>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()

            return f"{md_content}\n\n--- Rendered Content ---\n\n{text_content}"

        except Exception as e:
            cls.logger.error(f"Error processing Markdown file {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process Markdown: {str(e)}")

    @classmethod
    async def _process_text(cls, file: BinaryIO, filename: str) -> str:
        """Process a plain text file."""
        status_tracker[filename]['status'] = 'processing text'

        try:
            # Read the text content
            text_content = file.read().decode('utf-8')
            return text_content

        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    file.seek(0)
                    text_content = file.read().decode(encoding)
                    return text_content
                except:
                    pass

            raise ProcessingError("Could not decode text file with any supported encoding")
        except Exception as e:
            cls.logger.error(f"Error processing text file {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process text file: {str(e)}")

    @classmethod
    async def _process_json(cls, file: BinaryIO, filename: str) -> str:
        """Process a JSON file."""
        status_tracker[filename]['status'] = 'processing JSON'

        try:
            # Read the JSON content
            json_content = file.read().decode('utf-8')

            # Parse JSON to validate and format it
            parsed = json.loads(json_content)

            # Format JSON for readability
            formatted_json = json.dumps(parsed, indent=2)

            # For large JSON files, also include a summary
            summary = cls._summarize_json(parsed)

            return f"{formatted_json}\n\n--- JSON Summary ---\n\n{summary}"

        except Exception as e:
            cls.logger.error(f"Error processing JSON file {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process JSON: {str(e)}")

    @classmethod
    def _summarize_json(cls, data: Any, max_items: int = 3) -> str:
        """Create a summary of a JSON structure."""
        if isinstance(data, dict):
            keys = list(data.keys())[:max_items]
            if len(data) > max_items:
                keys_str = ', '.join(repr(k) for k in keys)
                return f"Dictionary with {len(data)} keys, including: {keys_str}, ..."
            else:
                return f"Dictionary with keys: {', '.join(repr(k) for k in keys)}"
        elif isinstance(data, list):
            if len(data) > max_items:
                types = set(type(x).__name__ for x in data[:max_items])
                return f"List with {len(data)} items of type(s): {', '.join(types)}"
            elif data:
                types = set(type(x).__name__ for x in data)
                return f"List with {len(data)} items of type(s): {', '.join(types)}"
            else:
                return "Empty list"
        else:
            return f"Value of type: {type(data).__name__}"

    @classmethod
    async def _process_csv(cls, file: BinaryIO, filename: str) -> str:
        """Process a CSV file."""
        status_tracker[filename]['status'] = 'processing CSV'

        try:
            # Read the CSV content
            csv_content = file.read().decode('utf-8')

            # Parse CSV
            csv_reader = csv.reader(io.StringIO(csv_content))
            rows = list(csv_reader)

            if not rows:
                return "Empty CSV file"

            # Get header row
            header = rows[0]

            # Format as markdown table
            md_table = []
            md_table.append("| " + " | ".join(header) + " |")
            md_table.append("| " + " | ".join(["-" * len(col) for col in header]) + " |")

            # Add data rows (limit to 100 for large files)
            max_rows = min(100, len(rows) - 1)
            for i in range(1, max_rows + 1):
                # Ensure the row has the correct number of columns
                row = rows[i]
                while len(row) < len(header):
                    row.append("")
                row = [cell.replace("|", "\\|") for cell in row]  # Escape pipe characters
                md_table.append("| " + " | ".join(row) + " |")

            # Add indicator if rows were truncated
            if len(rows) - 1 > max_rows:
                md_table.append(f"\n*CSV file truncated. Showing {max_rows} of {len(rows) - 1} rows.*")

            return "\n".join(md_table)

        except Exception as e:
            cls.logger.error(f"Error processing CSV file {filename}: {str(e)}")
            raise ProcessingError(f"Failed to process CSV: {str(e)}")

    @classmethod
    async def _process_image(cls, file: BinaryIO, filename: str) -> str:
        """Process an image file (placeholder - would need OCR)."""
        status_tracker[filename]['status'] = 'processing image'

        # For real image processing, you'd need an OCR library like pytesseract
        # This is just a placeholder
        return f"[Image File: {filename}]\n\nImage processing requires OCR capabilities which are not currently enabled."

# Add synchronous versions of the processing methods
def process_file_sync(file, filename):
    """Process a file synchronously and extract its text content."""
    return asyncio.run(FileProcessor.process_file(file, filename))
