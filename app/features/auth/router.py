from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.features.auth import handler
from app.features.auth.schema import (
    LogoutRequest,
    RefreshRequest,
    SendOTPRequest,
    SendOTPResponse,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
)
from app.shared.dependencies import get_current_user
from app.shared.responses import SuccessResponse, success_response

router = APIRouter()


@router.post("/send-otp", response_model=SuccessResponse[SendOTPResponse])
async def send_otp(body: SendOTPRequest, redis=Depends(get_redis)):
    res = await handler.handle_send_otp(body, redis)
    return success_response(data=res, message=res.message)


@router.post("/verify-otp", response_model=SuccessResponse[TokenResponse])
async def verify_otp(
    body: VerifyOTPRequest, redis=Depends(get_redis), db: AsyncSession = Depends(get_db)
):
    res = await handler.handle_verify_otp(body, redis, db)
    return success_response(data=res, message="OTP verified successfully")


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    res = await handler.handle_refresh(body, db)
    return success_response(data=res, message="Token refreshed successfully")


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    res = await handler.handle_logout(body, db)
    return success_response(data=res, message="Logged out successfully")


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(current_user=Depends(get_current_user)):
    res = await handler.handle_get_me(current_user)
    return success_response(data=res, message="User profile retrieved successfully")
