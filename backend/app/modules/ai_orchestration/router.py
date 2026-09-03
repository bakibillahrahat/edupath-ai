"""
AI Orchestration Domain REST Endpoints.
Combines /counseling and /workflows endpoints into the AI Orchestration module.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_optional, get_db
from app.modules.ai_orchestration.export import build_workflow_workbook
from app.modules.ai_orchestration.schemas import (
    ApprovalDecisionRequest,
    CounselingAnalyzeRequest,
    CounselingAnalyzeResponse,
    CounselingChatMessage,
    CounselingChatRequest,
    CounselingChatResponse,
    WorkflowCreateRequest,
    WorkflowExecutionResponse,
    WorkflowLogsResponse,
    WorkflowRead,
)
from app.modules.ai_orchestration.service import WorkflowNotResumableError, WorkflowService
from app.modules.auth.models import User
from app.modules.ai_orchestration.schemas import AgentExecutionRead, AgentMessageRead

counseling_router = APIRouter(prefix="/counseling", tags=["counseling"])
workflows_router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_service() -> WorkflowService:
    return WorkflowService()


get_counseling_service = get_workflow_service


# ---------------------------------------------------------------------------
# Counseling Endpoints
# ---------------------------------------------------------------------------


@counseling_router.post("/analyze", response_model=CounselingAnalyzeResponse)
async def analyze_opportunity(
    request: CounselingAnalyzeRequest,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> CounselingAnalyzeResponse:
    if current_user and current_user.student_profile and not request.student_profile_id:
        request.student_profile_id = str(current_user.student_profile.id)

    workflow_req = WorkflowCreateRequest(
        user_request=request.user_request,
        student_profile_id=request.student_profile_id,
        workflow_type=request.workflow_type,
    )
    result = await service.execute(session, workflow_req)
    return CounselingAnalyzeResponse(
        workflow_id=result.workflow_id,
        workflow_type=result.workflow_type,
        workflow_status=result.workflow_status,
        approval_status=result.approval_status,
        execution_plan=result.execution_plan,
        agent_results=result.agent_results,
        agent_messages=result.agent_messages,
        final_response=result.final_response,
        errors=result.errors,
        started_at=result.started_at,
        completed_at=result.completed_at,
        token_usage=result.token_usage,
        estimated_cost_usd=result.estimated_cost_usd,
        candidate_opportunities=result.candidate_opportunities,
        ranked_opportunities=result.ranked_opportunities,
        pending_approval=result.pending_approval,
        message="Counseling analysis completed." if result.workflow_status == "completed" else "Counseling analysis in progress.",
        status=result.workflow_status,
    )


@counseling_router.post("/chat", response_model=CounselingChatResponse)
async def chat_counseling(
    request: CounselingChatRequest,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> CounselingChatResponse:
    workflow_req = WorkflowCreateRequest(
        user_request=request.message,
        student_profile_id=request.profile_id,
        workflow_type="opportunity_discovery",
    )
    result = await service.execute(session, workflow_req)
    reply = result.final_response or "I analyzed your request, but could not produce a final response."
    suggested = ["Refine search", "View opportunities", "Generate SOP"]
    return CounselingChatResponse(reply=reply, suggested_actions=suggested)


# ---------------------------------------------------------------------------
# Workflow Lifecycle Endpoints
# ---------------------------------------------------------------------------


@workflows_router.post("", response_model=WorkflowExecutionResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowExecutionResponse:
    return await service.execute(session, request)


@workflows_router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowRead]:
    return await service.list_for_profile(session, profile_id)


@workflows_router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    workflow = await service.get_workflow(session, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@workflows_router.post("/{workflow_id}/pause", response_model=WorkflowRead)
async def pause_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    workflow = await service.transition_workflow(session, workflow_id, "paused")
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@workflows_router.post("/{workflow_id}/resume", response_model=WorkflowRead)
async def resume_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    workflow = await service.transition_workflow(session, workflow_id, "running")
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@workflows_router.post("/{workflow_id}/approve", response_model=WorkflowExecutionResponse)
async def approve_workflow(
    workflow_id: UUID,
    request: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowExecutionResponse:
    try:
        return await service.resume(session, workflow_id, decision="approve", opportunity_id=request.opportunity_id)
    except WorkflowNotResumableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@workflows_router.post("/{workflow_id}/reject", response_model=WorkflowExecutionResponse)
async def reject_workflow(
    workflow_id: UUID,
    request: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowExecutionResponse:
    try:
        return await service.resume(session, workflow_id, decision="reject", opportunity_id=request.opportunity_id)
    except WorkflowNotResumableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@workflows_router.post("/{workflow_id}/retry", response_model=WorkflowRead)
async def retry_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowRead:
    workflow = await service.transition_workflow(session, workflow_id, "retrying")
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@workflows_router.get("/{workflow_id}/agents", response_model=list[AgentExecutionRead])
async def get_workflow_agents(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[AgentExecutionRead]:
    return await service.list_agents(session, workflow_id)


@workflows_router.get("/{workflow_id}/messages", response_model=list[AgentMessageRead])
async def get_workflow_messages(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> list[AgentMessageRead]:
    return await service.list_messages(session, workflow_id)


@workflows_router.get("/{workflow_id}/logs", response_model=WorkflowLogsResponse)
async def get_workflow_logs(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowLogsResponse:
    return WorkflowLogsResponse(events=await service.list_logs(session, workflow_id))


@workflows_router.get("/{workflow_id}/export.xlsx")
async def export_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> StreamingResponse:
    result = await service.get_workflow_result(session, workflow_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workbook_bytes = build_workflow_workbook(
        candidate_opportunities=result.get("candidate_opportunities") or [],
        eligibility_verdicts=result.get("eligibility_verdicts") or [],
        research_match_verdicts=result.get("research_match_verdicts") or [],
        ranked_opportunities=result.get("ranked_opportunities") or [],
    )
    return StreamingResponse(
        iter([workbook_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=edupath-workflow-{workflow_id}.xlsx"},
    )


# Combined module router
router = APIRouter()
router.include_router(counseling_router)
router.include_router(workflows_router)

__all__ = [
    "router",
    "counseling_router",
    "workflows_router",
    "create_workflow",
    "get_workflow",
    "get_workflow_service",
    "get_counseling_service",
]
