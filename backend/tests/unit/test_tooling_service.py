from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.ai_orchestration.schemas import ToolSearchResponse, ToolSearchResult, ToolSource
from app.modules.ai_orchestration.service import ToolingService, _professor_discovery_relevant


def _empty_response(tool_name: str) -> ToolSearchResponse:
    return ToolSearchResponse(tool_name=tool_name, query="q", results=[])


class FakeSearchTool:
    def __init__(self, response: ToolSearchResponse) -> None:
        self._response = response
        self.calls = 0

    async def search(self, *args, **kwargs):
        self.calls += 1
        return self._response


class FakeWebSearchTool:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, *args, **kwargs):
        self.calls += 1
        return _empty_response("web_search")


class FakePageExtractorTool:
    def __init__(self, response: ToolSearchResponse | None = None) -> None:
        self._response = response or _empty_response("faculty_directory_search")
        self.calls: list[str] = []
        self.extra_metadata_calls: list[dict | None] = []

    async def fetch_and_extract(self, url, *, tool_name, entity_description, context=None, extra_metadata=None):
        self.calls.append(url)
        self.extra_metadata_calls.append(extra_metadata)
        return self._response


def _university_result_with_directory(url: str | None) -> ToolSearchResponse:
    return ToolSearchResponse(
        tool_name="university_search",
        query="q",
        results=[
            ToolSearchResult(
                title="Example University",
                source=ToolSource(source="postgresql", url="https://example.edu", retrieved_at=datetime.now(UTC), confidence=0.8),
                metadata={"country": "USA", "faculty_directory_url": url},
            )
        ],
    )


@pytest.mark.parametrize("query,expected", [
    ("I want to find a PhD supervisor in AI", True),
    ("Looking for professors doing NLP research", True),
    ("I need a scholarship for my Master's", False),
    ("What universities offer online degrees", False),
])
def test_professor_discovery_relevant_keyword_check(query, expected):
    assert _professor_discovery_relevant(query) == expected


@pytest.mark.asyncio
async def test_build_context_triggers_faculty_extraction_when_relevant_and_url_available():
    university_search = FakeSearchTool(_university_result_with_directory("https://example.edu/faculty"))
    page_extractor = FakePageExtractorTool()
    service = ToolingService(
        web_search=FakeWebSearchTool(),
        university_search=university_search,
        professor_search=FakeSearchTool(_empty_response("professor_search")),
        opportunity_search=FakeSearchTool(_empty_response("opportunity_search")),
        page_extractor=page_extractor,
    )

    results = await service.build_context(SimpleNamespace(), "I want a PhD supervisor in machine learning")

    assert page_extractor.calls == ["https://example.edu/faculty"]
    # The source university's name must travel with the extraction so
    # discovered professors can be linked back to it (CatalogSyncService
    # needs this -- without it, extracted professors would have no
    # university association at all).
    assert page_extractor.extra_metadata_calls == [{"university": "Example University"}]
    tool_names = {r["tool_name"] for r in results}
    assert "faculty_directory_search" in tool_names


@pytest.mark.asyncio
async def test_build_context_skips_extraction_when_not_relevant():
    page_extractor = FakePageExtractorTool()
    service = ToolingService(
        web_search=FakeWebSearchTool(),
        university_search=FakeSearchTool(_university_result_with_directory("https://example.edu/faculty")),
        professor_search=FakeSearchTool(_empty_response("professor_search")),
        opportunity_search=FakeSearchTool(_empty_response("opportunity_search")),
        page_extractor=page_extractor,
    )

    results = await service.build_context(SimpleNamespace(), "I want a scholarship for my Master's degree")

    assert page_extractor.calls == []
    tool_names = {r["tool_name"] for r in results}
    assert "faculty_directory_search" not in tool_names


@pytest.mark.asyncio
async def test_build_context_skips_extraction_when_no_university_has_a_directory_url():
    page_extractor = FakePageExtractorTool()
    service = ToolingService(
        web_search=FakeWebSearchTool(),
        university_search=FakeSearchTool(_university_result_with_directory(None)),
        professor_search=FakeSearchTool(_empty_response("professor_search")),
        opportunity_search=FakeSearchTool(_empty_response("opportunity_search")),
        page_extractor=page_extractor,
    )

    results = await service.build_context(SimpleNamespace(), "I want a PhD supervisor in robotics")

    assert page_extractor.calls == []


@pytest.mark.asyncio
async def test_build_context_calls_extractor_at_most_once_even_with_multiple_universities():
    two_universities = ToolSearchResponse(
        tool_name="university_search", query="q",
        results=[
            ToolSearchResult(title="Uni A", source=ToolSource(source="postgresql", url="https://a.edu", retrieved_at=datetime.now(UTC)), metadata={"faculty_directory_url": "https://a.edu/faculty"}),
            ToolSearchResult(title="Uni B", source=ToolSource(source="postgresql", url="https://b.edu", retrieved_at=datetime.now(UTC)), metadata={"faculty_directory_url": "https://b.edu/faculty"}),
        ],
    )
    page_extractor = FakePageExtractorTool()
    service = ToolingService(
        web_search=FakeWebSearchTool(),
        university_search=FakeSearchTool(two_universities),
        professor_search=FakeSearchTool(_empty_response("professor_search")),
        opportunity_search=FakeSearchTool(_empty_response("opportunity_search")),
        page_extractor=page_extractor,
    )

    await service.build_context(SimpleNamespace(), "I want a PhD supervisor in robotics")

    assert len(page_extractor.calls) == 1
