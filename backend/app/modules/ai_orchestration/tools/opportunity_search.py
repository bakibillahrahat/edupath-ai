from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.search import extract_keywords
from app.modules.opportunities.repository import OpportunityRepository
from app.modules.ai_orchestration.schemas import ToolSearchResponse, ToolSearchResult, ToolSource


class OpportunitySearchTool:
    def __init__(self, repository: OpportunityRepository | None = None) -> None:
        self._repository = repository or OpportunityRepository()

    async def search(self, session: AsyncSession, query: str, limit: int = 5) -> ToolSearchResponse:
        opportunities = await self._repository.list(session)
        keywords = extract_keywords(query)
        filtered = [
            opportunity
            for opportunity in opportunities
            if keywords
            and any(
                keyword
                in " ".join(
                    filter(
                        None,
                        [
                            opportunity.title,
                            opportunity.provider or "",
                            opportunity.university or "",
                            opportunity.field or "",
                            opportunity.funding_type or "",
                            opportunity.degree_level or "",
                        ],
                    )
                ).lower()
                for keyword in keywords
            )
        ]
        results = [
            ToolSearchResult(
                title=opportunity.title,
                description=opportunity.description,
                source=ToolSource(
                    source="postgresql",
                    url=opportunity.application_url or opportunity.source_url,
                    retrieved_at=datetime.now(UTC),
                    confidence=0.85,
                ),
                metadata={
                    "university": opportunity.university,
                    "degree_level": opportunity.degree_level,
                    "country": opportunity.country,
                    "funding_type": opportunity.funding_type,
                    "field": opportunity.field,
                    "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
                },
            )
            for opportunity in filtered[:limit]
        ]
        return ToolSearchResponse(tool_name="opportunity_search", query=query, results=results)
