from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.opportunities.repository import ProfessorRepository
from app.modules.ai_orchestration.schemas import ToolSearchResponse, ToolSearchResult, ToolSource


class ProfessorSearchTool:
    def __init__(self, repository: ProfessorRepository | None = None) -> None:
        self._repository = repository or ProfessorRepository()

    async def search(self, session: AsyncSession, query: str, limit: int = 5) -> ToolSearchResponse:
        professors = await self._repository.search(session, query, limit=limit)
        results = [
            ToolSearchResult(
                title=professor.name,
                description=f"{professor.department or ''} at {professor.university or ''}".strip(),
                source=ToolSource(
                    source="postgresql",
                    url=professor.profile_url,
                    retrieved_at=datetime.now(UTC),
                    confidence=0.8,
                ),
                metadata={
                    "university": professor.university,
                    "department": professor.department,
                    "research_interests": professor.research_interests,
                },
            )
            for professor in professors
        ]
        return ToolSearchResponse(tool_name="professor_search", query=query, results=results)
