"""
Admissions Tracker Domain Service.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tracker.models import Application
from app.modules.tracker.repository import ApplicationRepository
from app.modules.tracker.schemas import ApplicationCreate, ApplicationRead, ApplicationUpdate


class TrackerService:
    def __init__(self, repository: ApplicationRepository | None = None) -> None:
        self._repository = repository or ApplicationRepository()

    async def create(self, session: AsyncSession, request: ApplicationCreate) -> ApplicationRead:
        app = Application(
            profile_id=UUID(request.profile_id) if request.profile_id else None,
            opportunity_id=UUID(request.opportunity_id) if request.opportunity_id else None,
            status=request.status,
            notes=request.notes,
        )
        saved = await self._repository.create(session, app)
        return ApplicationRead.model_validate(saved)

    async def get(self, session: AsyncSession, application_id: UUID) -> ApplicationRead | None:
        item = await self._repository.get(session, application_id)
        return ApplicationRead.model_validate(item) if item else None

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[ApplicationRead]:
        items = await self._repository.list_for_profile(session, profile_id)
        return [ApplicationRead.model_validate(item) for item in items]

    async def update(self, session: AsyncSession, application_id: UUID, request: ApplicationUpdate) -> ApplicationRead | None:
        app = await self._repository.get(session, application_id)
        if not app:
            return None
        if request.status is not None:
            app.status = request.status
        if request.submitted_at is not None:
            app.submitted_at = request.submitted_at
        if request.notes is not None:
            app.notes = request.notes
        saved = await self._repository.update(session, app)
        return ApplicationRead.model_validate(saved)
