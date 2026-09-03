"""
Profile Domain Service.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profile.models import StudentProfile
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.schemas import StudentProfileCreate, StudentProfileRead, StudentProfileUpdate


class ProfileService:
    def __init__(self, repository: ProfileRepository | None = None) -> None:
        self._repository = repository or ProfileRepository()

    async def create(self, session: AsyncSession, request: StudentProfileCreate, *, user_id: UUID | None = None) -> StudentProfileRead:
        profile = StudentProfile(**request.model_dump(), user_id=user_id)
        saved = await self._repository.create(session, profile)
        return StudentProfileRead.model_validate(saved)

    async def get(self, session: AsyncSession, profile_id: UUID) -> StudentProfileRead | None:
        profile = await self._repository.get(session, profile_id)
        return StudentProfileRead.model_validate(profile) if profile else None

    async def get_for_user(self, session: AsyncSession, user_id: UUID | None, email: str | None = None) -> StudentProfileRead | None:
        def coerce_profile(profile):
            if profile is None:
                return None
            if not hasattr(profile, "created_at"):
                profile.created_at = datetime.now(UTC)
            if not hasattr(profile, "updated_at"):
                profile.updated_at = datetime.now(UTC)
            return StudentProfileRead.model_validate(profile)

        if user_id is not None:
            profile = await self._repository.get_by_user_id(session, user_id)
            validated = coerce_profile(profile)
            if validated is not None:
                return validated
        if email:
            profile = await self._repository.get_by_email(session, email)
            validated = coerce_profile(profile)
            if validated is not None:
                return validated
        return None

    async def update(self, session: AsyncSession, profile_id: UUID, request: StudentProfileUpdate) -> StudentProfileRead | None:
        profile = await self._repository.get(session, profile_id)
        if profile is None:
            return None

        payload = request.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(profile, key, value)

        saved = await self._repository.update(session, profile)
        return StudentProfileRead.model_validate(saved)
