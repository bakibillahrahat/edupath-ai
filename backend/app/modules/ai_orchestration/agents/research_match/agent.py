from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.modules.ai_orchestration.agents.context import ensure_llm_budget, summarize_candidates
from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.infrastructure.llm.usage import serialize_usage
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult
from app.modules.opportunities.schemas import ResearchMatchVerdict


class ResearchMatchAgentOutput(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str = "verification_agent"
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float = 0.75
    evaluations: list[ResearchMatchVerdict] = Field(default_factory=list)


def build_research_match_agent(provider=None):
    provider = provider or get_openrouter_provider()

    def research_match_agent(state: dict) -> dict:
        profile = state.get("profile", {})
        candidates = state.get("candidate_opportunities", [])
        started_at = datetime.now(UTC)
        call_number, call_context = ensure_llm_budget(state, agent_name="research_match_agent", purpose="research_match")

        prompt = f"""
You are EduPath AI's Research Match Agent.

For EACH candidate opportunity below, score how well it aligns with the student's research
background, on a 0.0-1.0 scale for each dimension:
- interest_overlap: overlap between the student's stated research_interests and the
  candidate's research_areas/professor_name.
- technical_overlap: overlap between the student's skills and what the candidate's field
  plausibly requires.
- experience_alignment: how well the student's publications/projects/work_experience support
  this candidate.
- program_alignment: how well the candidate's degree_level/field matches the student's stated
  target_degree and goals.
overall_match should be a reasonable weighted combination of the four, not just their average.

Student profile (research_interests, skills, publications, projects, target_degree):
{profile}

Candidate opportunities to evaluate (evaluate every one; opportunity_id must match exactly):
{summarize_candidates(candidates)}

Ground every score in the student profile and candidate fields actually provided -- do not
invent research alignment that isn't supported by the data. If the candidate list above is
empty, return an empty evaluations list.

Return JSON with summary, key_findings, recommended_next_agent, supervisor_message, next_agent_message, confidence, evaluations.
"""

        try:
            structured, raw_result = provider.generate_structured(
                prompt,
                response_model=ResearchMatchAgentOutput,
                model=settings.openrouter_model,
                context=call_context,
            )
        except LLMQuotaError:
            raise
        except LLMError as exc:
            error_message = f"Research match agent failed during LLM call: {exc}"
            return {
                "errors": [error_message],
                "llm_call_count": call_number,
                "agent_messages": [
                    AgentMessage(
                        sender="research_match_agent",
                        receiver="supervisor",
                        message_type="error",
                        content=f"Failed to generate research match analysis. Reason: {exc}",
                    )
                ],
            }
        completed_at = datetime.now(UTC)

        result = AgentResult(
            agent_name="research_match_agent",
            summary=structured.summary,
            key_findings=structured.key_findings,
            recommended_next_agent=structured.recommended_next_agent,
            supervisor_message=structured.supervisor_message,
            next_agent_message=structured.next_agent_message,
            confidence=structured.confidence,
            raw_output=raw_result.text,
            started_at=started_at,
            completed_at=completed_at,
            token_usage=serialize_usage(raw_result.usage),
            estimated_cost_usd=raw_result.usage.estimated_cost_usd,
        )

        return {
            "research_match_verdicts": structured.evaluations,
            "agent_results": [result],
            "llm_call_count": call_number,
            "agent_messages": [
                AgentMessage(
                    sender="research_match_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=structured.supervisor_message,
                )
            ],
            "tool_results": [],
            "memory_references": [],
        }

    return research_match_agent


research_match_agent = build_research_match_agent()
