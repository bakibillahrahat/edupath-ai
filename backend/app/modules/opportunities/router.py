"""
Opportunities & Catalog Domain REST Endpoints.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.modules.opportunities.schemas import OpportunityRead, UniversityRead
from app.modules.opportunities.service import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def get_opportunity_service() -> OpportunityService:
    return OpportunityService()


@router.get("", response_model=list[OpportunityRead])
async def list_opportunities(
    session: AsyncSession = Depends(get_db),
    service: OpportunityService = Depends(get_opportunity_service),
) -> list[OpportunityRead]:
    return await service.list_opportunities(session)


@router.get("/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(
    opportunity_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: OpportunityService = Depends(get_opportunity_service),
) -> OpportunityRead:
    opportunity = await service.get_opportunity(session, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity
