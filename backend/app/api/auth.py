from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    try:
        token = await AuthService.login(req.phone, req.code)
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/logout")
async def logout():
    return {"status": "ok"}
