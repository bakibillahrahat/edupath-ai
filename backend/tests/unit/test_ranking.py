from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.ai_orchestration.graph.ranking import rank_opportunities
from app.modules.opportunities.schemas import (
    CandidateOpportunity,
    EligibilityVerdict,
    Evidence,
    RankedOpportunity,
    ResearchMatchVerdict,
    VerificationVerdict,
)


def _candidate(id_: str, **kwargs) -> CandidateOpportunity:
    defaults = {"id": id_, "title": f"Opportunity {id_}", "created_by": "test"}
    defaults.update(kwargs)
    return CandidateOpportunity(**defaults)


def test_rank_opportunities_orders_by_weighted_score():
    near_deadline = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    candidates = [
        _candidate("strong", funding_type="Fully Funded", professor_name="Dr. A", deadline=near_deadline),
        _candidate("weak"),
    ]
    eligibility = [
        EligibilityVerdict(opportunity_id="strong", eligible="verified_eligible", confidence=0.9, explanation="Meets GPA requirement."),
        EligibilityVerdict(opportunity_id="weak", eligible="unknown", confidence=0.2, explanation="No data."),
    ]
    research_match = [
        ResearchMatchVerdict(
            opportunity_id="strong", overall_match=0.9, interest_overlap=0.9,
            technical_overlap=0.85, experience_alignment=0.8, program_alignment=0.9,
            explanation="Strong AI/ML overlap.",
        ),
        ResearchMatchVerdict(
            opportunity_id="weak", overall_match=0.1, interest_overlap=0.1,
            technical_overlap=0.1, experience_alignment=0.1, program_alignment=0.1,
            explanation="Little overlap.",
        ),
    ]

    ranked = rank_opportunities(candidates, eligibility, research_match)

    assert [r.opportunity_id for r in ranked] == ["strong", "weak"]
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    assert ranked[0].overall_score > ranked[1].overall_score
    # Score breakdown keys are stable and sum to the overall score.
    assert set(ranked[0].score_breakdown) == {
        "research_match", "eligibility", "funding", "professor_match", "university_tier", "deadline_urgency",
    }
    assert abs(sum(ranked[0].score_breakdown.values()) - ranked[0].overall_score) < 1e-6


def test_rank_opportunities_handles_missing_verdicts_without_crashing():
    candidates = [_candidate("no-data")]
    ranked = rank_opportunities(candidates, eligibility_verdicts=[], research_match_verdicts=[])

    assert len(ranked) == 1
    assert ranked[0].opportunity_id == "no-data"
    # No verdict data => conservative, non-zero-fabricated defaults, not a crash.
    assert 0.0 <= ranked[0].overall_score <= 1.0


def test_rank_opportunities_empty_candidates_returns_empty_list():
    assert rank_opportunities([], [], []) == []


def test_rank_opportunities_past_deadline_scores_lower_than_near_deadline():
    past = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    near = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    candidates = [_candidate("past", deadline=past), _candidate("near", deadline=near)]

    ranked = rank_opportunities(candidates, [], [])
    by_id = {r.opportunity_id: r for r in ranked}

    assert by_id["near"].score_breakdown["deadline_urgency"] > by_id["past"].score_breakdown["deadline_urgency"]


def test_evidence_and_candidate_serialize_round_trip():
    evidence = Evidence(
        claim="Fully funded PhD in AI",
        source_url="https://example.edu/phd",
        source_title="Example University PhD Program",
        source_type="official_university",
        verified=True,
        retrieved_at=datetime.now(UTC),
    )
    candidate = _candidate("example", evidence=[evidence], official_url="https://example.edu/phd")

    dumped = candidate.model_dump()
    restored = CandidateOpportunity.model_validate(dumped)

    assert restored.evidence[0].source_url == "https://example.edu/phd"
    assert restored.official_url == "https://example.edu/phd"
