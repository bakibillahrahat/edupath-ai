"""
Opportunities, Universities, and Professors Domain Repository.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.opportunities.models import Opportunity, Professor, Program, University


class UniversityRepository:
    async def get_by_id(self, session: AsyncSession, university_id: UUID) -> University | None:
        return await session.get(University, university_id)

    async def get_by_name(self, session: AsyncSession, name: str) -> University | None:
        return await session.scalar(select(University).where(University.name == name))

    async def upsert_by_name(
        self, session: AsyncSession, name: str, country: str | None = None,
        website_url: str | None = None, description: str | None = None,
    ) -> University:
        existing = await self.get_by_name(session, name)
        if existing:
            if country:
                existing.country = country
            if website_url:
                existing.website_url = website_url
            if description:
                existing.description = description
            await session.commit()
            await session.refresh(existing)
            return existing
        uni = University(name=name, country=country or "", website_url=website_url, description=description)
        session.add(uni)
        await session.commit()
        await session.refresh(uni)
        return uni

    async def list(self, session: AsyncSession, *, limit: int = 50) -> list[University]:
        stmt = select(University).limit(limit)
        return list((await session.scalars(stmt)).all())

    async def search(self, session: AsyncSession, query: str) -> list[University]:
        stmt = select(University).where(University.name.ilike(f"%{query}%")).limit(20)
        return list((await session.scalars(stmt)).all())


class ProfessorRepository:
    async def get_by_id(self, session: AsyncSession, professor_id: UUID) -> Professor | None:
        return await session.get(Professor, professor_id)

    async def upsert_by_name_and_university(
        self, session: AsyncSession, name: str, university: str | None = None,
        research_interests: list[str] | None = None, profile_url: str | None = None,
    ) -> Professor:
        stmt = select(Professor).where(Professor.name == name)
        existing = await session.scalar(stmt)
        if existing:
            if research_interests:
                existing.research_interests = ", ".join(research_interests) if isinstance(research_interests, list) else str(research_interests)
            if profile_url:
                existing.profile_url = profile_url
            await session.commit()
            await session.refresh(existing)
            return existing
        prof = Professor(
            name=name,
            research_interests=", ".join(research_interests) if isinstance(research_interests, list) else str(research_interests or ""),
            profile_url=profile_url,
        )
        session.add(prof)
        await session.commit()
        await session.refresh(prof)
        return prof

    async def search(self, session: AsyncSession, query: str, university_id: UUID | None = None) -> list[Professor]:
        stmt = select(Professor).where(
            (Professor.name.ilike(f"%{query}%")) | (Professor.research_interests.ilike(f"%{query}%"))
        )
        if university_id:
            stmt = stmt.where(Professor.university_id == university_id)
        return list((await session.scalars(stmt.limit(20))).all())


class OpportunityRepository:
    async def get_by_id(self, session: AsyncSession, opportunity_id: UUID) -> Opportunity | None:
        return await session.get(Opportunity, opportunity_id)

    async def list(self, session: AsyncSession, *, limit: int = 50) -> list[Opportunity]:
        stmt = select(Opportunity).limit(limit)
        return list((await session.scalars(stmt)).all())

    async def search(self, session: AsyncSession, query: str) -> list[Opportunity]:
        stmt = (
            select(Opportunity)
            .where((Opportunity.title.ilike(f"%{query}%")) | (Opportunity.description.ilike(f"%{query}%")))
            .limit(20)
        )
        return list((await session.scalars(stmt)).all())

    async def upsert_by_title(
        self, session: AsyncSession, title: str, university: str | None = None,
        degree_level: str | None = None, country: str | None = None, field: str | None = None,
        funding_type: str | None = None, deadline: datetime | None = None,
        application_url: str | None = None, description: str | None = None,
    ) -> Opportunity:
        stmt = select(Opportunity).where(Opportunity.title == title)
        existing = await session.scalar(stmt)
        if existing:
            if funding_type:
                existing.funding_type = funding_type
            if deadline:
                existing.deadline = deadline
            if application_url:
                existing.application_url = application_url
            await session.commit()
            await session.refresh(existing)
            return existing
        opp = Opportunity(
            title=title,
            degree_level=degree_level or "Masters",
            field=field or "General",
            funding_type=funding_type,
            deadline=deadline,
            application_url=application_url,
            description=description or "",
        )
        session.add(opp)
        await session.commit()
        await session.refresh(opp)
        return opp


CatalogRepository = OpportunityRepository

__all__ = [
    "UniversityRepository",
    "ProfessorRepository",
    "OpportunityRepository",
    "CatalogRepository",
]
