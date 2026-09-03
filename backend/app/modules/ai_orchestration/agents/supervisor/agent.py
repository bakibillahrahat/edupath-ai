from __future__ import annotations

import json

from app.modules.ai_orchestration.agents.context import ensure_llm_budget
from app.core.exceptions import LLMError, LLMQuotaError
from app.modules.ai_orchestration.graph.routing import (
    ALL_AGENTS,
    build_execution_plan,
    ensure_approval_gate,
    synthesize_final_response,
)
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.modules.ai_orchestration.schemas import AgentMessage, SupervisorDecision


def _dump(value):
    return value.model_dump() if hasattr(value, "model_dump") else value


def build_supervisor_agent(provider=None):
    """The graph's supervisor implementation."""
    provider = provider or get_openrouter_provider()

    def supervisor_agent(state: dict) -> dict:
        request = state.get("user_request") or state.get("user_input", "")
        existing_plan = list(state.get("execution_plan") or [])
        completed = [_dump(item) for item in state.get("agent_results", [])]
        plan_index = int(state.get("plan_index", 0))
        call_count = int(state.get("llm_call_count", 0))

        human_approval = state.get("human_approval") or {}
        if human_approval.get("decision") == "reject":
            # approval_gate paused, the human declined -- end here rather
            # than continuing on to sop_agent with an opportunity nobody
            # approved.
            return {
                **_complete(existing_plan, completed),
                "workflow_status": "completed",
                "approval_status": "rejected",
                "current_task": "Human rejected the proposed opportunity; workflow ended without SOP generation.",
                "llm_call_count": call_count,
            }

        if existing_plan and plan_index >= len(existing_plan):
            return {**_complete(existing_plan, completed), "llm_call_count": call_count}

        errors = state.get("errors", [])

        if existing_plan:
            # The plan was already decided on the first supervisor turn. Reuse
            # it instead of re-deriving the same plan on every step, which would
            # burn unnecessary LLM quota.
            plan = existing_plan
            reason = f"Continuing the existing plan at step {plan_index + 1}/{len(plan)}."
        else:
            prompt = f"""You are the EduPath AI supervisor. Decide the execution plan for a student workflow.
Use only these valid agents: {sorted(ALL_AGENTS)}. Return JSON matching SupervisorDecision.
Typical order when relevant: profile_agent first; then discovery agents
(university_agent, professor_agent, scholarship_agent) in any order; then
eligibility_agent; then research_match_agent; then verification_agent; then
ranking_agent; sop_agent (if requested) always last, since it should use the
final ranked/verified candidates. Skip irrelevant agents for this request.
Do not invent opportunities or facts.
USER REQUEST: {request}
STUDENT PROFILE: {json.dumps(state.get('profile', {}), default=str)}
MEMORY: {json.dumps(state.get('memory_references', []), default=str)}"""
            try:
                call_number, call_context = ensure_llm_budget(state, agent_name="supervisor", purpose="plan_workflow")
                decision, _ = provider.generate_structured(
                    prompt, response_model=SupervisorDecision, context=call_context
                )
                profile_ctx = state.get("profile") or {}
                plan = [agent for agent in decision.execution_plan if agent in ALL_AGENTS] or build_execution_plan(request, profile_ctx)
                reason = decision.reason
                call_count = call_number
            except LLMQuotaError:
                # Quota exhaustion must propagate; the safe fallback plan would
                # still trigger every downstream agent and burn the remaining
                # quota. Surface the 429 cleanly instead.
                raise
            except LLMError as exc:
                # Provider failure is visible to callers; this constrained fallback
                # keeps the workflow operable without pretending the model decided.
                profile_ctx = state.get("profile") or {}
                plan = build_execution_plan(request, profile_ctx)
                reason = "Provider unavailable; using safe fallback plan."
                errors = errors + [f"Supervisor provider failure: {exc}"]

            # Applied exactly once, here, when the plan is first established --
            # never on later reuse turns, since plan_index indexes into
            # whatever list ends up stored in state.
            plan = ensure_approval_gate(plan)

        completed_names = {item.get("agent_name") for item in completed}
        index = plan_index
        while index < len(plan) and plan[index] in completed_names:
            index += 1
        if index >= len(plan):
            return {**_complete(plan, completed), "errors": errors, "llm_call_count": call_count}
        next_agent = plan[index]
        return {
            "execution_plan": plan, "plan_index": index + 1, "next_agent": next_agent,
            "workflow_status": "running", "current_task": reason, "errors": errors,
            "llm_call_count": call_count,
            "agent_messages": [AgentMessage(sender="supervisor", receiver=next_agent, message_type="handoff", content=reason)],
        }
    return supervisor_agent


def _complete(plan: list[str], results: list[dict]) -> dict:
    return {
        "execution_plan": plan, "workflow_status": "completed",
        "final_response": synthesize_final_response(results), "next_agent": "__end__",
        "current_task": "Workflow completed.",
        "agent_messages": [AgentMessage(sender="supervisor", receiver="workflow", message_type="completion", content="All planned agents have completed.")],
    }


supervisor_agent = build_supervisor_agent()
