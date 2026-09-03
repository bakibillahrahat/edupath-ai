from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_orchestration.models import AgentExecution, AgentMessage, WorkflowExecution


class WorkflowRepository:
    def summarize_token_usage(self, agent_results: list[Any]) -> dict[str, float | int]:
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        estimated_cost = 0.0
        for result in agent_results:
            usage = getattr(result, "token_usage", {}) or {}
            input_tokens += int(usage.get("input_tokens", 0) or 0)
            output_tokens += int(usage.get("output_tokens", 0) or 0)
            total_tokens += int(usage.get("total_tokens", 0) or 0)
            estimated_cost += float(getattr(result, "estimated_cost_usd", 0.0) or 0.0)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
        }

    def summarize_cost(self, agent_results: list[Any]) -> float:
        return float(self.summarize_token_usage(agent_results)["estimated_cost_usd"])

    async def create_workflow_execution(
        self,
        session: AsyncSession,
        *,
        profile_id: str | None,
        workflow_type: str,
        user_request: str,
        started_at: datetime,
    ) -> WorkflowExecution:
        workflow = WorkflowExecution(
            profile_id=profile_id,
            workflow_type=workflow_type,
            status="running",
            started_at=started_at,
            user_request=user_request,
        )
        session.add(workflow)
        await session.flush()
        return workflow

    async def save_workflow_result(
        self,
        session: AsyncSession,
        workflow_id: UUID,
        response,
        *,
        raw_state: dict[str, Any],
        completed_at: datetime | None,
    ) -> None:
        """Persist a workflow's current state. `completed_at=None` means the
        workflow is paused (e.g. awaiting human approval), not finished --
        the caller is expected to call this again once it resumes.

        `raw_state["agent_results"]`/`agent_messages"]` always hold the full
        accumulated history for the run (LangGraph's append reducers never
        drop earlier entries), so this call is idempotent: it replaces this
        workflow's AgentExecution/AgentMessage rows wholesale each time,
        rather than risking duplicate rows across a pause + resume.
        """
        workflow = await session.get(WorkflowExecution, workflow_id)
        if workflow is None:
            return

        workflow.status = response.workflow_status
        workflow.completed_at = completed_at
        workflow.result = response.model_dump(mode="json")
        workflow.token_usage = response.token_usage
        workflow.estimated_cost_usd = response.estimated_cost_usd
        workflow.error = None

        await session.execute(delete(AgentExecution).where(AgentExecution.workflow_id == workflow_id))
        await session.execute(delete(AgentMessage).where(AgentMessage.workflow_id == workflow_id))

        for agent_result in raw_state.get("agent_results", []):
            session.add(
                AgentExecution(
                    workflow_id=workflow_id,
                    agent_name=agent_result.agent_name,
                    status=agent_result.status,
                    started_at=agent_result.started_at,
                    completed_at=agent_result.completed_at,
                    input={"user_request": workflow.user_request, "workflow_type": workflow.workflow_type},
                    output=agent_result.model_dump(mode="json"),
                    token_usage=agent_result.token_usage,
                    estimated_cost=agent_result.estimated_cost_usd,
                    error=None,
                )
            )

        for message in raw_state.get("agent_messages", []):
            session.add(
                AgentMessage(
                    workflow_id=workflow_id,
                    sender=message.sender,
                    receiver=message.receiver,
                    message_type=message.message_type,
                    content=message.content,
                    timestamp=message.timestamp,
                )
            )

        await session.commit()

    async def fail_workflow_execution(
        self,
        session: AsyncSession,
        workflow_id: UUID,
        error: str,
        *,
        completed_at: datetime,
    ) -> None:
        workflow = await session.get(WorkflowExecution, workflow_id)
        if workflow is None:
            return
        workflow.status = "failed"
        workflow.completed_at = completed_at
        workflow.error = error
        await session.commit()

    async def get_workflow_execution(self, session: AsyncSession, workflow_id: UUID) -> WorkflowExecution | None:
        return await session.get(WorkflowExecution, workflow_id)

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID, limit: int = 50) -> list[WorkflowExecution]:
        result = await session.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.profile_id == profile_id)
            .order_by(desc(WorkflowExecution.started_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_workflow_status(self, session: AsyncSession, workflow_id: UUID, status: str) -> WorkflowExecution | None:
        workflow = await session.get(WorkflowExecution, workflow_id)
        if workflow is None:
            return None
        workflow.status = status
        if status in {"completed", "rejected", "cancelled"}:
            workflow.completed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(workflow)
        return workflow

    async def list_agent_executions(self, session: AsyncSession, workflow_id: UUID) -> list[AgentExecution]:
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.workflow_id == workflow_id).order_by(AgentExecution.started_at)
        )
        return list(result.scalars().all())

    async def list_agent_messages(self, session: AsyncSession, workflow_id: UUID) -> list[AgentMessage]:
        result = await session.execute(
            select(AgentMessage).where(AgentMessage.workflow_id == workflow_id).order_by(AgentMessage.timestamp)
        )
        return list(result.scalars().all())

    async def list_workflow_logs(self, session: AsyncSession, workflow_id: UUID) -> list[dict[str, Any]]:
        agent_rows = await self.list_agent_executions(session, workflow_id)
        message_rows = await self.list_agent_messages(session, workflow_id)

        logs: list[dict[str, Any]] = []
        for row in agent_rows:
            logs.append(
                {
                    "event_type": "agent_execution",
                    "agent_name": row.agent_name,
                    "status": row.status,
                    "started_at": row.started_at,
                    "completed_at": row.completed_at,
                    "input": row.input,
                    "output": row.output,
                    "token_usage": row.token_usage,
                    "estimated_cost": row.estimated_cost,
                    "error": row.error,
                }
            )

        for row in message_rows:
            logs.append(
                {
                    "event_type": "agent_message",
                    "sender": row.sender,
                    "receiver": row.receiver,
                    "message_type": row.message_type,
                    "content": row.content,
                    "timestamp": row.timestamp,
                }
            )

        return sorted(logs, key=lambda item: item.get("started_at") or item.get("timestamp"))

CounselingRepository = WorkflowRepository
__all__ = ["WorkflowRepository", "CounselingRepository"]
