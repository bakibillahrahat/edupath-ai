from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.modules.ai_orchestration.schemas import WorkflowCreateRequest
from app.modules.ai_orchestration.service import WorkflowNotResumableError, WorkflowService
from app.modules.profiles.service import ProfileService
from app.modules.ai_orchestration.schemas import AgentMessage, AgentResult


@dataclass
class FakeWorkflowRecord:
    id: UUID
    user_request: str
    workflow_type: str
    profile_id: UUID | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "running"


class FakeGraph:
    def __init__(self) -> None:
        self.last_state: dict | None = None

    def invoke(self, state: dict) -> dict:
        self.last_state = state
        return {
            "workflow_status": "completed",
            "execution_plan": ["profile_agent", "verification_agent"],
            "plan_index": 2,
            "next_agent": "__end__",
            "agent_results": [
                AgentResult(
                    agent_name="profile_agent",
                    summary="Profile matched.",
                    supervisor_message="Profile ready.",
                    token_usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                    estimated_cost_usd=0.00001,
                ),
                AgentResult(
                    agent_name="verification_agent",
                    summary="Verified.",
                    supervisor_message="Verified.",
                    token_usage={"input_tokens": 12, "output_tokens": 18, "total_tokens": 30},
                    estimated_cost_usd=0.00002,
                ),
            ],
            "agent_messages": [
                AgentMessage(sender="supervisor", receiver="profile_agent", message_type="handoff", content="start"),
                AgentMessage(sender="verification_agent", receiver="supervisor", message_type="analysis", content="ok"),
            ],
            "final_response": "Done",
            "errors": [],
        }


class FakeRepository:
    def __init__(self) -> None:
        self.created: FakeWorkflowRecord | None = None
        self.saved_response = None
        self.saved_raw_state = None
        self.failed_error: str | None = None

    async def create_workflow_execution(self, session, *, profile_id, workflow_type, user_request, started_at):
        self.created = FakeWorkflowRecord(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            user_request=user_request,
            workflow_type=workflow_type,
        )
        return self.created

    async def save_workflow_result(self, session, workflow_id, response, *, raw_state, completed_at):
        self.saved_response = response
        self.saved_raw_state = raw_state
        self.saved_workflow_id = workflow_id
        if self.created is not None:
            self.created.status = response.workflow_status

    async def fail_workflow_execution(self, session, workflow_id, error, *, completed_at):
        self.failed_error = error

    async def get_workflow_execution(self, session, workflow_id):
        return self.created

    def summarize_token_usage(self, agent_results):
        total_input = sum(int(result.token_usage.get("input_tokens", 0)) for result in agent_results)
        total_output = sum(int(result.token_usage.get("output_tokens", 0)) for result in agent_results)
        total_tokens = sum(int(result.token_usage.get("total_tokens", 0)) for result in agent_results)
        cost = sum(float(result.estimated_cost_usd) for result in agent_results)
        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost,
        }

    def summarize_cost(self, agent_results):
        return float(self.summarize_token_usage(agent_results)["estimated_cost_usd"])


class FakeMemoryService:
    async def load_context(self, session, profile_id, query_text, limit=5):
        return [
            {
                "id": "memory-1",
                "profile_id": str(profile_id) if profile_id else None,
                "memory_type": "profile",
                "scope": "long_term",
                "content": {"note": "prefers funded PhD programs"},
                "source": "test",
            }
        ]


class FakeToolingService:
    async def build_context(self, session, query):
        return [
            {
                "tool_name": "university_search",
                "query": query,
                "results": [{"title": "Test University"}],
            }
        ]


@pytest.mark.asyncio
async def test_workflow_service_persists_execution_and_records() -> None:
    graph = FakeGraph()
    repository = FakeRepository()
    service = WorkflowService(repository=repository, graph=graph, memory_service=FakeMemoryService(), tooling_service=FakeToolingService())
    session = SimpleNamespace()

    response = await service.execute(
        session,
        WorkflowCreateRequest(
            user_request="I am a CSE student with GPA 3.7 and want a funded PhD in AI in USA.",
            student_profile_id=None,
            workflow_type="opportunity_discovery",
        ),
    )

    assert repository.created is not None
    assert repository.saved_workflow_id == repository.created.id
    assert response.workflow_status == "completed"
    assert response.workflow_id == "11111111-1111-1111-1111-111111111111"
    assert response.token_usage["total_tokens"] == 60
    assert len(response.agent_results) == 2
    assert graph.last_state is not None
    assert graph.last_state["workflow_id"] == "11111111-1111-1111-1111-111111111111"
    assert graph.last_state["workflow_type"] == "opportunity_discovery"
    assert graph.last_state["memory_references"]
    assert graph.last_state["tool_results"]


class FakeInterruptingGraph:
    """Simulates approval_gate pausing on the first invoke() and completing
    on a Command(resume=...) invoke() -- mirrors real LangGraph's interrupt
    contract (a __interrupt__ key with .value payloads) without needing a
    real graph/checkpointer in this unit test."""

    def __init__(self) -> None:
        self.calls: list = []

    def invoke(self, graph_input):
        self.calls.append(graph_input)
        is_resume = not isinstance(graph_input, dict)

        base_agent_result = AgentResult(
            agent_name="profile_agent",
            summary="Profile matched.",
            supervisor_message="Profile ready.",
            token_usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            estimated_cost_usd=0.00001,
        )

        if not is_resume:
            return {
                "workflow_status": "running",
                "execution_plan": ["profile_agent", "approval_gate", "sop_agent"],
                "plan_index": 2,
                "next_agent": "approval_gate",
                "agent_results": [base_agent_result],
                "agent_messages": [AgentMessage(sender="supervisor", receiver="profile_agent", message_type="handoff", content="start")],
                "errors": [],
                "candidate_opportunities": [],
                "ranked_opportunities": [],
                "__interrupt__": [SimpleNamespace(value={"type": "opportunity_approval", "ranked_opportunities": []})],
            }

        sop_result = AgentResult(
            agent_name="sop_agent",
            summary="SOP guidance ready.",
            supervisor_message="Done.",
            token_usage={"input_tokens": 5, "output_tokens": 5, "total_tokens": 10},
            estimated_cost_usd=0.000005,
        )
        return {
            "workflow_status": "completed",
            "execution_plan": ["profile_agent", "approval_gate", "sop_agent"],
            "plan_index": 3,
            "next_agent": "__end__",
            "approval_status": "approved",
            "agent_results": [base_agent_result, sop_result],
            "agent_messages": [
                AgentMessage(sender="supervisor", receiver="profile_agent", message_type="handoff", content="start"),
                AgentMessage(sender="approval_gate", receiver="supervisor", message_type="approval", content="Human decision: approve"),
            ],
            "final_response": "Done",
            "errors": [],
            "candidate_opportunities": [],
            "ranked_opportunities": [],
        }


@pytest.mark.asyncio
async def test_workflow_service_execute_detects_interrupt_and_pauses() -> None:
    graph = FakeInterruptingGraph()
    repository = FakeRepository()
    service = WorkflowService(repository=repository, graph=graph, memory_service=FakeMemoryService(), tooling_service=FakeToolingService())
    session = SimpleNamespace()

    response = await service.execute(
        session,
        WorkflowCreateRequest(user_request="I want a funded PhD in AI, and approve my top choice for an SOP.", student_profile_id=None),
    )

    assert response.workflow_status == "awaiting_approval"
    assert response.pending_approval == {"type": "opportunity_approval", "ranked_opportunities": []}
    assert response.completed_at is None
    assert repository.created.status == "awaiting_approval"
    # Only the pre-interrupt agent ran; sop_agent has not executed yet.
    assert [r.agent_name for r in response.agent_results] == ["profile_agent"]


@pytest.mark.asyncio
async def test_workflow_service_resume_completes_paused_workflow() -> None:
    graph = FakeInterruptingGraph()
    repository = FakeRepository()
    service = WorkflowService(repository=repository, graph=graph, memory_service=FakeMemoryService(), tooling_service=FakeToolingService())
    session = SimpleNamespace()

    paused = await service.execute(
        session,
        WorkflowCreateRequest(user_request="I want a funded PhD in AI, and approve my top choice for an SOP.", student_profile_id=None),
    )
    assert paused.workflow_status == "awaiting_approval"

    resumed = await service.resume(session, repository.created.id, decision="approve", opportunity_id="stanford-cs-phd")

    assert resumed.workflow_status == "completed"
    assert resumed.completed_at is not None
    assert resumed.approval_status == "approved"
    assert [r.agent_name for r in resumed.agent_results] == ["profile_agent", "sop_agent"]
    # Command(resume=...) was actually passed through on the second call.
    assert len(graph.calls) == 2
    from langgraph.types import Command
    assert isinstance(graph.calls[1], Command)
    assert graph.calls[1].resume == {"decision": "approve", "opportunity_id": "stanford-cs-phd"}


@pytest.mark.asyncio
async def test_workflow_service_resume_rejects_when_not_awaiting_approval() -> None:
    graph = FakeGraph()
    repository = FakeRepository()
    service = WorkflowService(repository=repository, graph=graph, memory_service=FakeMemoryService(), tooling_service=FakeToolingService())
    session = SimpleNamespace()

    await service.execute(session, WorkflowCreateRequest(user_request="Simple request.", student_profile_id=None))
    assert repository.created.status == "completed"

    with pytest.raises(WorkflowNotResumableError):
        await service.resume(session, repository.created.id, decision="approve", opportunity_id=None)


class FakeGraphWithCandidates(FakeGraph):
    def invoke(self, state: dict) -> dict:
        result = super().invoke(state)
        from app.modules.opportunities.schemas import CandidateOpportunity
        result["candidate_opportunities"] = [
            CandidateOpportunity(id="c1", title="Example PhD", university="Example University", created_by="test")
        ]
        return result


class SpyCatalogSyncService:
    def __init__(self) -> None:
        self.synced_candidates = None

    async def sync_candidates_to_catalog(self, session, candidates):
        self.synced_candidates = list(candidates)


@pytest.mark.asyncio
async def test_workflow_service_syncs_discovered_candidates_into_catalog() -> None:
    """Regression test for the core sync bug: discovered candidates must be
    handed to CatalogSyncService, not left stranded in the workflow-only
    response -- otherwise the Catalog/Dashboard never reflect what a
    discovery run found."""
    graph = FakeGraphWithCandidates()
    repository = FakeRepository()
    catalog_sync = SpyCatalogSyncService()
    service = WorkflowService(
        repository=repository, graph=graph, memory_service=FakeMemoryService(),
        tooling_service=FakeToolingService(), catalog_sync_service=catalog_sync,
    )
    session = SimpleNamespace()

    await service.execute(session, WorkflowCreateRequest(user_request="Find me a PhD.", student_profile_id=None))

    assert catalog_sync.synced_candidates is not None
    assert len(catalog_sync.synced_candidates) == 1
    assert catalog_sync.synced_candidates[0].title == "Example PhD"


@pytest.mark.asyncio
async def test_workflow_service_skips_catalog_sync_when_no_candidates() -> None:
    graph = FakeGraph()  # base FakeGraph returns no candidate_opportunities key
    repository = FakeRepository()
    catalog_sync = SpyCatalogSyncService()
    service = WorkflowService(
        repository=repository, graph=graph, memory_service=FakeMemoryService(),
        tooling_service=FakeToolingService(), catalog_sync_service=catalog_sync,
    )
    session = SimpleNamespace()

    await service.execute(session, WorkflowCreateRequest(user_request="Simple request.", student_profile_id=None))

    assert catalog_sync.synced_candidates is None


def test_counseling_schema_accepts_analysis_payload() -> None:
    from app.modules.ai_orchestration.schemas import CounselingAnalyzeRequest
    from app.modules.ai_orchestration.schemas import CounselingAnalyzeResponse

    payload = CounselingAnalyzeRequest(
        user_request="I want a funded PhD in AI in the USA.",
        student_profile_id="d5f2d2d9-0d0a-4a0a-9ddb-4ac8da94d57a",
    )

    assert payload.user_request == "I want a funded PhD in AI in the USA."
    assert payload.student_profile_id == "d5f2d2d9-0d0a-4a0a-9ddb-4ac8da94d57a"


def test_counseling_response_keeps_full_workflow_payload() -> None:
    from app.modules.ai_orchestration.schemas import CounselingAnalyzeResponse

    result = CounselingAnalyzeResponse(
        workflow_id="wf-123",
        workflow_status="completed",
        workflow_type="opportunity_discovery",
        execution_plan=["profile_agent", "ranking_agent"],
        agent_results=[
            {
                "agent_name": "profile_agent",
                "summary": "Profile matched.",
                "supervisor_message": "Ready.",
            }
        ],
        final_response="Found a strong fit.",
        status="completed",
    )

    assert result.workflow_type == "opportunity_discovery"
    assert result.execution_plan == ["profile_agent", "ranking_agent"]
    assert result.agent_results[0].agent_name == "profile_agent"
    assert result.final_response == "Found a strong fit."


@pytest.mark.asyncio
async def test_profile_service_get_for_user_returns_matching_profile_by_email() -> None:
    profile = SimpleNamespace(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        user_id=UUID("33333333-3333-3333-3333-333333333333"),
        email="student@example.com",
        name="Student Name",
        field_of_study="Computer Science",
    )

    class FakeProfileRepository:
        async def get_by_user_id(self, session, user_id):
            return profile if user_id == profile.user_id else None

        async def get_by_email(self, session, email):
            return profile if email == profile.email else None

    service = ProfileService(repository=FakeProfileRepository())
    result = await service.get_for_user(SimpleNamespace(), UUID("33333333-3333-3333-3333-333333333333"), "student@example.com")

    assert result is not None
    assert result.email == "student@example.com"
    assert result.name == "Student Name"


