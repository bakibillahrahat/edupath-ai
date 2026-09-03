"""
Profile & Identity Domain Schemas.
"""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StudentProfileCreate(BaseModel):
    name: str | None = None
    email: str
    academic_level: str | None = None
    current_degree: str | None = None
    field_of_study: str | None = None
    university: str | None = None
    gpa: float | None = None
    graduation_year: int | None = None
    target_degree: str | None = None
    target_countries: list[str] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    work_experience: list[str] = Field(default_factory=list)
    preferred_funding: str | None = None
    phone: str | None = None
    ssc_exam_type: str | None = None
    ssc_group: str | None = None
    ssc_result: str | None = None
    ssc_school: str | None = None
    ssc_board: str | None = None
    ssc_year: int | None = None
    hsc_exam_type: str | None = None
    hsc_group: str | None = None
    hsc_result: str | None = None
    hsc_college: str | None = None
    hsc_board: str | None = None
    hsc_year: int | None = None
    sat_score: str | None = None
    gre_score: str | None = None
    english_score: str | None = None
    has_msc: bool | None = None
    msc_degree: str | None = None
    msc_university: str | None = None
    msc_gpa: float | None = None
    msc_year: int | None = None
    msc_thesis: str | None = None


class StudentProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    academic_level: str | None = None
    current_degree: str | None = None
    field_of_study: str | None = None
    university: str | None = None
    gpa: float | None = None
    graduation_year: int | None = None
    target_degree: str | None = None
    target_countries: list[str] | None = None
    research_interests: list[str] | None = None
    skills: list[str] | None = None
    publications: list[str] | None = None
    projects: list[str] | None = None
    work_experience: list[str] | None = None
    preferred_funding: str | None = None
    phone: str | None = None
    ssc_exam_type: str | None = None
    ssc_group: str | None = None
    ssc_result: str | None = None
    ssc_school: str | None = None
    ssc_board: str | None = None
    ssc_year: int | None = None
    hsc_exam_type: str | None = None
    hsc_group: str | None = None
    hsc_result: str | None = None
    hsc_college: str | None = None
    hsc_board: str | None = None
    hsc_year: int | None = None
    sat_score: str | None = None
    gre_score: str | None = None
    english_score: str | None = None
    has_msc: bool | None = None
    msc_degree: str | None = None
    msc_university: str | None = None
    msc_gpa: float | None = None
    msc_year: int | None = None
    msc_thesis: str | None = None


class StudentProfileRead(BaseModel):
    id: str
    user_id: str | None = None
    name: str | None = None
    email: str
    academic_level: str | None = None
    current_degree: str | None = None
    field_of_study: str | None = None
    university: str | None = None
    gpa: float | None = None
    graduation_year: int | None = None
    target_degree: str | None = None
    target_countries: list[str] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    work_experience: list[str] = Field(default_factory=list)
    preferred_funding: str | None = None
    phone: str | None = None
    ssc_exam_type: str | None = None
    ssc_group: str | None = None
    ssc_result: str | None = None
    ssc_school: str | None = None
    ssc_board: str | None = None
    ssc_year: int | None = None
    hsc_exam_type: str | None = None
    hsc_group: str | None = None
    hsc_result: str | None = None
    hsc_college: str | None = None
    hsc_board: str | None = None
    hsc_year: int | None = None
    sat_score: str | None = None
    gre_score: str | None = None
    english_score: str | None = None
    has_msc: bool | None = None
    msc_degree: str | None = None
    msc_university: str | None = None
    msc_gpa: float | None = None
    msc_year: int | None = None
    msc_thesis: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def serialize_id(cls, value: object) -> str | None:
        return str(value) if value is not None else None
