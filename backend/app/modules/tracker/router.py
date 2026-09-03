"""
Admissions Tracker Domain REST Endpoints.
"""
from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.tracker.schemas import ApplicationCreate, ApplicationRead, ApplicationUpdate
from app.modules.tracker.service import TrackerService

router = APIRouter(prefix="/applications", tags=["applications"])


def get_tracker_service() -> TrackerService:
    return TrackerService()


@router.post("", response_model=ApplicationRead)
async def create_application(
    request: ApplicationCreate,
    session: AsyncSession = Depends(get_db),
    service: TrackerService = Depends(get_tracker_service),
) -> ApplicationRead:
    return await service.create(session, request)


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: TrackerService = Depends(get_tracker_service),
) -> list[ApplicationRead]:
    return await service.list_for_profile(session, profile_id)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: TrackerService = Depends(get_tracker_service),
) -> ApplicationRead:
    app = await service.get(session, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.put("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: UUID,
    request: ApplicationUpdate,
    session: AsyncSession = Depends(get_db),
    service: TrackerService = Depends(get_tracker_service),
) -> ApplicationRead:
    app = await service.update(session, application_id, request)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app
