from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.opportunities.schemas import CandidateOpportunity
from app.modules.opportunities.service import CatalogSyncService


class FakeUniversityRepository:
    def __init__(self) -> None:
        self.upserts: list[dict] = []

    async def upsert_by_name(self, session, **kwargs):
        self.upserts.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeProfessorRepository:
    def __init__(self) -> None:
        self.upserts: list[dict] = []

    async def upsert_by_name_and_university(self, session, **kwargs):
        self.upserts.append(kwargs)
        return SimpleNamespace(**kwargs)


class FakeOpportunityRepository:
    def __init__(self) -> None:
        self.upserts: list[dict] = []

    async def upsert_by_title(self, session, **kwargs):
        self.upserts.append(kwargs)
        return SimpleNamespace(**kwargs)


def _candidate(**overrides) -> CandidateOpportunity:
    defaults = {"id": "c1", "title": "Some Opportunity", "created_by": "test"}
    defaults.update(overrides)
    return CandidateOpportunity(**defaults)


@pytest.mark.asyncio
async def test_university_candidate_upserts_only_university():
    universities, professors, opportunities = FakeUniversityRepository(), FakeProfessorRepository(), FakeOpportunityRepository()
    service = CatalogSyncService(opportunity_repository=opportunities, university_repository=universities, professor_repository=professors)

    candidate = _candidate(title="PhD in Computer Science", university="Example University", country="USA", official_url="https://example.edu/phd")
    await service.sync_candidates_to_catalog(SimpleNamespace(), [candidate])

    assert len(universities.upserts) == 1
    assert universities.upserts[0]["name"] == "Example University"
    assert len(professors.upserts) == 0
    assert len(opportunities.upserts) == 0


@pytest.mark.asyncio
async def test_professor_candidate_upserts_university_and_professor():
    universities, professors, opportunities = FakeUniversityRepository(), FakeProfessorRepository(), FakeOpportunityRepository()
    service = CatalogSyncService(opportunity_repository=opportunities, university_repository=universities, professor_repository=professors)

    candidate = _candidate(
        title="Dr. Jane Smith", university="Example University", professor_name="Dr. Jane Smith",
        research_areas=["AI", "ML"], official_url="https://example.edu/~jsmith/",
    )
    await service.sync_candidates_to_catalog(SimpleNamespace(), [candidate])

    assert len(universities.upserts) == 1
    assert len(professors.upserts) == 1
    assert professors.upserts[0]["name"] == "Dr. Jane Smith"
    assert professors.upserts[0]["research_interests"] == ["AI", "ML"]
    assert len(opportunities.upserts) == 0


@pytest.mark.asyncio
async def test_funded_candidate_upserts_opportunity_non_exclusively_with_university():
    """A candidate can legitimately match more than one category -- a
    university program that's also fully funded should sync to BOTH
    tables, not just one (same fix already applied to Excel export)."""
    universities, professors, opportunities = FakeUniversityRepository(), FakeProfessorRepository(), FakeOpportunityRepository()
    service = CatalogSyncService(opportunity_repository=opportunities, university_repository=universities, professor_repository=professors)

    candidate = _candidate(
        title="Fully Funded PhD in AI", university="Example University", funding_type="Fully Funded",
        degree_level="PhD", country="USA", deadline="2027-01-15T00:00:00+00:00",
    )
    await service.sync_candidates_to_catalog(SimpleNamespace(), [candidate])

    assert len(universities.upserts) == 1
    assert len(opportunities.upserts) == 1
    assert opportunities.upserts[0]["title"] == "Fully Funded PhD in AI"
    assert opportunities.upserts[0]["funding_type"] == "Fully Funded"
    assert opportunities.upserts[0]["deadline"] is not None  # parsed from the ISO string, not left as a raw str


@pytest.mark.asyncio
async def test_candidate_with_no_university_professor_or_funding_syncs_nothing():
    universities, professors, opportunities = FakeUniversityRepository(), FakeProfessorRepository(), FakeOpportunityRepository()
    service = CatalogSyncService(opportunity_repository=opportunities, university_repository=universities, professor_repository=professors)

    await service.sync_candidates_to_catalog(SimpleNamespace(), [_candidate(title="Untitled")])

    assert universities.upserts == []
    assert professors.upserts == []
    assert opportunities.upserts == []


@pytest.mark.asyncio
async def test_malformed_deadline_string_does_not_crash_sync():
    universities, professors, opportunities = FakeUniversityRepository(), FakeProfessorRepository(), FakeOpportunityRepository()
    service = CatalogSyncService(opportunity_repository=opportunities, university_repository=universities, professor_repository=professors)

    candidate = _candidate(title="Odd Deadline Opportunity", funding_type="Fully Funded", deadline="not-a-real-date")
    await service.sync_candidates_to_catalog(SimpleNamespace(), [candidate])

    assert opportunities.upserts[0]["deadline"] is None
