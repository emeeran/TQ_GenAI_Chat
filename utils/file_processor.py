import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import docx
import io
import fitz  # PyMuPDF
import pandas as pd
import csv
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import markdown
import concurrent.futures
import warnings

class ProcessingError(Exception):
    """Custom error for file processing failures"""
    pass

class FileProcessor:
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    MAX_FILE_SIZE = 60 * 1024 * 1024  # 60MB per file
    MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total (increased to handle larger files)
    MAX_TEXT_LENGTH = 100000  # Increased maximum characters to process

    @staticmethod
    def process_pdf(file_bytes, progress_callback=None):
        """Process PDF with improved error handling"""
        if not file_bytes:
            raise ProcessingError("Empty PDF file")

        try:
            text = []
            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            total_pages = pdf.page_count

            for i, page in enumerate(pdf):
                try:
                    if progress_callback:
                        progress = int((i / total_pages) * 100)
                        progress_callback(progress)

                    content = page.get_text()
                    if not content.strip():
                        # Try OCR with error handling
                        try:
                            images = convert_from_bytes(file_bytes, size=(1200, None))
                            for img in images:
                                text.append(pytesseract.image_to_string(img))
                        except Exception as e:
                            text.append(f"[OCR failed on page {i+1}: {str(e)}]")
                    else:
                        text.append(content)

                except Exception as e:
                    text.append(f"[Error on page {i+1}: {str(e)}]")
                    continue

            if progress_callback:
                progress_callback(100)

            if not text:
                raise ProcessingError("No text content extracted")

            return "\n".join(text)

        except Exception as e:
            raise ProcessingError(f"PDF processing failed: {str(e)}")

        finally:
            try:
                pdf.close()
            except:
                pass

    @staticmethod
    def process_image(file_bytes, progress_callback=None):
        """Process image with recovery options"""
        if not file_bytes:
            raise ProcessingError("Empty image file")

        try:
            if progress_callback:
                progress_callback(10)

            image = Image.open(io.BytesIO(file_bytes))

            if progress_callback:
                progress_callback(30)

            # Validate image
            if max(image.size) < 10:
                raise ProcessingError("Image too small")

            # Resize with error handling
            try:
                if max(image.size) > 2000:
                    ratio = 2000 / max(image.size)
                    new_size = tuple(int(dim * ratio) for dim in image.size)
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
            except Exception as e:
                # Continue with original size
                pass

            if progress_callback:
                progress_callback(70)

            # OCR with retry
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    text = pytesseract.image_to_string(image)
                    if text.strip():
                        if progress_callback:
                            progress_callback(100)
                        return text
                except Exception as e:
                    last_error = e
                    continue

            if last_error:
                raise ProcessingError(f"OCR failed after {max_retries} attempts: {str(last_error)}")
            else:
                raise ProcessingError("No text extracted from image")

        except Exception as e:
            raise ProcessingError(f"Image processing failed: {str(e)}")

    @staticmethod
    def process_docx(file_bytes):
        """Extract text from DOCX"""
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    @staticmethod
    def process_excel(file_bytes):
        """Extract text from Excel files"""
        df = pd.read_excel(file_bytes, nrows=1000)  # Limit rows
        return df.to_string(max_rows=100, max_cols=20)

    @staticmethod
    def process_csv(file_bytes):
        """Extract text from CSV"""
        content = io.StringIO(file_bytes.decode('utf-8'))
        reader = csv.reader(content)
        return "\n".join([",".join(row) for row in reader])

    @staticmethod
    def process_epub(file_bytes):
        """Extract text from EPUB"""
        text = []
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='In the future version.*')
            book = epub.read_epub(io.BytesIO(file_bytes))

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text.append(soup.get_text())
        return "\n\n".join(text)

    @staticmethod
    def process_markdown(file_bytes):
        """Convert Markdown to text"""
        md_text = file_bytes.decode('utf-8')
        html = markdown.markdown(md_text)
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()

    @staticmethod
    def get_processor(extension):
        """Get appropriate processor for file type"""
        processors = {
            'pdf': FileProcessor.process_pdf,
            'epub': FileProcessor.process_epub,
            'jpg': FileProcessor.process_image,
            'jpeg': FileProcessor.process_image,
            'png': FileProcessor.process_image,
            'docx': FileProcessor.process_docx,
            'xlsx': FileProcessor.process_excel,
            'csv': FileProcessor.process_csv,
            'md': FileProcessor.process_markdown,
        }
        return processors.get(extension.lower())
