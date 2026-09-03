"""
Opportunities & Catalog Domain Service.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.opportunities.repository import (
    CatalogRepository,
    OpportunityRepository,
    ProfessorRepository,
    UniversityRepository,
)
from app.modules.opportunities.schemas import OpportunityRead, UniversityRead


class CatalogService:
    def __init__(self, repository: CatalogRepository | None = None) -> None:
        self._repository = repository or CatalogRepository()

    async def list_opportunities(self, session: AsyncSession) -> list[OpportunityRead]:
        entities = await self._repository.list_opportunities(session)
        return [OpportunityRead.model_validate(e) for e in entities]

    async def get_opportunity(self, session: AsyncSession, opportunity_id: UUID) -> OpportunityRead | None:
        entity = await self._repository.get_opportunity(session, opportunity_id)
        return OpportunityRead.model_validate(entity) if entity else None

    async def list_universities(self, session: AsyncSession) -> list[UniversityRead]:
        entities = await self._repository.list_universities(session)
        return [UniversityRead.model_validate(e) for e in entities]


class OpportunityService(CatalogService):
    """Opportunity-specific alias for CatalogService."""
    pass

from typing import Iterable
from app.modules.opportunities.schemas import CandidateOpportunity


def _parse_deadline(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


class CatalogSyncService:
    def __init__(
        self,
        opportunity_repository: OpportunityRepository | None = None,
        university_repository: UniversityRepository | None = None,
        professor_repository: ProfessorRepository | None = None,
    ) -> None:
        self._opportunity_repository = opportunity_repository or OpportunityRepository()
        self._university_repository = university_repository or UniversityRepository()
        self._professor_repository = professor_repository or ProfessorRepository()

    async def sync_candidates_to_catalog(self, session: AsyncSession, candidates: Iterable[CandidateOpportunity]) -> None:
        for candidate in candidates:
            if candidate.university:
                await self._university_repository.upsert_by_name(
                    session,
                    name=candidate.university,
                    country=candidate.country,
                    website_url=candidate.official_url if not candidate.professor_name else None,
                    description=None,
                )

            if candidate.professor_name:
                await self._professor_repository.upsert_by_name_and_university(
                    session,
                    name=candidate.professor_name,
                    university=candidate.university,
                    research_interests=candidate.research_areas,
                    profile_url=candidate.official_url,
                )

            if candidate.funding_type:
                await self._opportunity_repository.upsert_by_title(
                    session,
                    title=candidate.title,
                    university=candidate.university,
                    degree_level=candidate.degree_level,
                    country=candidate.country,
                    field=", ".join(candidate.research_areas) if candidate.research_areas else None,
                    funding_type=candidate.funding_type,
                    deadline=_parse_deadline(candidate.deadline),
                    application_url=candidate.official_url,
                    description=None,
                )
