from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.agents.context import ensure_llm_budget, grounded_context, summarize_candidates
from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.llm.openrouter import get_openrouter_provider
from app.llm.usage import serialize_usage
from app.schemas.agent import AgentMessage, AgentResult
from app.schemas.opportunity_candidate import EligibilityVerdict


class EligibilityAgentOutput(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str = "research_match_agent"
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float = 0.75
    evaluations: list[EligibilityVerdict] = Field(default_factory=list)


def build_eligibility_agent(provider=None):
    provider = provider or get_openrouter_provider()

    def eligibility_agent(state: dict) -> dict:
        user_request = state.get("user_request") or state.get("user_input", "")
        profile = state.get("profile", {})
        candidates = state.get("candidate_opportunities", [])
        started_at = datetime.now(UTC)
        call_number, call_context = ensure_llm_budget(state, agent_name="eligibility_agent", purpose="eligibility_review")

        prompt = f"""
You are EduPath AI's Eligibility Evaluation Agent.

For EACH candidate opportunity below, assess whether the student is likely eligible by comparing
the student's profile (GPA, degree, academic level) against the candidate's known requirements.

Student request:
{user_request}

Student profile:
{profile}

Candidate opportunities to evaluate (evaluate every one; opportunity_id must match exactly):
{summarize_candidates(candidates)}
{grounded_context(state, {"opportunity_search", "university_search", "web_search"})}

For each candidate, classify eligible as one of: "verified_eligible" (requirement explicitly
confirmed by evidence), "likely_eligible" (reasonable estimate, not explicitly confirmed),
"verified_ineligible", or "unknown" (insufficient information -- prefer this over guessing).
For each evaluation, include:
- opportunity_id (matching candidate id)
- eligible (verdict)
- confidence (float)
- explanation (rationale)
- ielts_score (e.g. "IELTS 6.5 - 7.0 minimum")
- required_documents (list of documents, e.g. ["Official Transcripts", "Statement of Purpose (SOP)", "3 Letters of Recommendation", "Academic CV"])
- missing_requirements and warnings

If the candidate list above is empty, return an empty evaluations list.

Return JSON with summary, key_findings, recommended_next_agent, supervisor_message, next_agent_message, confidence, evaluations.
"""

        try:
            structured, raw_result = provider.generate_structured(
                prompt,
                response_model=EligibilityAgentOutput,
                model=settings.openrouter_model,
                context=call_context,
            )
        except LLMQuotaError:
            raise
        except LLMError as exc:
            error_message = f"Eligibility agent failed during LLM call: {exc}"
            return {
                "errors": [error_message],
                "llm_call_count": call_number,
                "agent_messages": [
                    AgentMessage(
                        sender="eligibility_agent",
                        receiver="supervisor",
                        message_type="error",
                        content=f"Failed to generate eligibility review. Reason: {exc}",
                    )
                ],
            }
        completed_at = datetime.now(UTC)

        result = AgentResult(
            agent_name="eligibility_agent",
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
            "eligibility_review": structured.model_dump(exclude={"evaluations"}),
            "eligibility_verdicts": structured.evaluations,
            "agent_results": [result],
            "llm_call_count": call_number,
            "agent_messages": [
                AgentMessage(
                    sender="eligibility_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=structured.supervisor_message,
                )
            ],
            "tool_results": [],
            "memory_references": [],
        }

    return eligibility_agent


eligibility_agent = build_eligibility_agent()
