"""
Model management routes for FastAPI application.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasicCredentials

from app.models.requests import SetDefaultModelRequest
from app.models.responses import ModelsResponse
from app.routers.auth import require_auth
from core.models import model_manager

router = APIRouter()

@router.get("/get_models/{provider}", response_model=ModelsResponse)
async def get_models(
    provider: str,
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Get available models for a provider"""
    try:
        models = model_manager.get_models(provider)
        default_model = models[0] if models else None
        return {"models": models, "default": default_model}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get models") from e


@router.post("/update_models/{provider}")
async def update_models(
    provider: str,
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Update models for a provider by fetching from their API"""
    try:
        # Import the update script functionality
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

        from update_models_from_providers import fetch_provider_models

        # Fetch latest models from provider
        new_models = fetch_provider_models(provider)

        if not new_models:
            raise ValueError(f"No models returned from {provider} API. Check API key or provider availability.")

        # Update the model manager
        model_manager.update_models(provider, new_models)

        default_model = new_models[0] if new_models else None

        return {
            "success": True,
            "message": f"Successfully updated {len(new_models)} models for {provider}",
            "models": new_models,
            "default": default_model,
            "count": len(new_models),
        }

    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except Exception as e:
        error_msg = str(e) if str(e) else f"Unknown error updating models for {provider}"
        raise HTTPException(status_code=500, detail=f"Failed to update models: {error_msg}") from e


@router.post("/set_default_model/{provider}")
async def set_default_model(
    provider: str,
    request: SetDefaultModelRequest,
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Set default model for a provider"""
    try:
        model = request.model

        # Verify model exists for provider
        if not model_manager.is_model_available(provider, model):
            raise HTTPException(
                status_code=400,
                detail=f"Model {model} not available for {provider}"
            )

        # Set as default
        model_manager.set_default_model(provider, model)

        return {
            "success": True,
            "message": f"Set {model} as default for {provider}",
            "provider": provider,
            "model": model,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set default model: {str(e)}") from e

