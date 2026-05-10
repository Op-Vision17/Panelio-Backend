from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.shared.dependencies import get_current_user
from app.features.auth import handler
from app.features.auth.schema import (
    SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, TokenResponse,
    RefreshRequest, LogoutRequest
)

router = APIRouter()

@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    body: SendOTPRequest,
    redis=Depends(get_redis)
):
    return await handler.handle_send_otp(body, redis)

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: VerifyOTPRequest,
    redis=Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    return await handler.handle_verify_otp(body, redis, db)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    return await handler.handle_refresh(body, db)

@router.post("/logout")
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await handler.handle_logout(body, db)
