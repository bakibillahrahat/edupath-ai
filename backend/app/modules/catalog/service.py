"""
Catalog Domain Service.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.repository import OpportunityRepository, UniversityRepository
from app.modules.catalog.schemas import OpportunityRead, UniversityRead


class CatalogService:
    def __init__(
        self,
        opp_repository: OpportunityRepository | None = None,
        uni_repository: UniversityRepository | None = None,
    ) -> None:
        self._opp_repository = opp_repository or OpportunityRepository()
        self._uni_repository = uni_repository or UniversityRepository()

    async def list_opportunities(self, session: AsyncSession) -> list[OpportunityRead]:
        items = await self._opp_repository.list(session)
        return [OpportunityRead.model_validate(item) for item in items]

    async def get_opportunity(self, session: AsyncSession, opportunity_id: UUID) -> OpportunityRead | None:
        item = await self._opp_repository.get(session, opportunity_id)
        return OpportunityRead.model_validate(item) if item else None

    async def search_universities(self, session: AsyncSession, query: str, limit: int = 5) -> list[UniversityRead]:
        items = await self._uni_repository.search(session, query, limit=limit)
        return [UniversityRead.model_validate(item) for item in items]
