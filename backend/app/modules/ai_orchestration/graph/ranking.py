from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import settings
from app.modules.opportunities.schemas import (
    CandidateOpportunity,
    EligibilityVerdict,
    RankedOpportunity,
    ResearchMatchVerdict,
)

_ELIGIBILITY_SCORES = {
    "verified_eligible": 1.0,
    "likely_eligible": 0.7,
    "unknown": 0.4,
    "verified_ineligible": 0.0,
}
_NO_ELIGIBILITY_DATA_SCORE = 0.3


def _eligibility_score(verdict: EligibilityVerdict | None) -> float:
    if verdict is None:
        return _NO_ELIGIBILITY_DATA_SCORE
    return _ELIGIBILITY_SCORES.get(verdict.eligible, _NO_ELIGIBILITY_DATA_SCORE)


def _deadline_urgency_score(deadline: str | None) -> float:
    """Opportunities with a real, near-but-not-past deadline score higher --
    they need action soonest. No deadline data => neutral score, not a
    fabricated urgency."""
    if not deadline:
        return 0.5
    try:
        parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    except ValueError:
        return 0.5
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    days_remaining = (parsed - datetime.now(UTC)).days
    if days_remaining < 0:
        return 0.0
    if days_remaining <= 30:
        return 1.0
    if days_remaining <= 90:
        return 0.75
    if days_remaining <= 180:
        return 0.5
    return 0.3


def rank_opportunities(
    candidates: list[CandidateOpportunity],
    eligibility_verdicts: list[EligibilityVerdict],
    research_match_verdicts: list[ResearchMatchVerdict],
) -> list[RankedOpportunity]:
    """Deterministic, configurable weighted ranking -- no LLM call. Weights
    come from settings.ranking_weight_* (sum to 1.0) so they're adjustable
    without touching this function."""
    eligibility_by_id = {v.opportunity_id: v for v in eligibility_verdicts}
    research_by_id = {v.opportunity_id: v for v in research_match_verdicts}

    weights = {
        "research_match": settings.ranking_weight_research_match,
        "eligibility": settings.ranking_weight_eligibility,
        "funding": settings.ranking_weight_funding,
        "professor_match": settings.ranking_weight_professor_match,
        "university_tier": settings.ranking_weight_university_tier,
        "deadline_urgency": settings.ranking_weight_deadline_urgency,
    }

    scored: list[tuple[str, float, dict[str, float]]] = []
    for candidate in candidates:
        research_verdict = research_by_id.get(candidate.id)
        research_score = research_verdict.overall_match if research_verdict else 0.0
        eligibility_score = _eligibility_score(eligibility_by_id.get(candidate.id))
        funding_score = 1.0 if candidate.funding_type else 0.0
        # Professor match rides on the same research alignment score, but
        # only counts when a real professor is actually attached.
        professor_score = research_score if candidate.professor_name else 0.0
        # No independent university-tier dataset exists (deliberately not
        # fabricating a ranking of institutions) -- neutral weight for every
        # candidate until one is curated.
        university_score = 0.5
        deadline_score = _deadline_urgency_score(candidate.deadline)

        breakdown = {
            "research_match": round(research_score * weights["research_match"], 4),
            "eligibility": round(eligibility_score * weights["eligibility"], 4),
            "funding": round(funding_score * weights["funding"], 4),
            "professor_match": round(professor_score * weights["professor_match"], 4),
            "university_tier": round(university_score * weights["university_tier"], 4),
            "deadline_urgency": round(deadline_score * weights["deadline_urgency"], 4),
        }
        overall = round(sum(breakdown.values()), 4)
        scored.append((candidate.id, overall, breakdown))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [
        RankedOpportunity(opportunity_id=opportunity_id, overall_score=overall_score, score_breakdown=breakdown, rank=index + 1)
        for index, (opportunity_id, overall_score, breakdown) in enumerate(scored)
    ]
