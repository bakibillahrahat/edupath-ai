"""
Catalog Domain Schemas.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class OpportunityRead(BaseModel):
    id: str
    title: str
    provider: str | None = None
    university: str | None = None
    degree_level: str | None = None
    country: str | None = None
    field: str | None = None
    funding_type: str | None = None
    amount: float | None = None
    deadline: datetime | None = None
    eligibility: dict = Field(default_factory=dict)
    application_url: str | None = None
    source_url: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, value: object) -> str:
        return str(value)


class UniversityRead(BaseModel):
    id: str
    name: str
    country: str | None = None
    website_url: str | None = None
    faculty_directory_url: str | None = None
    description: str | None = None
    metadata_json: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, value: object) -> str:
        return str(value)
