"""
Profile Domain Repository.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profile.models import StudentProfile


class ProfileRepository:
    async def create(self, session: AsyncSession, profile: StudentProfile) -> StudentProfile:
        session.add(profile)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise
        await session.refresh(profile)
        return profile

    async def get(self, session: AsyncSession, profile_id: UUID) -> StudentProfile | None:
        return await session.get(StudentProfile, profile_id)

    async def get_by_user_id(self, session: AsyncSession, user_id: UUID) -> StudentProfile | None:
        return await session.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))

    async def get_by_email(self, session: AsyncSession, email: str) -> StudentProfile | None:
        return await session.scalar(select(StudentProfile).where(StudentProfile.email == email))

    async def update(self, session: AsyncSession, profile: StudentProfile) -> StudentProfile:
        await session.commit()
        await session.refresh(profile)
        return profile
