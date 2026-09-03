"""
Memory Domain REST Endpoints.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.modules.memory.schemas import MemoryRead
from app.modules.memory.service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


def get_memory_service() -> MemoryService:
    return MemoryService()


@router.get("/{profile_id}", response_model=list[MemoryRead])
async def get_memory(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemoryRead]:
    return await service.list_for_profile(session, profile_id)
