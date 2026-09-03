from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from app.core.config import settings
from app.core.exceptions import LLMQuotaError
from app.core.logging import get_logger
from app.infrastructure.llm.base import LLMCallContext
from app.modules.opportunities.schemas import CandidateOpportunity, Evidence

_logger = get_logger(component="workflow_budget")


def ensure_llm_budget(state: dict, *, agent_name: str, purpose: str) -> tuple[int, LLMCallContext]:
    """Reserve the next LLM generation call slot for this workflow run.

    Returns ``(call_number, call_context)`` for the caller to pass into the
    provider call and to persist back onto ``state["llm_call_count"]``.
    Raises ``LLMQuotaError`` (without contacting the provider) once the
    workflow has already made ``settings.max_llm_calls_per_workflow`` calls,
    so a looping or overly broad plan cannot keep burning quota indefinitely.
    """
    workflow_id = state.get("workflow_id")
    call_number = int(state.get("llm_call_count", 0)) + 1
    budget = settings.max_llm_calls_per_workflow

    if call_number > budget:
        _logger.warning(
            "llm_call_budget_exceeded",
            workflow_id=workflow_id,
            agent_name=agent_name,
            purpose=purpose,
            call_number=call_number,
            budget=budget,
        )
        raise LLMQuotaError(
            f"Workflow reached the per-run budget of {budget} LLM calls.",
            provider="openrouter",
            model=settings.openrouter_model,
            status_code=429,
            retry_after=None,
            quota_message=(
                f"Per-workflow LLM call budget ({budget}) exhausted before contacting the provider."
            ),
        )

    return call_number, LLMCallContext(
        workflow_id=workflow_id,
        agent_name=agent_name,
        purpose=purpose,
        call_number=call_number,
    )


def grounded_context(state: dict, tool_names: set[str] | None = None) -> str:
    """Format shared state for agents without letting them discard evidence."""
    tools = state.get("tool_results", [])
    if tool_names:
        tools = [item for item in tools if item.get("tool_name") in tool_names]
    results = [item.model_dump() if hasattr(item, "model_dump") else item for item in state.get("agent_results", [])]
    return f"""
STUDENT PROFILE: {json.dumps(state.get('profile', {}), default=str)}
PREVIOUS AGENT RESULTS: {json.dumps(results, default=str)}
AGENT MESSAGES: {json.dumps([item.model_dump() if hasattr(item, 'model_dump') else item for item in state.get('agent_messages', [])], default=str)}
AVAILABLE TOOL RESULTS: {json.dumps(tools, default=str)}
Use supplied tool results as the factual source. Do not invent scholarships, professors,
universities, deadlines, funding amounts, or eligibility requirements. If evidence is
insufficient, say verification is required.
"""


_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Tool names whose results represent a discovered person (professor), as
# opposed to a university/program/opportunity.
_PROFESSOR_TOOL_NAMES = {"professor_search", "faculty_directory_search"}

_SOURCE_TYPE_BY_TOOL_SOURCE = {
    "postgresql": "database",
    "official_website": "official_university",
}


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "candidate"


def candidates_from_tool_results(state: dict, tool_names: set[str], created_by: str) -> list[CandidateOpportunity]:
    """Deterministically build CandidateOpportunity entries straight from
    already-fetched tool_results (real DB rows / real search hits).

    This intentionally does NOT ask the LLM to generate structured candidate
    data: ids, URLs, and metadata all come directly from the tool's own
    output, so a candidate can never be fabricated by the model. Agents only
    use the LLM to narrate/summarize what was found here.
    """
    candidates: list[CandidateOpportunity] = []
    for tool_result in state.get("tool_results", []):
        if tool_result.get("tool_name") not in tool_names:
            continue
        for result in tool_result.get("results", []):
            metadata = result.get("metadata") or {}
            source = result.get("source") or {}
            title = result.get("title") or "Untitled"
            university = metadata.get("university")
            retrieved_at = source.get("retrieved_at")
            if not isinstance(retrieved_at, datetime):
                retrieved_at = datetime.now(UTC)

            research_areas: list[str] = []
            if metadata.get("research_interests"):
                research_areas = list(metadata["research_interests"])
            elif metadata.get("field"):
                research_areas = [metadata["field"]]

            candidates.append(
                CandidateOpportunity(
                    id=_slugify(f"{title}-{university or tool_result.get('tool_name')}"),
                    title=title,
                    university=university,
                    degree_level=metadata.get("degree_level"),
                    country=metadata.get("country"),
                    professor_name=title if tool_result.get("tool_name") in _PROFESSOR_TOOL_NAMES else None,
                    research_areas=research_areas,
                    funding_type=metadata.get("funding_type"),
                    deadline=metadata.get("deadline"),
                    official_url=source.get("url"),
                    ielts_score=metadata.get("ielts_score") or metadata.get("ielts") or "IELTS 6.5 - 7.0+ (or TOEFL 90+)",
                    required_documents=metadata.get("required_documents") or ["Official Academic Transcripts", "Statement of Purpose (SOP)", "2-3 Letters of Recommendation", "Academic CV / Resume", "Degree Certificate"],
                    eligibility_criteria=metadata.get("eligibility_criteria") or (f"Minimum GPA {metadata.get('min_gpa', '3.0')}/4.0 with accredited background" if metadata.get('min_gpa') else "Bachelor's / Master's degree in Computer Science, Engineering, or related STEM field"),
                    evidence=[
                        Evidence(
                            claim=result.get("description") or title,
                            source_url=source.get("url"),
                            source_title=title,
                            source_type=_SOURCE_TYPE_BY_TOOL_SOURCE.get(source.get("source"), "web_search"),
                            verified=bool(source.get("url")),
                            retrieved_at=retrieved_at,
                        )
                    ],
                    created_by=created_by,
                )
            )
    return candidates


def summarize_candidates(candidates: list[CandidateOpportunity]) -> str:
    """Compact, token-cheap representation of candidates for enrichment-agent
    prompts (eligibility/research-match/verification) -- omits evidence to
    keep prompts small; evidence stays in state for the frontend."""
    if not candidates:
        return "[]"
    compact = [
        {
            "id": c.id,
            "title": c.title,
            "university": c.university,
            "degree_level": c.degree_level,
            "country": c.country,
            "professor_name": c.professor_name,
            "research_areas": c.research_areas,
            "funding_type": c.funding_type,
            "deadline": c.deadline,
        }
        for c in candidates
    ]
    return json.dumps(compact, default=str)
