"""
Catalog Domain Repositories (Opportunity and University).
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy import cast, or_, select, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.search import extract_keywords
from app.modules.catalog.models import Opportunity, University


class OpportunityRepository:
    async def list(self, session: AsyncSession) -> list[Opportunity]:
        result = await session.execute(select(Opportunity).order_by(Opportunity.created_at.desc()))
        return list(result.scalars().all())

    async def get(self, session: AsyncSession, opportunity_id: UUID) -> Opportunity | None:
        return await session.get(Opportunity, opportunity_id)

    async def upsert_by_title(
        self,
        session: AsyncSession,
        *,
        title: str,
        university: str | None,
        degree_level: str | None,
        country: str | None,
        field: str | None,
        funding_type: str | None,
        deadline,
        application_url: str | None,
        description: str | None,
    ) -> Opportunity:
        existing = await session.scalar(select(Opportunity).where(Opportunity.title == title))
        if existing is not None:
            existing.university = university or existing.university
            existing.degree_level = degree_level or existing.degree_level
            existing.country = country or existing.country
            existing.field = field or existing.field
            existing.funding_type = funding_type or existing.funding_type
            existing.deadline = deadline or existing.deadline
            existing.application_url = application_url or existing.application_url
            existing.description = description or existing.description
            return existing

        opportunity = Opportunity(
            title=title, university=university, degree_level=degree_level, country=country,
            field=field, funding_type=funding_type, deadline=deadline,
            application_url=application_url, source_url=application_url, description=description,
        )
        session.add(opportunity)
        return opportunity


class UniversityRepository:
    async def search(self, session: AsyncSession, query: str, limit: int = 5) -> list[University]:
        keywords = extract_keywords(query)
        if not keywords:
            return []

        conditions = [
            or_(
                University.name.ilike(f"%{keyword}%"),
                University.country.ilike(f"%{keyword}%"),
                University.description.ilike(f"%{keyword}%"),
                cast(University.metadata_json, Text).ilike(f"%{keyword}%"),
            )
            for keyword in keywords
        ]
        result = await session.execute(select(University).where(or_(*conditions)).limit(limit))
        return list(result.scalars().all())

    async def upsert_by_name(
        self, session: AsyncSession, *, name: str, country: str | None, website_url: str | None, description: str | None
    ) -> University:
        existing = await session.scalar(select(University).where(University.name == name))
        if existing is not None:
            existing.country = country or existing.country
            existing.website_url = website_url or existing.website_url
            existing.description = description or existing.description
            return existing

        university = University(name=name, country=country, website_url=website_url, description=description)
        session.add(university)
        return university
