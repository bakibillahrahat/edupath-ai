"""
Admissions Tracker Domain Repository.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tracker.models import Application


class ApplicationRepository:
    async def create(self, session: AsyncSession, application: Application) -> Application:
        session.add(application)
        await session.commit()
        await session.refresh(application)
        return application

    async def get(self, session: AsyncSession, application_id: UUID) -> Application | None:
        return await session.get(Application, application_id)

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[Application]:
        result = await session.execute(
            select(Application).where(Application.profile_id == profile_id).order_by(Application.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, session: AsyncSession, application: Application) -> Application:
        await session.commit()
        await session.refresh(application)
        return application

    async def delete(self, session: AsyncSession, application: Application) -> None:
        await session.delete(application)
        await session.commit()
