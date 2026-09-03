from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.infrastructure.llm.usage import TokenUsage


@dataclass(slots=True)
class LLMResult:
    text: str
    usage: TokenUsage


@dataclass(slots=True)
class LLMCallContext:
    """Request-level metadata attached to an LLM call purely for
    observability. Never sent to the provider API and must never carry API
    keys or raw user content.
    """

    workflow_id: str | None = None
    agent_name: str | None = None
    purpose: str | None = None
    call_number: int | None = None

    def fields(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "agent_name": self.agent_name,
            "purpose": self.purpose,
            "call_number": self.call_number,
        }
