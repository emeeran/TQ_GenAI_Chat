"""
Authentication routes for FastAPI application.
"""

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

# Basic auth credentials from environment
BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "changeme")


@router.get("/login")
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Process login form"""
    if username == BASIC_AUTH_USERNAME and password == BASIC_AUTH_PASSWORD:
        # In a real application, you would set a session/JWT token here
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="authenticated", value="true", httponly=True)
        return response
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials."}
        )


@router.get("/logout")
async def logout():
    """Process logout"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="authenticated")
    return response


def verify_credentials(credentials: HTTPBasicCredentials) -> bool:
    """Verify HTTP basic auth credentials"""
    return (
        credentials.username == BASIC_AUTH_USERNAME and
        credentials.password == BASIC_AUTH_PASSWORD
    )


# Dependency for requiring authentication
async def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Dependency to require authentication"""
    if not verify_credentials(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials
