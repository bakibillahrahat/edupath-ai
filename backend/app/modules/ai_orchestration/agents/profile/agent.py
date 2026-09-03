from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.modules.ai_orchestration.agents.context import ensure_llm_budget
from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.infrastructure.llm.usage import serialize_usage
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult


class ProfileAgentOutput(BaseModel):
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str = "professor_agent"
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float = 0.8


def build_profile_agent(provider=None):
    provider = provider or get_openrouter_provider()

    def profile_agent(state: dict) -> dict:
        user_request = state.get("user_request") or state.get("user_input", "")
        started_at = datetime.now(UTC)
        call_number, call_context = ensure_llm_budget(state, agent_name="profile_agent", purpose="profile_analysis")

        prompt = f"""
You are EduPath AI's Profile Analysis Agent.

Analyze the student's request and infer the academic profile signals.

Student request:
{user_request}

Return JSON with:
- summary
- key_findings (array of concise bullets)
- recommended_next_agent
- supervisor_message
- next_agent_message
- confidence
"""

        try:
            structured, raw_result = provider.generate_structured(
                prompt,
                response_model=ProfileAgentOutput,
                model=settings.openrouter_model,
                context=call_context,
            )
        except LLMQuotaError:
            # Quota exhaustion is terminal: propagate so the workflow can
            # surface a 429 instead of silently absorbing and burning the
            # remaining agents' quota.
            raise
        except LLMError as exc:
            error_message = f"Profile agent failed during LLM call: {exc}"
            return {
                "errors": [error_message],
                "llm_call_count": call_number,
                "agent_messages": [
                    AgentMessage(
                        sender="profile_agent",
                        receiver="supervisor",
                        message_type="error",
                        content=f"Failed to generate profile analysis. Reason: {exc}",
                    )
                ],
            }
        completed_at = datetime.now(UTC)

        result = AgentResult(
            agent_name="profile_agent",
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

        existing_profile = dict(state.get("profile") or {})
        updated_profile = {
            **existing_profile,
            **structured.model_dump(),
        }

        return {
            "profile": updated_profile,
            "profile_analysis": structured.model_dump(),
            "agent_results": [result],
            "llm_call_count": call_number,
            "agent_messages": [
                AgentMessage(
                    sender="profile_agent",
                    receiver="supervisor",
                    message_type="analysis",
                    content=structured.supervisor_message,
                )
            ],
            "tool_results": [],
            "memory_references": [],
        }

    return profile_agent


profile_agent = build_profile_agent()
