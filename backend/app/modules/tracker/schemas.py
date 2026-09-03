"""
Admissions Tracker Domain Schemas.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class ApplicationCreate(BaseModel):
    profile_id: str
    opportunity_id: str
    status: str = "draft"
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: str | None = None
    submitted_at: datetime | None = None
    notes: str | None = None


class ApplicationRead(BaseModel):
    id: str
    profile_id: str | None = None
    opportunity_id: str | None = None
    status: str
    submitted_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "profile_id", "opportunity_id", mode="before")
    @classmethod
    def serialize_ids(cls, value: object) -> str | None:
        return str(value) if value is not None else None


class ApplicationStageUpdate(BaseModel):
    stage: str
    notes: str | None = None


__all__ = [
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationRead",
    "ApplicationStageUpdate",
]
