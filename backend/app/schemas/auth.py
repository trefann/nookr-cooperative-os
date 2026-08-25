"""Authentication schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=160)
    role: UserRole = UserRole.CUSTOMER
    phone: str = Field(default="", max_length=24)
    address: str = Field(default="", max_length=500)
    zone_id: int | None = None
    language: str = Field(default="en", max_length=8)

    @field_validator("role")
    @classmethod
    def _no_self_service_admin(cls, value: UserRole) -> UserRole:
        # Admin accounts are provisioned by the cooperative, never self-serve.
        if value is UserRole.ADMIN:
            raise ValueError(
                "Administrator accounts are created by the cooperative office."
            )
        return value

    @field_validator("full_name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Please enter your full name.")
        return cleaned


class DemoLoginRequest(BaseModel):
    role: UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    phone: str = ""
    address: str = ""
    language: str = "en"
    is_demo: bool = False
    cooperative_id: int | None = None
    zone_id: int | None = None
    lat: float = 0.0
    lng: float = 0.0
    worker_id: int | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int


class DemoAccount(BaseModel):
    role: str
    label: str
    email: EmailStr
    password: str
    description: str
