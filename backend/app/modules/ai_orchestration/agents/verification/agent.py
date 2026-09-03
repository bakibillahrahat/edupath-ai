from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.modules.ai_orchestration.agents.context import ensure_llm_budget, grounded_context, summarize_candidates
from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.infrastructure.llm.usage import serialize_usage
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult
from app.modules.opportunities.schemas import VerificationVerdict


class VerificationAgentOutput(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str = "ranking_agent"
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float = 0.85
    evaluations: list[VerificationVerdict] = Field(default_factory=list)


def build_verification_agent(provider=None):
    provider = provider or get_openrouter_provider()

    def verification_agent(state: dict) -> dict:
        candidates = state.get("candidate_opportunities", [])
        started_at = datetime.now(UTC)
        call_number, call_context = ensure_llm_budget(state, agent_name="verification_agent", purpose="cross_agent_verification")

        prompt = f"""
You are EduPath AI's Verification Agent.

For EACH candidate opportunity below, judge whether its key facts (official_url, university,
deadline) look verified, unverified, or possibly stale, based ONLY on the evidence already
attached to it and the tool results below. You cannot browse the web yourself -- you are
auditing what other agents already found, not re-discovering it.

- "verified": the candidate has a concrete official_url and consistent supporting evidence.
- "unverified": no official_url or no supporting evidence was attached.
- "stale_suspected": evidence exists but looks outdated or internally inconsistent.

Never mark something "verified" just because it sounds plausible -- only when real evidence is
present. List which fields you actually checked in checked_fields.

Candidate opportunities to audit (opportunity_id must match exactly):
{summarize_candidates(candidates)}
{grounded_context(state, {"opportunity_search", "professor_search", "university_search", "web_search"})}

If the candidate list above is empty, return an empty evaluations list.

Return JSON with summary, key_findings, recommended_next_agent, supervisor_message, next_agent_message, confidence, evaluations.
"""

        try:
            structured, raw_result = provider.generate_structured(
                prompt,
                response_model=VerificationAgentOutput,
                model=settings.openrouter_model,
                context=call_context,
            )
        except LLMQuotaError:
            raise
        except LLMError as exc:
            error_message = f"Verification agent failed during LLM call: {exc}"
            return {
                "errors": [error_message],
                "llm_call_count": call_number,
                "agent_messages": [
                    AgentMessage(
                        sender="verification_agent",
                        receiver="supervisor",
                        message_type="error",
                        content=f"Failed to generate verification report. Reason: {exc}",
                    )
                ],
            }
        completed_at = datetime.now(UTC)

        result = AgentResult(
            agent_name="verification_agent",
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
            "verification_report": structured.model_dump(exclude={"evaluations"}),
            "verification_verdicts": structured.evaluations,
            "agent_results": [result],
            "llm_call_count": call_number,
            "agent_messages": [
                AgentMessage(
                    sender="verification_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=structured.supervisor_message,
                )
            ],
            "tool_results": [],
            "memory_references": [],
        }

    return verification_agent


verification_agent = build_verification_agent()
