from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user_optional
from app.database.models.entities import User
from app.database.session import get_db
from app.schemas.counseling import CounselingAnalyzeRequest, CounselingAnalyzeResponse
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/counseling", tags=["counseling"])


def get_workflow_service() -> WorkflowService:
    return WorkflowService()


@router.post("/analyze", response_model=CounselingAnalyzeResponse)
async def analyze_counseling(
    request: CounselingAnalyzeRequest,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
    current_user: User | None = Depends(get_current_user_optional),
) -> CounselingAnalyzeResponse:
    """Thin entrypoint that preserves the existing workflow engine while
    exposing the counseling-style API contract expected by the frontend."""
    result = await service.execute(session, request)
    return CounselingAnalyzeResponse(
        workflow_id=str(result.workflow_id),
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
        message="Counseling analysis started successfully.",
        status="running" if result.workflow_status in {"running", "awaiting_approval"} else "completed",
    )


@router.get("/{session_id}")
async def get_counseling_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    result = await service.get_workflow_result(session, session_id)
    if result is not None:
        return result
    workflow = await service.get_workflow(session, session_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Counseling session not found")
    return workflow.model_dump()


@router.get("/{session_id}/trace")
async def get_counseling_trace(
    session_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    workflow = await service.get_workflow(session, session_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Counseling session not found")
    messages = await service.list_messages(session, session_id)
    events = await service.list_logs(session, session_id)
    agents = await service.list_agents(session, session_id)
    return {
        "workflow_id": str(session_id),
        "status": workflow.status,
        "messages": [m.model_dump(mode="json") for m in messages],
        "events": events,
        "agents": [a.model_dump(mode="json") for a in agents],
    }


@router.get("/{session_id}/graph")
async def get_counseling_graph(
    session_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(get_workflow_service),
) -> dict:
    workflow = await service.get_workflow(session, session_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Counseling session not found")
    agents = await service.list_agents(session, session_id)
    completed_agent_names = [a.agent_name for a in agents]
    result = await service.get_workflow_result(session, session_id) or {}
    execution_plan = result.get("execution_plan") or []
    return {
        "workflow_id": str(session_id),
        "graph": [
            "supervisor",
            "profile_agent",
            "university_agent",
            "scholarship_agent",
            "professor_agent",
            "eligibility_agent",
            "research_match_agent",
            "verification_agent",
            "ranking_agent",
            "approval_gate",
            "sop_agent",
        ],
        "execution_plan": execution_plan,
        "completed_agents": completed_agent_names,
        "status": workflow.status,
    }
