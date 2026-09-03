"""
Catalog Domain REST Endpoints.
"""
from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.modules.catalog.schemas import OpportunityRead, UniversityRead
from app.modules.catalog.service import CatalogService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def get_catalog_service() -> CatalogService:
    return CatalogService()


@router.get("", response_model=list[OpportunityRead])
async def list_opportunities(
    session: AsyncSession = Depends(get_db),
    service: CatalogService = Depends(get_catalog_service),
) -> list[OpportunityRead]:
    return await service.list_opportunities(session)


@router.get("/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(
    opportunity_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: CatalogService = Depends(get_catalog_service),
) -> OpportunityRead:
    opportunity = await service.get_opportunity(session, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity
