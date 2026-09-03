from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EduPathError, WorkflowError
from app.modules.ai_orchestration.graph.workflow import build_graph
from app.modules.profiles.repository import ProfileRepository
from app.modules.ai_orchestration.repository import WorkflowRepository
from app.modules.profiles.schemas import StudentProfileRead
from app.modules.ai_orchestration.schemas import (
    AgentExecutionRead,
    AgentMessageRead,
    WorkflowCreateRequest,
    WorkflowExecutionResponse,
    WorkflowRead,
)
from app.modules.opportunities.service import CatalogSyncService
from app.modules.memory.service import MemoryService
from app.modules.ai_orchestration.tooling import ToolingService


class WorkflowNotResumableError(Exception):
    """Raised when /approve or /reject is called on a workflow that isn't
    actually paused awaiting a human decision."""


class WorkflowService:
    def __init__(
        self,
        provider=None,
        repository: WorkflowRepository | None = None,
        profile_repository: ProfileRepository | None = None,
        graph=None,
        memory_service: MemoryService | None = None,
        tooling_service: ToolingService | None = None,
        catalog_sync_service: CatalogSyncService | None = None,
    ) -> None:
        self._graph = graph or build_graph(provider=provider)
        self._repository = repository or WorkflowRepository()
        self._profile_repository = profile_repository or ProfileRepository()
        self._memory_service = memory_service or MemoryService()
        self._tooling_service = tooling_service or ToolingService()
        self._catalog_sync_service = catalog_sync_service or CatalogSyncService()

    async def execute(self, session: AsyncSession, request: WorkflowCreateRequest) -> WorkflowExecutionResponse:
        profile_id = UUID(request.student_profile_id) if request.student_profile_id else None
        started_at = datetime.now(UTC)
        workflow = await self._repository.create_workflow_execution(
            session,
            profile_id=profile_id,
            workflow_type=request.workflow_type,
            user_request=request.user_request,
            started_at=started_at,
        )

        memory_references = await self._memory_service.load_context(
            session,
            profile_id,
            request.user_request,
            limit=5,
        )

        tool_results = await self._tooling_service.build_context(session, request.user_request)

        profile_data: dict = {}
        if profile_id is not None and session is not None:
            try:
                profile_record = await self._profile_repository.get(session, profile_id)
                if profile_record is not None:
                    profile_data = StudentProfileRead.model_validate(profile_record).model_dump(mode="json")
            except Exception:
                profile_data = {}

        state = {
            "workflow_id": str(workflow.id),
            "workflow_type": request.workflow_type,
            "user_request": request.user_request,
            "user_input": request.user_request,
            "student_profile_id": request.student_profile_id,
            "profile": profile_data,
            "workflow_status": "running",
            "approval_status": "not_required",
            "execution_plan": [],
            "plan_index": 0,
            "agent_results": [],
            "agent_messages": [],
            "memory_references": memory_references,
            "tool_results": tool_results,
            "errors": [],
        }

        result = await self._invoke_graph(session, workflow.id, state)

        response = await self._persist_result(
            session,
            workflow_id=workflow.id,
            workflow_type=request.workflow_type,
            profile_id=profile_id,
            user_request=request.user_request,
            started_at=started_at,
            result=result,
        )
        return response

    async def resume(
        self,
        session: AsyncSession,
        workflow_id: UUID,
        *,
        decision: Literal["approve", "reject"],
        opportunity_id: str | None = None,
    ) -> WorkflowExecutionResponse:
        """Resumes a workflow genuinely paused at approval_gate's interrupt().

        Calls graph.invoke(Command(resume=...), ...) against the same
        thread_id -- LangGraph continues execution from exactly where it
        paused, using the process-wide cached checkpointer (see
        app/graph/checkpoints.py), not a re-run from scratch.
        """
        workflow = await self._repository.get_workflow_execution(session, workflow_id)
        if workflow is None or workflow.status != "awaiting_approval":
            raise WorkflowNotResumableError(f"Workflow {workflow_id} is not awaiting approval.")

        resume_state = {"decision": decision, "opportunity_id": opportunity_id}
        result = await self._invoke_graph(session, workflow_id, Command(resume=resume_state))

        profile_id = workflow.profile_id
        return await self._persist_result(
            session,
            workflow_id=workflow_id,
            workflow_type=workflow.workflow_type,
            profile_id=profile_id,
            user_request=workflow.user_request,
            started_at=workflow.started_at,
            result=result,
        )

    async def _invoke_graph(self, session: AsyncSession, workflow_id: UUID, graph_input: Any) -> dict:
        config = {"configurable": {"thread_id": str(workflow_id)}}
        try:
            try:
                return await asyncio.to_thread(self._graph.invoke, graph_input, config)
            except TypeError as exc:
                # Lightweight test/deterministic graph adapters may not expose
                # LangGraph's optional config parameter.
                if "positional arguments" not in str(exc):
                    raise
                return await asyncio.to_thread(self._graph.invoke, graph_input)
        except EduPathError as exc:
            # Preserve domain errors (LLMQuotaError, LLMError, ToolError, ...)
            # so the FastAPI exception handler can map them to the correct
            # HTTP status (e.g. 429 for quota exhaustion) instead of the
            # generic 500 WorkflowError.
            await self._repository.fail_workflow_execution(session, workflow_id, str(exc), completed_at=datetime.now(UTC))
            raise
        except Exception as exc:
            await self._repository.fail_workflow_execution(session, workflow_id, str(exc), completed_at=datetime.now(UTC))
            raise WorkflowError(str(exc)) from exc

    async def _persist_result(
        self,
        session: AsyncSession,
        *,
        workflow_id: UUID,
        workflow_type: str,
        profile_id: UUID | None,
        user_request: str,
        started_at: datetime,
        result: dict,
    ) -> WorkflowExecutionResponse:
        interrupts = result.get("__interrupt__")
        is_paused = bool(interrupts)
        completed_at = None if is_paused else datetime.now(UTC)

        response = WorkflowExecutionResponse.model_validate({
            **result,
            "workflow_id": str(workflow_id),
            "workflow_type": workflow_type,
            "workflow_status": "awaiting_approval" if is_paused else result.get("workflow_status", "completed"),
            "pending_approval": interrupts[0].value if is_paused else None,
            "started_at": started_at,
            "completed_at": completed_at,
            "token_usage": self._repository.summarize_token_usage(result.get("agent_results", [])),
            "estimated_cost_usd": self._repository.summarize_cost(result.get("agent_results", [])),
        })

        # Persist discovered candidates into the real catalog tables *before*
        # save_workflow_result's commit, in the same transaction -- so the
        # Catalog/Dashboard reflect what this run found as soon as it's
        # found, whether the run is paused awaiting approval or complete.
        # Approval gates SOP generation, not whether a university "exists".
        candidates = result.get("candidate_opportunities") or []
        if candidates:
            await self._catalog_sync_service.sync_candidates_to_catalog(session, candidates)

        await self._repository.save_workflow_result(session, workflow_id, response, raw_state=result, completed_at=completed_at)

        if not is_paused and hasattr(self._memory_service, "record_workflow_context"):
            await self._memory_service.record_workflow_context(
                session, profile_id, user_request=user_request, workflow_id=str(workflow_id), profile=result.get("profile")
            )
        return response

    async def get_workflow(self, session: AsyncSession, workflow_id: UUID) -> WorkflowRead | None:
        workflow = await self._repository.get_workflow_execution(session, workflow_id)
        return WorkflowRead.model_validate(workflow) if workflow else None

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[WorkflowRead]:
        workflows = await self._repository.list_for_profile(session, profile_id)
        return [WorkflowRead.model_validate(workflow) for workflow in workflows]

    async def get_workflow_result(self, session: AsyncSession, workflow_id: UUID) -> dict | None:
        """The full stored WorkflowExecutionResponse payload (candidates,
        verdicts, ranking, etc.) -- used by the Excel export and any UI that
        needs more than the WorkflowRead summary."""
        workflow = await self._repository.get_workflow_execution(session, workflow_id)
        if workflow is None:
            return None
        return workflow.result

    async def list_agents(self, session: AsyncSession, workflow_id: UUID) -> list[AgentExecutionRead]:
        items = await self._repository.list_agent_executions(session, workflow_id)
        return [AgentExecutionRead.model_validate(item) for item in items]

    async def list_messages(self, session: AsyncSession, workflow_id: UUID) -> list[AgentMessageRead]:
        items = await self._repository.list_agent_messages(session, workflow_id)
        return [AgentMessageRead.model_validate(item) for item in items]

    async def list_logs(self, session: AsyncSession, workflow_id: UUID) -> list[dict[str, Any]]:
        return await self._repository.list_workflow_logs(session, workflow_id)

    async def transition_workflow(self, session: AsyncSession, workflow_id: UUID, status: str) -> WorkflowRead | None:
        workflow = await self._repository.update_workflow_status(session, workflow_id, status)
        return WorkflowRead.model_validate(workflow) if workflow else None
