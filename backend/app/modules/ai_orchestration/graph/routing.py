from __future__ import annotations

from typing import Final


ALL_AGENTS: Final[set[str]] = {
    "profile_agent",
    "professor_agent",
    "university_agent",
    "scholarship_agent",
    "eligibility_agent",
    "research_match_agent",
    "verification_agent",
    "ranking_agent",
    "sop_agent",
}


def route_from_supervisor(state: dict) -> str:
    return state.get("next_agent", "__end__")


def ensure_approval_gate(plan: list[str]) -> list[str]:
    """Deterministically insert the approval_gate node immediately before
    sop_agent, whenever sop_agent is present in the plan.

    This is intentionally NOT left to the LLM's own planning (approval_gate
    is not a member of ALL_AGENTS, so the planner can never select or misplace
    it) -- the human-approval pause before SOP generation must be a
    structural guarantee, not a prompt-following outcome. Must be called
    exactly once, when a plan is first established, since plan_index
    indexes into whatever list is ultimately stored in state.
    """
    if "sop_agent" not in plan:
        return plan
    plan = [agent for agent in plan if agent != "approval_gate"]
    index = plan.index("sop_agent")
    plan.insert(index, "approval_gate")
    return plan


def build_execution_plan(user_request: str, profile: dict | None = None) -> list[str]:
    """
    Build a lightweight deterministic execution plan from the user's request
    and student profile. Tailors required agents based on degree level
    (Undergraduate vs. Masters vs. PhD).
    """
    request = user_request.lower()
    profile = profile or {}
    target_degree = str(profile.get("target_degree") or "").lower()

    plan: list[str] = ["profile_agent"]

    is_undergrad = any(k in target_degree for k in ("undergrad", "bachelor", "bs", "ba")) or (
        any(k in request for k in ("undergraduate", "bachelor", "freshman")) and not any(k in request for k in ("phd", "master", "ms"))
    )

    phd_or_research_request = (
        any(k in target_degree for k in ("phd", "doctorate", "doctoral"))
        or any(
            keyword in request
            for keyword in (
                "phd",
                "doctorate",
                "research",
                "ai",
                "ml",
                "machine learning",
                "supervisor",
                "advisor",
                "professor",
                "faculty",
            )
        )
    ) and not is_undergrad

    # Scholarship / funding search
    if any(
        keyword in request
        for keyword in (
            "scholarship",
            "funded",
            "funding",
            "fully funded",
            "financial aid",
            "stipend",
        )
    ) or profile.get("preferred_funding"):
        plan.extend(["university_agent", "scholarship_agent", "eligibility_agent"])
        if phd_or_research_request:
            plan.append("professor_agent")

    # Professor / supervisor search (PhD / Research focus)
    if not is_undergrad and any(
        keyword in request
        for keyword in (
            "professor",
            "supervisor",
            "advisor",
            "faculty",
            "research group",
            "lab",
        )
    ):
        plan.extend(["professor_agent", "university_agent", "eligibility_agent"])

    # University / program discovery
    if "university_agent" not in plan:
        plan.append("university_agent")

    if phd_or_research_request:
        if "professor_agent" not in plan:
            plan.append("professor_agent")
        if "scholarship_agent" not in plan:
            plan.append("scholarship_agent")
        if "eligibility_agent" not in plan:
            plan.append("eligibility_agent")

    # Research alignment scoring for Masters/PhD
    if "eligibility_agent" in plan and not is_undergrad and "research_match_agent" not in plan:
        plan.append("research_match_agent")

    # SOP generation
    if any(
        keyword in request
        for keyword in (
            "sop",
            "statement of purpose",
            "personal statement",
            "essay",
        )
    ) or phd_or_research_request:
        plan.append("sop_agent")

    # Verification and ranking happen after research-oriented agents, and
    # before the plan reaches sop_agent (moved to the end below).
    if len(plan) > 1:
        plan.append("verification_agent")
        plan.append("ranking_agent")

    # sop_agent should always be the last step when present, since it's
    # meant to draft guidance using the final ranked/verified candidates.
    if "sop_agent" in plan:
        plan.remove("sop_agent")
        plan.append("sop_agent")

    # Remove duplicates while preserving execution order.
    plan = list(dict.fromkeys(plan))

    return [agent for agent in plan if agent in ALL_AGENTS]


def synthesize_final_response(agent_results: list[dict]) -> str:
    if not agent_results:
        return "No agent results were produced."

    lines = ["EduPath AI workflow summary:"]

    for result in agent_results:
        agent_name = result.get("agent_name", "agent")
        summary = result.get("summary", "")

        if summary:
            lines.append(f"- {agent_name}: {summary}")

    return "\n".join(lines)
