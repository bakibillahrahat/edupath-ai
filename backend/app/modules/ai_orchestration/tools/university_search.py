from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.opportunities.repository import UniversityRepository
from app.modules.ai_orchestration.schemas import ToolSearchResponse, ToolSearchResult, ToolSource


class UniversitySearchTool:
    def __init__(self, repository: UniversityRepository | None = None) -> None:
        self._repository = repository or UniversityRepository()

    async def search(self, session: AsyncSession, query: str, limit: int = 5) -> ToolSearchResponse:
        universities = await self._repository.search(session, query, limit=limit)
        results = [
            ToolSearchResult(
                title=university.name,
                description=university.description,
                source=ToolSource(
                    source="postgresql",
                    url=university.website_url,
                    retrieved_at=datetime.now(UTC),
                    confidence=0.8,
                ),
                metadata={"country": university.country, "faculty_directory_url": university.faculty_directory_url},
            )
            for university in universities
        ]
        return ToolSearchResponse(tool_name="university_search", query=query, results=results)
