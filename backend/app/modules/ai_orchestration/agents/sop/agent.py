from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.modules.ai_orchestration.agents.context import ensure_llm_budget
from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.infrastructure.llm.usage import serialize_usage
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult


class SOPAgentOutput(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str = "verification_agent"
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float = 0.7


def build_sop_agent(provider=None):
    provider = provider or get_openrouter_provider()

    def sop_agent(state: dict) -> dict:
        user_request = state.get("user_request") or state.get("user_input", "")
        profile = state.get("profile", {})
        started_at = datetime.now(UTC)
        call_number, call_context = ensure_llm_budget(state, agent_name="sop_agent", purpose="sop_guidance")

        prompt = f"""
You are EduPath AI's SOP Support Agent.

Provide high-level SOP improvement guidance from the request and profile.

Student request:
{user_request}

Profile context:
{profile}

Return JSON with summary, key_findings, recommended_next_agent, supervisor_message, next_agent_message, confidence.
"""

        try:
            structured, raw_result = provider.generate_structured(
                prompt,
                response_model=SOPAgentOutput,
                model=settings.openrouter_model,
                context=call_context,
            )
        except LLMQuotaError:
            raise
        except LLMError as exc:
            error_message = f"SOP agent failed during LLM call: {exc}"
            return {
                "errors": [error_message],
                "llm_call_count": call_number,
                "agent_messages": [
                    AgentMessage(
                        sender="sop_agent",
                        receiver="supervisor",
                        message_type="error",
                        content=f"Failed to generate SOP guidance. Reason: {exc}",
                    )
                ],
            }
        completed_at = datetime.now(UTC)

        result = AgentResult(
            agent_name="sop_agent",
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
            "sop_review": structured.model_dump(),
            "agent_results": [result],
            "llm_call_count": call_number,
            "agent_messages": [
                AgentMessage(
                    sender="sop_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=structured.supervisor_message,
                )
            ],
            "tool_results": [],
            "memory_references": [],
        }

    return sop_agent


sop_agent = build_sop_agent()
