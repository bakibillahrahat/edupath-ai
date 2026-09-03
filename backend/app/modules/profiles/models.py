"""
Profile Domain Database Models.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.modules.auth.models import TimestampMixin, UUIDMixin


class StudentProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    academic_level: Mapped[str | None] = mapped_column(String(100))
    current_degree: Mapped[str | None] = mapped_column(String(255))
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    university: Mapped[str | None] = mapped_column(String(255))
    gpa: Mapped[float | None] = mapped_column(Numeric(3, 2))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    target_degree: Mapped[str | None] = mapped_column(String(100))
    target_countries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    research_interests: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    publications: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    projects: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    work_experience: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    preferred_funding: Mapped[str | None] = mapped_column(String(255))

    # Contact & Secondary Schooling
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ssc_exam_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ssc_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ssc_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ssc_school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssc_board: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ssc_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Higher Secondary Schooling
    hsc_exam_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hsc_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hsc_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hsc_college: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hsc_board: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hsc_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Standardized Tests
    sat_score: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gre_score: Mapped[str | None] = mapped_column(String(100), nullable=True)
    english_score: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Optional Master's (MSc) for PhD applicants
    has_msc: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    msc_degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    msc_university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    msc_gpa: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    msc_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    msc_thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
