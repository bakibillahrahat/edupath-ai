from __future__ import annotations

from datetime import UTC, datetime

from app.modules.ai_orchestration.graph.ranking import rank_opportunities
from app.infrastructure.llm.usage import TokenUsage, serialize_usage
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult


def build_ranking_agent(provider=None):
    """Ranking is deterministic Python scoring (see app/graph/ranking.py),
    not an LLM call -- no provider is used, no LLM quota is spent, and
    token usage is honestly reported as unavailable rather than zero."""

    def ranking_agent(state: dict) -> dict:
        started_at = datetime.now(UTC)
        candidates = state.get("candidate_opportunities", [])
        eligibility_verdicts = state.get("eligibility_verdicts", [])
        research_match_verdicts = state.get("research_match_verdicts", [])

        ranked = rank_opportunities(candidates, eligibility_verdicts, research_match_verdicts)
        completed_at = datetime.now(UTC)

        if ranked:
            top = ranked[0]
            top_candidate = next((c for c in candidates if c.id == top.opportunity_id), None)
            summary = (
                f"Ranked {len(ranked)} candidate opportunit{'y' if len(ranked) == 1 else 'ies'}. "
                f"Top match: {top_candidate.title if top_candidate else top.opportunity_id} "
                f"(score {top.overall_score:.2f})."
            )
            key_findings = [
                f"#{r.rank} {next((c.title for c in candidates if c.id == r.opportunity_id), r.opportunity_id)} - score {r.overall_score:.2f}"
                for r in ranked[:5]
            ]
        else:
            summary = "No candidate opportunities were available to rank."
            key_findings = []

        result = AgentResult(
            agent_name="ranking_agent",
            summary=summary,
            key_findings=key_findings,
            recommended_next_agent="sop_agent",
            supervisor_message=summary,
            confidence=1.0,  # deterministic computation, not an LLM estimate
            started_at=started_at,
            completed_at=completed_at,
            token_usage=serialize_usage(TokenUsage()),
            estimated_cost_usd=0.0,
        )

        return {
            "ranked_opportunities": ranked,
            "agent_results": [result],
            "agent_messages": [
                AgentMessage(
                    sender="ranking_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=summary,
                )
            ],
        }

    return ranking_agent


ranking_agent = build_ranking_agent()
