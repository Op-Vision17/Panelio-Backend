from pydantic import BaseModel, EmailStr, Field, field_validator


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


class VerifyOTPResponse(BaseModel):
    access_token: str
    refresh_token: str
    is_onboarded: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


import uuid
from datetime import datetime

from pydantic import ConfigDict


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    phone_number: str
    enrollment_number: str
    is_onboarded: bool
    profile_photo_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Phone number must contain exactly 10 digits")
        return v


class OnboardingRequest(BaseModel):
    name: str = Field(..., min_length=1)
    phone_number: str
    enrollment_number: str = Field(..., min_length=1)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 10:
            raise ValueError("Phone number must contain exactly 10 digits")
        return v


class UpdateUserRequest(BaseModel):
    name: str | None = Field(None, min_length=1)
    phone_number: str | None = None
    enrollment_number: str | None = Field(None, min_length=1)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.isdigit() or len(v) != 10:
                raise ValueError("Phone number must contain exactly 10 digits")
        return v
