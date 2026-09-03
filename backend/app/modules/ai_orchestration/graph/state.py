from __future__ import annotations

from typing import Annotated, Callable, TypedDict

from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult
from app.modules.opportunities.schemas import (
    CandidateOpportunity,
    EligibilityVerdict,
    RankedOpportunity,
    ResearchMatchVerdict,
    VerificationVerdict,
)


def _append(left, right):
    return left + right


def _entry_key(item, field: str):
    return item.get(field) if isinstance(item, dict) else getattr(item, field)


def _merge_by_key(field: str) -> Callable:
    """Reducer factory: upserts `right` entries into `left` keyed by `field`,
    instead of blindly appending. Used for lists where later graph turns
    should replace/update an earlier entry with the same id rather than
    duplicate it (e.g. a candidate re-discovered on a later turn)."""

    def reducer(left: list, right: list) -> list:
        merged = {_entry_key(item, field): item for item in left}
        for item in right:
            merged[_entry_key(item, field)] = item
        return list(merged.values())

    return reducer


class EduPathState(TypedDict, total=False):
    workflow_id: str
    workflow_type: str
    user_request: str
    student_profile_id: str | None
    current_task: str
    execution_plan: list[str]
    plan_index: int
    next_agent: str
    # Total LLM generation calls made so far in this workflow run,
    # enforced against settings.max_llm_calls_per_workflow.
    llm_call_count: int
    workflow_status: str
    approval_status: str
    profile: dict
    profile_analysis: dict
    agent_results: Annotated[list[AgentResult], _append]
    agent_messages: Annotated[list[AgentMessage], _append]
    memory_references: Annotated[list[dict], _append]
    tool_results: Annotated[list[dict], _append]
    errors: Annotated[list[str], _append]
    scholarship_research: dict
    university_research: dict
    professor_research: dict
    eligibility_review: dict
    sop_review: dict
    verification_report: dict
    final_response: str

    # Structured, per-candidate opportunity data (see
    # app/schemas/opportunity_candidate.py). Discovery agents (university,
    # professor, scholarship) contribute candidates; eligibility/research
    # match/verification agents attach verdicts keyed by opportunity_id;
    # ranking_agent writes the final ordered list once, deterministically.
    candidate_opportunities: Annotated[list[CandidateOpportunity], _merge_by_key("id")]
    eligibility_verdicts: Annotated[list[EligibilityVerdict], _merge_by_key("opportunity_id")]
    research_match_verdicts: Annotated[list[ResearchMatchVerdict], _merge_by_key("opportunity_id")]
    verification_verdicts: Annotated[list[VerificationVerdict], _merge_by_key("opportunity_id")]
    ranked_opportunities: list[RankedOpportunity]

    # Set by the approval_gate node's interrupt() payload once the human
    # responds; consumed by the graph to route approve/reject.
    human_approval: dict
