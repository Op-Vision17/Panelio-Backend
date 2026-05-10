from fastapi import HTTPException, status
from app.features.auth import service
from app.features.auth.schema import (
    SendOTPRequest, SendOTPResponse, 
    VerifyOTPRequest, TokenResponse,
    RefreshRequest, LogoutRequest
)
from app.shared.email import send_otp_email
from app.shared.exceptions import BadRequestError

async def handle_send_otp(body: SendOTPRequest, redis) -> SendOTPResponse:
    otp = await service.generate_and_store_otp(body.email, redis)
    await send_otp_email(body.email, otp)
    return SendOTPResponse(message="OTP sent successfully")

async def handle_verify_otp(body: VerifyOTPRequest, redis, db) -> TokenResponse:
    is_valid = await service.verify_and_consume_otp(body.email, body.otp, redis)
    if not is_valid:
        raise BadRequestError("Invalid or expired OTP")
    
    user = await service.get_or_create_user(body.email, db)
    access_token, refresh_token = await service.create_token_pair(str(user.id), db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

async def handle_refresh(body: RefreshRequest, db) -> TokenResponse:
    access_token, refresh_token = await service.rotate_refresh_token(body.refresh_token, db)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

async def handle_logout(body: LogoutRequest, db):
    await service.revoke_refresh_token(body.refresh_token, db)
    return {"message": "logged out"}
