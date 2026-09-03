"""
Profile Domain REST Endpoints.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.modules.auth import get_current_user_optional
from app.modules.auth.models import User
from app.modules.profiles.schemas import (
    StudentProfileCreate,
    StudentProfileRead,
    StudentProfileUpdate,
)
from app.modules.profiles.service import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_profile_service() -> ProfileService:
    return ProfileService()


@router.post("", response_model=StudentProfileRead)
async def create_profile(
    request: StudentProfileCreate,
    session: AsyncSession = Depends(get_db),
    service: ProfileService = Depends(get_profile_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> StudentProfileRead:
    try:
        return await service.create(session, request, user_id=current_user.id if current_user else None)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="A profile with this email already exists") from exc


@router.get("/me", response_model=StudentProfileRead | None)
async def get_my_profile(
    session: AsyncSession = Depends(get_db),
    service: ProfileService = Depends(get_profile_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> StudentProfileRead | None:
    if current_user is None:
        return None
    return await service.get_for_user(session, current_user.id, current_user.email)


@router.get("/{profile_id}", response_model=StudentProfileRead)
async def get_profile(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: ProfileService = Depends(get_profile_service),
) -> StudentProfileRead:
    profile = await service.get(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=StudentProfileRead)
async def update_profile(
    profile_id: UUID,
    request: StudentProfileUpdate,
    session: AsyncSession = Depends(get_db),
    service: ProfileService = Depends(get_profile_service),
) -> StudentProfileRead:
    profile = await service.update(session, profile_id, request)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
