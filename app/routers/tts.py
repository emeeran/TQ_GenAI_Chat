"""
Text-to-speech routes for FastAPI application.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPBasicCredentials

from app.models.requests import TTSRequest
from app.models.responses import TTSVoicesResponse
from app.routers.auth import require_auth
from core.tts import tts_engine

router = APIRouter()


@router.get("/voices", response_model=TTSVoicesResponse)
async def tts_voices():
    """Get available TTS voices"""
    try:
        voices = tts_engine.get_voices()
        return {"voices": [voice.to_dict() for voice in voices]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get TTS voices")


@router.post("")
async def tts(
    request: TTSRequest,
    _: HTTPBasicCredentials = Depends(require_auth)
):
    """Convert text to speech"""
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="No text provided")

        audio_data, content_type = tts_engine.synthesize(
            request.text, 
            request.voice_id, 
            request.lang
        )
        return Response(content=audio_data, media_type=content_type)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="TTS processing failed")
