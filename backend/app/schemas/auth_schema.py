from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    device_id: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Literal["USER", "ADMIN"]


class TokenResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    user: AuthenticatedUserResponse


class VerificationRequest(BaseModel):
    session_id: str = Field(min_length=36, max_length=36)


class VerificationConfirmRequest(VerificationRequest):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerificationIssueResponse(BaseModel):
    session_id: str
    expires_in_seconds: int
    retry_after_seconds: int
    verification_code: str | None = None


class VerificationConfirmResponse(TokenResponse):
    login_status: Literal["AUTHENTICATED"]
    requires_verification: Literal[False]
    reason_codes: list[str]
    session_id: str
    verification_token: None = None
