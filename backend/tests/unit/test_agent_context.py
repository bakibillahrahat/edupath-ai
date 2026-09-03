from __future__ import annotations

from datetime import UTC, datetime

from app.modules.ai_orchestration.agents.context import candidates_from_tool_results, summarize_candidates
from app.modules.opportunities.schemas import CandidateOpportunity


def _tool_result(tool_name: str, results: list[dict]) -> dict:
    return {"tool_name": tool_name, "query": "q", "results": results, "notes": [], "tool_status": "available"}


def test_candidates_from_tool_results_builds_real_candidates_from_db_rows():
    state = {
        "tool_results": [
            _tool_result(
                "opportunity_search",
                [
                    {
                        "title": "Fully Funded PhD in AI",
                        "description": "A funded PhD.",
                        "source": {"source": "postgresql", "url": "https://example.edu/apply", "retrieved_at": datetime.now(UTC), "confidence": 0.85},
                        "metadata": {"university": "Example University", "degree_level": "PhD", "country": "USA", "funding_type": "Fully Funded", "field": "AI", "deadline": "2026-12-01T00:00:00+00:00"},
                    }
                ],
            ),
        ]
    }

    candidates = candidates_from_tool_results(state, {"opportunity_search"}, created_by="scholarship_agent")

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.title == "Fully Funded PhD in AI"
    assert candidate.university == "Example University"
    assert candidate.official_url == "https://example.edu/apply"
    assert candidate.funding_type == "Fully Funded"
    assert candidate.research_areas == ["AI"]
    assert candidate.deadline == "2026-12-01T00:00:00+00:00"
    assert candidate.created_by == "scholarship_agent"
    assert candidate.evidence[0].verified is True
    assert candidate.evidence[0].source_url == "https://example.edu/apply"
    # id is a stable, deterministic slug -- not fabricated by an LLM.
    assert candidate.id == "fully-funded-phd-in-ai-example-university"


def test_candidates_from_tool_results_ignores_unrelated_tools():
    state = {"tool_results": [_tool_result("web_search", [{"title": "irrelevant", "source": {"source": "web", "retrieved_at": datetime.now(UTC)}}])]}

    candidates = candidates_from_tool_results(state, {"opportunity_search"}, created_by="scholarship_agent")

    assert candidates == []


def test_candidates_from_tool_results_never_invents_missing_fields():
    state = {
        "tool_results": [
            _tool_result("professor_search", [{"title": "Dr. Example", "source": {"source": "postgresql", "url": None, "retrieved_at": datetime.now(UTC)}, "metadata": {}}]),
        ]
    }

    candidates = candidates_from_tool_results(state, {"professor_search"}, created_by="professor_agent")

    assert len(candidates) == 1
    assert candidates[0].official_url is None
    # No url => not verified. Never marked verified without a real source.
    assert candidates[0].evidence[0].verified is False


def test_summarize_candidates_is_compact_and_omits_evidence():
    candidate = CandidateOpportunity(id="x", title="X", created_by="test", evidence=[])
    summary = summarize_candidates([candidate])

    assert "evidence" not in summary
    assert '"id": "x"' in summary


def test_summarize_candidates_empty_list():
    assert summarize_candidates([]) == "[]"
