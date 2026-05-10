from pydantic import BaseModel, EmailStr

class SendOTPRequest(BaseModel):
    email: EmailStr

class SendOTPResponse(BaseModel):
    message: str

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str
