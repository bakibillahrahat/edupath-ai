from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.llm.base import LLMCallContext
from app.modules.ai_orchestration.tools import OpportunitySearchTool, ProfessorSearchTool, UniversitySearchTool, WebSearchTool
from app.modules.ai_orchestration.tools.page_extractor import PageExtractorTool

_PROFESSOR_RELEVANCE_KEYWORDS = (
    "professor", "supervisor", "advisor", "faculty", "research group",
    "phd", "doctorate", "research",
)


def _professor_discovery_relevant(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in _PROFESSOR_RELEVANCE_KEYWORDS)


class ToolingService:
    def __init__(
        self,
        web_search: WebSearchTool | None = None,
        university_search: UniversitySearchTool | None = None,
        professor_search: ProfessorSearchTool | None = None,
        opportunity_search: OpportunitySearchTool | None = None,
        page_extractor: PageExtractorTool | None = None,
    ) -> None:
        self._web_search = web_search or WebSearchTool()
        self._university_search = university_search or UniversitySearchTool()
        self._professor_search = professor_search or ProfessorSearchTool()
        self._opportunity_search = opportunity_search or OpportunitySearchTool()
        self._page_extractor = page_extractor or PageExtractorTool()

    async def build_context(self, session: AsyncSession, query: str) -> list[dict]:
        results = []

        university_result = await self._university_search.search(session, query, limit=3)
        professor_result = await self._professor_search.search(session, query, limit=3)
        opportunity_result = await self._opportunity_search.search(session, query, limit=3)
        web_result = await self._web_search.search(query, limit=3)

        for item in (university_result, professor_result, opportunity_result, web_result):
            results.append(item.model_dump())

        # Automated professor finder: real, sourced discovery from a matched
        # university's own official faculty directory, instead of staying
        # empty forever. Deliberately capped to a single extra retrieval pass
        # per workflow run and gated by a cheap keyword check, since this runs
        # before the graph's own per-agent quota accounting even starts.
        if _professor_discovery_relevant(query):
            match = self._first_university_with_faculty_directory(university_result)
            if match:
                university_name, directory_url = match
                faculty_result = await self._page_extractor.fetch_and_extract(
                    directory_url,
                    tool_name="faculty_directory_search",
                    entity_description="Extract real faculty/professor names from this university department page.",
                    context=LLMCallContext(purpose="faculty_directory_extraction"),
                    extra_metadata={"university": university_name},
                )
                results.append(faculty_result.model_dump())

        return results

    @staticmethod
    def _first_university_with_faculty_directory(university_result) -> tuple[str, str] | None:
        for result in university_result.results:
            url = (result.metadata or {}).get("faculty_directory_url")
            if url:
                return result.title, url
        return None
