"""
Auth & Identity Domain Schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class AuthConfigResponse(BaseModel):
    """Tells the frontend which login flow to render."""

    mode: Literal["google", "dev-mock"]
    google_login_url: str | None = None


class UserRead(BaseModel):
    id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, value: object) -> str:
        return str(value)


class DevLoginRequest(BaseModel):
    email: str
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
