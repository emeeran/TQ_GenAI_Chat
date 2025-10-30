"""
File upload and processing routes for FastAPI application.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import HTTPBasicCredentials
from pydub import AudioSegment

from app.dependencies import get_file_manager
from app.models.responses import FileStatusResponse, FileUploadResponse
from app.routers.auth import require_auth
from app.utils import secure_filename
from config.settings import ALLOWED_EXTENSIONS, UPLOAD_DIR
from core.file_processor import FileProcessor

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)

# Processing status tracking
PROCESSING_STATUS = {}
PROCESSING_ERRORS = {}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or "." not in filename:
        logger.warning(f"Invalid filename format: {filename}")
        return False
    
    extension = filename.rsplit(".", 1)[1].lower()
    is_allowed = extension in ALLOWED_EXTENSIONS
    
    if not is_allowed:
        logger.warning(f"File extension '{extension}' not in allowed extensions: {ALLOWED_EXTENSIONS}")
    
    return is_allowed


async def process_file_async(filename: str, file_path: str, file_manager):
    """Process uploaded file asynchronously"""
    try:
        processor = FileProcessor()
        
        # Read file content as bytes
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Process the file content
        extracted_content = await processor.process_file(content, filename)
        logger.info(f"Successfully extracted {len(extracted_content)} characters from {filename}")

        # Add to document store
        try:
            doc_id = file_manager.add_document(filename, extracted_content)
            logger.info(f"Successfully added document to store with ID: {doc_id}")
        except Exception as doc_error:
            logger.error(f"Failed to add document to store: {str(doc_error)}")
            raise doc_error

        # Update status
        PROCESSING_STATUS[filename] = {
            "status": "Complete",
            "timestamp": asyncio.get_event_loop().time(),
            "size": len(extracted_content),
        }

    except Exception as e:
        logger.error(f"File processing error for {filename}: {str(e)}")
        PROCESSING_ERRORS[filename] = str(e)
        PROCESSING_STATUS[filename] = {
            "status": "Failed",
            "timestamp": asyncio.get_event_loop().time(),
            "error": str(e),
        }


@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    _: HTTPBasicCredentials = Depends(require_auth),
    file_manager = Depends(get_file_manager)
):
    """Upload and process files"""
    try:
        logger.info(f"Upload request received with {len(files)} files")
        
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        if len(files) > 10:  # MAX_FILES constant
            raise HTTPException(
                status_code=400, 
                detail=f"Too many files. Maximum 10 allowed"
            )

        # Process files asynchronously
        results = []
        tasks = []
        
        for file in files:
            if file.filename == "":
                continue

            logger.info(f"Processing file: {file.filename}")
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = Path(UPLOAD_DIR) / filename
                
                try:
                    # Ensure upload directory exists
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save file content
                    content = await file.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    logger.info(f"File saved: {file_path}")
                    
                    # Initialize processing status
                    PROCESSING_STATUS[filename] = {
                        "status": "Processing",
                        "timestamp": asyncio.get_event_loop().time(),
                        "progress": 0,
                    }
                    
                    # Start async processing
                    task = asyncio.create_task(
                        process_file_async(filename, str(file_path), file_manager)
                    )
                    tasks.append(task)
                    
                    results.append({"filename": filename, "status": "success"})
                    logger.info(f"File processing started: {filename}")
                    
                except Exception as save_error:
                    logger.error(f"Error saving file {filename}: {str(save_error)}")
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "message": f"Failed to save file: {str(save_error)}"
                    })
            else:
                logger.warning(f"File type not allowed: {file.filename}")
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": "File type not allowed",
                })

        # Don't await tasks here - let them run in background
        logger.info(f"Upload request completed with {len(results)} results")
        return {"results": results}

    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/upload/status/{filename}", response_model=FileStatusResponse)
async def upload_status(
    filename: str,
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Get file processing status"""
    try:
        status = PROCESSING_STATUS.get(filename, {})
        if filename in PROCESSING_ERRORS:
            status["error"] = PROCESSING_ERRORS[filename]
        return status
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")


@router.post("/upload_audio")
async def upload_audio(
    audio: UploadFile = File(...),
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Upload and transcribe audio files"""
    if not SPEECH_RECOGNITION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Speech recognition not available - missing speech_recognition module"
        )

    try:
        if not audio or audio.filename == "":
            raise HTTPException(status_code=400, detail="No audio file provided")

        # Save audio file temporarily
        filename = secure_filename(audio.filename)
        temp_path = Path(tempfile.gettempdir()) / filename
        
        content = await audio.read()
        with open(temp_path, 'wb') as f:
            f.write(content)

        # Convert to WAV if needed
        if not filename.lower().endswith(".wav"):
            audio_segment = AudioSegment.from_file(temp_path)
            wav_path = temp_path.with_suffix(".wav")
            audio_segment.export(wav_path, format="wav")
            temp_path.unlink()  # Remove original
            temp_path = wav_path

        # Transcribe audio
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(temp_path)) as source:
            audio_data = recognizer.record(source)
            transcript = recognizer.recognize_google(audio_data)

        # Cleanup
        temp_path.unlink()

        return {"transcript": transcript}

    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Could not understand audio")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Speech recognition error: {str(e)}")
    except Exception as e:
        logger.error(f"Audio transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Audio processing failed")
