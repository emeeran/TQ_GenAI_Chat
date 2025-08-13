"""
TQ GenAI Chat - FastAPI Application

Multi-provider GenAI chat application with modular architecture.
Supports 10+ AI providers with advanced file processing capabilities.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.dependencies import get_file_manager
from app.routers import auth, chat, documents, files, models, tts
from config.settings import EXPORT_DIR, SAVE_DIR, UPLOAD_DIR

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, verbose=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    # Ensure directories exist
    for directory in [SAVE_DIR, EXPORT_DIR, UPLOAD_DIR]:
        directory.mkdir(mode=0o755, parents=True, exist_ok=True)

    # Initialize file manager (will be created via dependency injection)
    logger.info("FastAPI GenAI Chat application starting up...")

    yield

    # Shutdown
    logger.info("FastAPI GenAI Chat application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="TQ GenAI Chat",
    description="Multi-provider GenAI chat application with advanced file processing",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router, prefix="", tags=["Authentication"])
app.include_router(chat.router, prefix="", tags=["Chat"])
app.include_router(files.router, prefix="", tags=["File Management"])
app.include_router(documents.router, prefix="/documents", tags=["Document Management"])
app.include_router(models.router, prefix="", tags=["Model Management"])
app.include_router(tts.router, prefix="/tts", tags=["Text-to-Speech"])


@app.get("/")
async def root():
    """Main chat interface - redirect to login or chat"""
    return {"message": "TQ GenAI Chat - FastAPI Version"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    file_manager = await get_file_manager()
    return {
        "status": "healthy",
        "framework": "FastAPI",
        "providers": [
            "openai", "groq", "anthropic", "mistral", "gemini",
            "cohere", "xai", "deepseek", "alibaba", "openrouter",
            "huggingface", "moonshot", "perplexity"
        ],
        "documents": getattr(file_manager, "total_documents", 0),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5005,
        reload=True,
        log_level="info"
    )
