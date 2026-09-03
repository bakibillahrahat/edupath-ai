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


class ProgramRead(BaseModel):
    id: str
    university_id: str | None = None
    name: str
    degree_level: str | None = None
    field: str | None = None
    tuition: float | None = None
    deadline: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, value: object) -> str:
        return str(value)

from typing import Literal

class Evidence(BaseModel):
    claim: str
    source_url: str | None = None
    source_title: str | None = None
    source_type: Literal["official_university", "official_funding", "database", "web_search", "llm_estimate"]
    verified: bool
    retrieved_at: datetime


class CandidateOpportunity(BaseModel):
    id: str
    title: str
    university: str | None = None
    program: str | None = None
    degree_level: str | None = None
    country: str | None = None
    professor_name: str | None = None
    research_areas: list[str] = Field(default_factory=list)
    funding_type: str | None = None
    funding_amount: str | None = None
    deadline: str | None = None
    official_url: str | None = None
    ielts_score: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    eligibility_criteria: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    created_by: str


class EligibilityVerdict(BaseModel):
    opportunity_id: str
    eligible: Literal["verified_eligible", "likely_eligible", "verified_ineligible", "unknown"]
    confidence: float
    missing_requirements: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: str
    ielts_score: str | None = None
    required_documents: list[str] = Field(default_factory=list)


class ResearchMatchVerdict(BaseModel):
    opportunity_id: str
    overall_match: float
    interest_overlap: float
    technical_overlap: float
    experience_alignment: float
    program_alignment: float
    explanation: str


class VerificationVerdict(BaseModel):
    opportunity_id: str
    status: Literal["verified", "unverified", "stale_suspected"]
    checked_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RankedOpportunity(BaseModel):
    opportunity_id: str
    overall_score: float
    score_breakdown: dict[str, float]
    rank: int


class ProfessorRead(BaseModel):
    id: str
    university_id: str | None = None
    name: str
    department: str | None = None
    research_interests: str | None = None
    email: str | None = None
    profile_url: str | None = None
    accepting_students: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "university_id", mode="before")
    @classmethod
    def serialize_uuid(cls, value: object) -> str | None:
        return str(value) if value is not None else None
