from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.ai_orchestration.tools.opportunity_search import OpportunitySearchTool
from app.modules.ai_orchestration.tools.professor_search import ProfessorSearchTool
from app.modules.ai_orchestration.tools.university_search import UniversitySearchTool
from app.modules.ai_orchestration.tools.web_search import WebSearchTool


class FakeUniversity:
    def __init__(self, name: str, country: str = "USA", website_url: str | None = None, description: str | None = None, faculty_directory_url: str | None = None) -> None:
        self.name = name
        self.country = country
        self.website_url = website_url
        self.description = description
        self.faculty_directory_url = faculty_directory_url


class FakeProfessor:
    def __init__(self, name: str, university: str = "Test U", department: str = "CS", profile_url: str | None = None) -> None:
        self.name = name
        self.university = university
        self.department = department
        self.profile_url = profile_url
        self.research_interests = ["AI", "ML"]
        self.publications = ["Paper 1"]


class FakeOpportunity:
    def __init__(self, title: str, university: str = "Test U", field: str = "CS") -> None:
        self.title = title
        self.provider = "Test Provider"
        self.university = university
        self.degree_level = "PhD"
        self.country = "USA"
        self.field = field
        self.funding_type = "Scholarship"
        self.application_url = "https://example.com/apply"
        self.source_url = "https://example.com/source"
        self.description = "Test opportunity"
        self.deadline = None


class FakeUniversityRepository:
    async def search(self, session, query, limit=5):
        return [FakeUniversity("Test University", website_url="https://testu.edu", description="Strong AI program")]


class FakeProfessorRepository:
    async def search(self, session, query, limit=5):
        return [FakeProfessor("Dr. Example", profile_url="https://testu.edu/prof")]


class FakeOpportunityRepository:
    async def list(self, session):
        return [FakeOpportunity("Fully Funded PhD in AI")]


@pytest.mark.asyncio
async def test_university_search_tool_formats_results() -> None:
    tool = UniversitySearchTool(repository=FakeUniversityRepository())
    response = await tool.search(SimpleNamespace(), "AI university", limit=3)

    assert response.tool_name == "university_search"
    assert response.results[0].title == "Test University"
    assert response.results[0].source.url == "https://testu.edu"


@pytest.mark.asyncio
async def test_professor_search_tool_formats_results() -> None:
    tool = ProfessorSearchTool(repository=FakeProfessorRepository())
    response = await tool.search(SimpleNamespace(), "AI professor", limit=3)

    assert response.tool_name == "professor_search"
    assert response.results[0].title == "Dr. Example"
    assert response.results[0].source.url == "https://testu.edu/prof"


@pytest.mark.asyncio
async def test_opportunity_search_tool_formats_results() -> None:
    tool = OpportunitySearchTool(repository=FakeOpportunityRepository())
    response = await tool.search(SimpleNamespace(), "funded PhD", limit=3)

    assert response.tool_name == "opportunity_search"
    assert response.results[0].title == "Fully Funded PhD in AI"
    assert response.results[0].source.url == "https://example.com/apply"


@pytest.mark.asyncio
async def test_web_search_tool_handles_disabled_config() -> None:
    tool = WebSearchTool()
    response = await tool.search("phd scholarships", limit=3)

    assert response.tool_name == "web_search"
    assert response.results == []
    assert response.notes
