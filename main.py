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
from core.pipeline import get_pipeline_orchestrator
from core.optimized.optimized_document_store import get_optimized_document_store
from core.load_balancing.load_balancer import get_load_balancer

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

    # Initialize optimized components
    logger.info("Initializing optimized components...")

    # Initialize optimized document store
    document_store = get_optimized_document_store(enable_async=True, pool_size=10)

    # Initialize load balancer
    load_balancer = get_load_balancer("response_time")
    await load_balancer.start()

    # Initialize pipeline orchestrator
    pipeline_config = {
        "preprocessing": {"max_message_length": 10000, "rate_limiter_enabled": True},
        "context_gathering": {"max_context_documents": 5, "context_ttl": 3600},
        "provider_selection": {"fallback_enabled": True, "max_providers": 3},
        "response_generation": {"timeout": 30.0, "parallel_execution": True},
        "response_processing": {"response_validation_enabled": True, "caching_enabled": True},
        "document_store": document_store
    }
    pipeline_orchestrator = get_pipeline_orchestrator(pipeline_config)

    # Store in app state for dependency injection
    app.state.document_store = document_store
    app.state.load_balancer = load_balancer
    app.state.pipeline_orchestrator = pipeline_orchestrator

    logger.info("FastAPI GenAI Chat application with five-stage pipeline starting up...")

    yield

    # Shutdown
    logger.info("Shutting down optimized components...")

    # Cleanup components
    if hasattr(app.state, 'load_balancer'):
        await app.state.load_balancer.stop()

    if hasattr(app.state, 'document_store'):
        app.state.document_store.close()

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
    """Enhanced health check endpoint with pipeline metrics"""
    from fastapi import Request

    # Get file manager
    file_manager = await get_file_manager()

    # Base health info
    health_info = {
        "status": "healthy",
        "framework": "FastAPI",
        "providers": [
            "openai", "groq", "anthropic", "mistral", "gemini",
            "cohere", "xai", "deepseek", "alibaba", "openrouter",
            "huggingface", "moonshot", "perplexity"
        ],
        "documents": getattr(file_manager, "total_documents", 0),
    }

    # Add pipeline metrics if available
    if hasattr(app.state, 'pipeline_orchestrator'):
        pipeline_metrics = app.state.pipeline_orchestrator.get_pipeline_metrics()
        health_info["pipeline"] = pipeline_metrics

    # Add load balancer metrics if available
    if hasattr(app.state, 'load_balancer'):
        lb_stats = app.state.load_balancer.get_statistics()
        health_info["load_balancer"] = {
            "strategy": lb_stats["strategy"],
            "healthy_instances": lb_stats["healthy_instances"],
            "total_requests": lb_stats["total_requests"],
            "error_rate": lb_stats["error_rate"],
            "average_response_time": lb_stats["average_response_time"]
        }

    # Add document store metrics if available
    if hasattr(app.state, 'document_store'):
        try:
            doc_stats = await app.state.document_store.get_document_statistics_async()
            health_info["document_store"] = {
                "total_documents": doc_stats.get("total_documents", 0),
                "recent_documents": doc_stats.get("recent_documents", 0),
                "total_size_bytes": doc_stats.get("total_size_bytes", 0)
            }
        except Exception as e:
            logger.warning(f"Failed to get document store stats: {e}")

    return health_info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5005,
        reload=True,
        log_level="info"
    )
