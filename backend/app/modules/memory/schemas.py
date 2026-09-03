"""
Memory Domain Schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class MemoryRead(BaseModel):
    id: str
    profile_id: str | None = None
    memory_type: str
    scope: str
    content: dict[str, Any]
    source: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "profile_id", mode="before")
    @classmethod
    def serialize_uuid(cls, value: object) -> str | None:
        return str(value) if value else None


class MemoryCreate(BaseModel):
    profile_id: UUID | None = None
    memory_type: str
    scope: str = "short_term"
    content: dict[str, Any]
    source: str | None = None


class MemoryQuery(BaseModel):
    profile_id: UUID | None = None
    query_text: str
    limit: int = 5
