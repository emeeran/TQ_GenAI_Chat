"""
Chat routes for FastAPI application.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.dependencies import get_file_manager
from app.models.requests import ChatRequest, SearchContextRequest
from app.models.responses import ChatResponse, SearchContextResponse, PersonasResponse
from app.routers.auth import require_auth
from core.chat_handler import create_chat_handler
from persona import PERSONAS

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def index(request: Request, _: HTTPBasicCredentials = Depends(require_auth)):
    """Main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _: HTTPBasicCredentials = Depends(require_auth),
    file_manager = Depends(get_file_manager)
):
    """Main chat endpoint"""
    try:
        chat_handler = create_chat_handler(file_manager)
        response = await chat_handler.process_chat_request(request.model_dump())
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search_context", response_model=SearchContextResponse)
async def search_context(
    request: SearchContextRequest,
    _: HTTPBasicCredentials = Depends(require_auth),
    file_manager = Depends(get_file_manager)
):
    """Search uploaded documents for relevant content"""
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="No query provided")

        results = file_manager.search_documents(request.message)

        # Format results for response
        formatted_results = [
            {
                "filename": r["filename"],
                "excerpt": (
                    r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"]
                ),
                "similarity": r["similarity"],
            }
            for r in results
        ]

        return {"results": formatted_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_personas", response_model=PersonasResponse)
async def get_personas():
    """Get available personas"""
    personas_list = []
    for persona_id, persona_content in PERSONAS.items():
        display_name = persona_id.replace("_", " ").title()
        if isinstance(persona_content, dict):
            personas_list.append({
                "id": persona_id,
                "name": persona_content.get("name", display_name),
                "content": persona_content.get("system_prompt", "")
            })
        else:
            personas_list.append({
                "id": persona_id,
                "name": display_name,
                "content": persona_content
            })
    return {"personas": personas_list}


@router.get("/get_persona_content/{persona_key}")
async def get_persona_content(persona_key: str):
    """Get persona content"""
    content = PERSONAS.get(persona_key, "")
    return {"content": content}
