from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """A single sourced claim backing part of a CandidateOpportunity.

    Every non-trivial fact an agent attaches to a candidate should carry at
    least one Evidence entry pointing at where it came from, so the frontend
    can render a verified/unverified badge instead of asking the user to
    trust an unsourced claim.
    """

    claim: str
    source_url: str | None = None
    source_title: str | None = None
    source_type: Literal["official_university", "official_funding", "database", "web_search", "llm_estimate"]
    verified: bool
    retrieved_at: datetime


class CandidateOpportunity(BaseModel):
    """One discovered opportunity, introduced by a discovery agent and
    progressively enriched (in place, by id) by the eligibility, research
    match, verification, and ranking agents."""

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
