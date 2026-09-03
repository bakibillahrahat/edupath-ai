from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.modules.ai_orchestration.agents.context import candidates_from_tool_results, ensure_llm_budget, grounded_context
from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.infrastructure.llm.usage import serialize_usage
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult


class ScholarshipAgentOutput(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str = "eligibility_agent"
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float = 0.8


def build_scholarship_agent(provider=None):
    provider = provider or get_openrouter_provider()

    def scholarship_agent(state: dict) -> dict:
        user_request = state.get("user_request") or state.get("user_input", "")
        started_at = datetime.now(UTC)
        call_number, call_context = ensure_llm_budget(state, agent_name="scholarship_agent", purpose="scholarship_research")

        candidates = candidates_from_tool_results(state, {"opportunity_search"}, created_by="scholarship_agent")

        prompt = f"""
You are EduPath AI's Scholarship Research Agent.

Analyze the funding signal in the student's request.

Student request:
{user_request}
{grounded_context(state, {"opportunity_search", "web_search"})}

{len(candidates)} candidate funding opportunities were found via database/search tools (already
extracted separately -- do not restate them as structured data). If zero candidates were found,
say so plainly instead of inventing any.

Return JSON with:
- summary
- key_findings
- recommended_next_agent
- supervisor_message
- next_agent_message
- confidence
"""

        try:
            structured, raw_result = provider.generate_structured(
                prompt,
                response_model=ScholarshipAgentOutput,
                model=settings.openrouter_model,
                context=call_context,
            )
        except LLMQuotaError:
            # Quota exhaustion is terminal: propagate so the workflow can
            # surface a 429 instead of silently absorbing and burning the
            # remaining agents' quota.
            raise
        except LLMError as exc:
            error_message = f"Scholarship agent failed during LLM call: {exc}"
            return {
                "errors": [error_message],
                "llm_call_count": call_number,
                "candidate_opportunities": candidates,
                "agent_messages": [
                    AgentMessage(
                        sender="scholarship_agent",
                        receiver="supervisor",
                        message_type="error",
                        content=f"Failed to generate scholarship analysis. Reason: {exc}",
                    )
                ],
            }

        completed_at = datetime.now(UTC)

        result = AgentResult(
            agent_name="scholarship_agent",
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
            "scholarship_research": structured.model_dump(),
            "candidate_opportunities": candidates,
            "agent_results": [result],
            "llm_call_count": call_number,
            "agent_messages": [
                AgentMessage(
                    sender="scholarship_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=structured.supervisor_message,
                )
            ],
        }

    return scholarship_agent


scholarship_agent = build_scholarship_agent()
