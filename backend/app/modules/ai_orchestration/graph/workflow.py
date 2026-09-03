from langgraph.graph import END, START, StateGraph

from app.modules.ai_orchestration.agents.eligibility.agent import build_eligibility_agent
from app.modules.ai_orchestration.agents.professor.agent import build_professor_agent
from app.modules.ai_orchestration.agents.profile.agent import build_profile_agent
from app.modules.ai_orchestration.agents.ranking.agent import build_ranking_agent
from app.modules.ai_orchestration.agents.research_match.agent import build_research_match_agent
from app.modules.ai_orchestration.agents.scholarship.agent import build_scholarship_agent
from app.modules.ai_orchestration.agents.sop.agent import build_sop_agent
from app.modules.ai_orchestration.agents.supervisor.agent import build_supervisor_agent
from app.modules.ai_orchestration.graph.approval_gate import approval_gate
from app.modules.ai_orchestration.graph.checkpoints import build_checkpointer
from app.modules.ai_orchestration.agents.university.agent import build_university_agent
from app.modules.ai_orchestration.agents.verification.agent import build_verification_agent
from app.modules.ai_orchestration.graph.state import EduPathState


def build_graph(provider=None, checkpointer=None):
    graph = StateGraph(EduPathState)

    graph.add_node("supervisor", build_supervisor_agent(provider))
    graph.add_node("profile_agent", build_profile_agent(provider))
    graph.add_node("professor_agent", build_professor_agent(provider))
    graph.add_node("university_agent", build_university_agent(provider))
    graph.add_node("scholarship_agent", build_scholarship_agent(provider))
    graph.add_node("eligibility_agent", build_eligibility_agent(provider))
    graph.add_node("research_match_agent", build_research_match_agent(provider))
    graph.add_node("verification_agent", build_verification_agent(provider))
    graph.add_node("ranking_agent", build_ranking_agent(provider))
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("sop_agent", build_sop_agent(provider))

    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next_agent", "__end__"),
        {
            "profile_agent": "profile_agent",
            "professor_agent": "professor_agent",
            "university_agent": "university_agent",
            "scholarship_agent": "scholarship_agent",
            "eligibility_agent": "eligibility_agent",
            "research_match_agent": "research_match_agent",
            "verification_agent": "verification_agent",
            "ranking_agent": "ranking_agent",
            "approval_gate": "approval_gate",
            "sop_agent": "sop_agent",
            "__end__": END,
        },
    )

    graph.add_edge("profile_agent", "supervisor")
    graph.add_edge("professor_agent", "supervisor")
    graph.add_edge("university_agent", "supervisor")
    graph.add_edge("scholarship_agent", "supervisor")
    graph.add_edge("eligibility_agent", "supervisor")
    graph.add_edge("research_match_agent", "supervisor")
    graph.add_edge("verification_agent", "supervisor")
    graph.add_edge("ranking_agent", "supervisor")
    graph.add_edge("approval_gate", "supervisor")
    graph.add_edge("sop_agent", "supervisor")

    # Production graphs use the durable-in-process checkpointer, needed for
    # approval_gate's interrupt()/resume to actually work. Test graphs
    # deliberately use injected providers and default to no checkpointer for
    # easy direct invocation; pass checkpointer= explicitly to test
    # interrupt/resume behavior with a fake provider.
    if checkpointer is None:
        checkpointer = build_checkpointer() if provider is None else None
    return graph.compile(checkpointer=checkpointer)
