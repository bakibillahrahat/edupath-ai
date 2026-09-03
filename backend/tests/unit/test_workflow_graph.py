from __future__ import annotations

from collections.abc import Callable

from app.modules.ai_orchestration.graph.workflow import build_graph
from app.modules.ai_orchestration.graph.routing import build_execution_plan
from app.modules.ai_orchestration.schemas import AgentMessage, SupervisorDecision, TokenUsage


class FakeResult:
    def __init__(self, text: str, input_tokens: int = 12, output_tokens: int = 24) -> None:
        self.text = text
        self.usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=0.0,
        )


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_structured(self, prompt: str, *, response_model, model=None, temperature=None, system_instruction=None, context=None):
        self.calls.append(response_model.__name__)
        name = response_model.__name__

        if name == "SupervisorDecision":
            # The supervisor prompt embeds the user request; we don't parse it,
            # but build_execution_plan is deterministic and tested elsewhere.
            plan = [
                "profile_agent",
                "professor_agent",
                "university_agent",
                "scholarship_agent",
                "eligibility_agent",
                "sop_agent",
                "verification_agent",
            ]
            return SupervisorDecision(
                next_agent=plan[0],
                reason="Initial planning.",
                execution_plan=plan,
            ), FakeResult(text="supervisor")

        if name == "ProfileAgentOutput":
            payload = {
                "summary": "Student profile indicates CSE, ML focus, and PhD intent.",
                "key_findings": ["CSE background", "AI/ML interest", "fully funded PhD target"],
                "recommended_next_agent": "professor_agent",
                "supervisor_message": "Profile signals are ready for professor matching.",
                "next_agent_message": "Look for AI/ML supervisors.",
                "confidence": 0.91,
            }
        elif name == "ProfessorAgentOutput":
            payload = {
                "summary": "Potential professors should align with AI and ML research.",
                "key_findings": ["Research fit needed", "Prefer USA institutions"],
                "recommended_next_agent": "university_agent",
                "supervisor_message": "Professor shortlist should feed university selection.",
                "next_agent_message": "Map professors to universities.",
                "confidence": 0.86,
            }
        elif name == "UniversityAgentOutput":
            payload = {
                "summary": "Universities with strong AI/ML programs are prioritized.",
                "key_findings": ["Program fit", "Country fit"],
                "recommended_next_agent": "scholarship_agent",
                "supervisor_message": "University selection is ready for funding search.",
                "next_agent_message": "Find funding for these universities.",
                "confidence": 0.84,
            }
        elif name == "ScholarshipAgentOutput":
            payload = {
                "summary": "Funding pathways include fully funded doctoral scholarships.",
                "key_findings": ["Funding required", "Need deadline review"],
                "recommended_next_agent": "eligibility_agent",
                "supervisor_message": "Funding options need eligibility review.",
                "next_agent_message": "Check scholarship criteria.",
                "confidence": 0.88,
            }
        elif name == "EligibilityAgentOutput":
            payload = {
                "summary": "Eligibility appears plausible for funded PhD opportunities.",
                "key_findings": ["GPA looks competitive", "Check publication requirements"],
                "recommended_next_agent": "sop_agent",
                "supervisor_message": "Eligibility checks are ready for SOP support.",
                "next_agent_message": "Improve SOP for applications.",
                "confidence": 0.8,
            }
        elif name == "SOPAgentOutput":
            payload = {
                "summary": "SOP should emphasize AI research and funding fit.",
                "key_findings": ["Need research narrative", "Need motivation clarity"],
                "recommended_next_agent": "verification_agent",
                "supervisor_message": "SOP guidance is ready for verification.",
                "next_agent_message": "Verify overall recommendations.",
                "confidence": 0.83,
            }
        elif name == "VerificationAgentOutput":
            payload = {
                "summary": "Cross-agent reasoning is internally consistent.",
                "key_findings": ["Profile aligns with professor search", "Funding and eligibility are consistent"],
                "recommended_next_agent": "ranking_agent",
                "supervisor_message": "The workflow is verified and ready to close.",
                "next_agent_message": None,
                "confidence": 0.95,
                "evaluations": [],
            }
        elif name == "ResearchMatchAgentOutput":
            payload = {
                "summary": "Research alignment looks strong for AI-focused candidates.",
                "key_findings": ["Interests overlap with candidate research areas"],
                "recommended_next_agent": "verification_agent",
                "supervisor_message": "Research match scoring complete.",
                "next_agent_message": None,
                "confidence": 0.82,
                "evaluations": [],
            }
        else:
            raise AssertionError(f"Unexpected response model: {name}")

        return response_model.model_validate(payload), FakeResult(text=response_model.model_validate(payload).model_dump_json())


def _initial_state() -> dict:
    return {
        "user_request": "I am a CSE student with GPA 3.7 and want a funded PhD in AI in USA.",
        "user_input": "I am a CSE student with GPA 3.7 and want a funded PhD in AI in USA.",
        "workflow_status": "running",
        "approval_status": "not_required",
        "execution_plan": [],
        "plan_index": 0,
        "agent_results": [],
        "agent_messages": [],
        "memory_references": [],
        "tool_results": [],
        "errors": [],
    }


def test_workflow_pauses_at_approval_gate_before_sop_agent():
    """The plan includes sop_agent, so approval_gate must genuinely pause
    execution before it -- with no checkpointer, the graph can still run
    once (degrading gracefully) but cannot be resumed."""
    graph = build_graph(provider=FakeProvider())  # checkpointer=None by default

    result = graph.invoke(_initial_state())

    assert "__interrupt__" in result
    assert result["workflow_status"] == "running"  # not "completed" -- genuinely paused
    ran_agents = [item.agent_name for item in result["agent_results"]]
    assert ran_agents == ["profile_agent", "professor_agent", "university_agent", "scholarship_agent", "eligibility_agent"]
    assert "sop_agent" not in ran_agents
    interrupt_payload = result["__interrupt__"][0].value
    assert interrupt_payload["type"] == "opportunity_approval"


def test_workflow_resumes_through_approval_gate_to_completion():
    """With a real checkpointer, approve resumes the SAME paused run and it
    completes through sop_agent and verification_agent."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    checkpointer = MemorySaver()
    graph = build_graph(provider=FakeProvider(), checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "resume-test-thread"}}

    paused = graph.invoke(_initial_state(), config)
    assert "__interrupt__" in paused
    assert paused["workflow_status"] == "running"

    result = graph.invoke(Command(resume={"decision": "approve", "opportunity_id": None}), config)

    assert "__interrupt__" not in result
    assert result["workflow_status"] == "completed"
    assert result["next_agent"] == "__end__"
    assert result["approval_status"] == "approved"
    ran_agents = [item.agent_name for item in result["agent_results"]]
    assert ran_agents == [
        "profile_agent", "professor_agent", "university_agent", "scholarship_agent",
        "eligibility_agent", "sop_agent", "verification_agent",
    ]
    assert any(message.sender == "approval_gate" for message in result["agent_messages"])


def test_workflow_rejection_ends_without_sop_agent():
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    checkpointer = MemorySaver()
    graph = build_graph(provider=FakeProvider(), checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "reject-test-thread"}}

    graph.invoke(_initial_state(), config)
    result = graph.invoke(Command(resume={"decision": "reject", "opportunity_id": None}), config)

    assert result["workflow_status"] == "completed"
    assert result["approval_status"] == "rejected"
    ran_agents = [item.agent_name for item in result["agent_results"]]
    assert "sop_agent" not in ran_agents
    assert "verification_agent" not in ran_agents


def test_workflow_runs_through_research_match_and_ranking_agents():
    graph = build_graph(provider=FakeProvider())

    result = graph.invoke(
        {
            "user_request": "I am a CSE student with GPA 3.7 and want a funded PhD in AI in USA.",
            "user_input": "I am a CSE student with GPA 3.7 and want a funded PhD in AI in USA.",
            "workflow_status": "running",
            "approval_status": "not_required",
            "execution_plan": [
                "profile_agent",
                "university_agent",
                "eligibility_agent",
                "research_match_agent",
                "verification_agent",
                "ranking_agent",
            ],
            "plan_index": 0,
            "agent_results": [],
            "agent_messages": [],
            "memory_references": [],
            "tool_results": [],
            "errors": [],
        }
    )

    assert result["workflow_status"] == "completed"
    assert [item.agent_name for item in result["agent_results"]] == [
        "profile_agent",
        "university_agent",
        "eligibility_agent",
        "research_match_agent",
        "verification_agent",
        "ranking_agent",
    ]
    # No tool_results were seeded, so there are no real candidates to rank --
    # the ranking agent must handle that honestly (empty list) rather than
    # fabricating an opportunity out of nowhere.
    assert result["ranked_opportunities"] == []
    assert any(message.sender == "ranking_agent" for message in result["agent_messages"])


from app.modules.ai_orchestration.agents.profile.agent import build_profile_agent, ProfileAgentOutput

def test_profile_agent_unit():
    """Tests the profile agent in isolation."""
    # Arrange
    provider = FakeProvider()
    profile_agent = build_profile_agent(provider=provider)
    initial_state = {
        "user_request": "I want a funded PhD in AI.",
        "agent_results": [],
        "agent_messages": [],
    }

    # Act
    result_state = profile_agent(initial_state)

    # Assert
    assert "profile" in result_state
    assert len(result_state["agent_results"]) == 1
    
    agent_result = result_state["agent_results"][0]
    assert agent_result.agent_name == "profile_agent"
    assert agent_result.summary == "Student profile indicates CSE, ML focus, and PhD intent."
    
    profile_output = ProfileAgentOutput.model_validate(result_state["profile"])
    assert profile_output.summary == "Student profile indicates CSE, ML focus, and PhD intent."
    assert profile_output.recommended_next_agent == "professor_agent"
    
    assert len(result_state["agent_messages"]) == 1
    agent_message = result_state["agent_messages"][0]
    assert agent_message.sender == "profile_agent"
    assert agent_message.receiver == "supervisor"


def test_undergraduate_workflow_plan_excludes_professor_agent():
    plan = build_execution_plan("I want admission in Computer Science bachelor program in USA with scholarships", profile={"target_degree": "Bachelor"})
    assert "professor_agent" not in plan
    assert "university_agent" in plan
    assert "scholarship_agent" in plan
    assert "ranking_agent" in plan


def test_phd_workflow_plan_includes_professor_and_research_match():
    plan = build_execution_plan("I want a funded PhD in AI and need to find an advisor", profile={"target_degree": "PhD"})
    assert "professor_agent" in plan
    assert "university_agent" in plan
    assert "research_match_agent" in plan
    assert "ranking_agent" in plan
    assert "sop_agent" in plan


def test_masters_workflow_plan_includes_research_match():
    plan = build_execution_plan("I want an MS in Data Science with funding", profile={"target_degree": "Masters"})
    assert "university_agent" in plan
    assert "scholarship_agent" in plan
    assert "research_match_agent" in plan
