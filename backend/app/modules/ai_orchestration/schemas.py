"""
AI Orchestration Domain Schemas.
Fully self-contained schema models for workflows, counseling, agents, and tooling.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.opportunities.schemas import CandidateOpportunity, RankedOpportunity


# ---------------------------------------------------------------------------
# Agent Schemas
# ---------------------------------------------------------------------------


class AgentMessage(BaseModel):
    sender: str
    receiver: str
    message_type: str = "handoff"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentResult(BaseModel):
    agent_name: str
    status: Literal["success", "needs_human_review", "failed"] = "success"
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_next_agent: str | None = None
    supervisor_message: str
    next_agent_message: str | None = None
    confidence: float | None = None
    needs_human_approval: bool = False
    raw_output: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    token_usage: dict[str, float | int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0

    model_config = ConfigDict(extra="forbid")


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class SupervisorDecision(BaseModel):
    next_agent: str
    reason: str
    execution_plan: list[str] = Field(default_factory=list)
    workflow_status: Literal["running", "completed", "awaiting_approval", "failed"] = "running"
    final_response: str | None = None


class WorkflowExecutionSummary(BaseModel):
    workflow_status: str
    execution_plan: list[str]
    agent_results: list[AgentResult]
    agent_messages: list[AgentMessage]
    final_response: str | None = None
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow Schemas
# ---------------------------------------------------------------------------


class WorkflowCreateRequest(BaseModel):
    user_request: str = Field(min_length=1)
    student_profile_id: str | None = None
    workflow_type: str = "opportunity_discovery"


class ApprovalDecisionRequest(BaseModel):
    """Body for POST /workflows/{id}/approve and /reject."""
    opportunity_id: str | None = None


class WorkflowRead(BaseModel):
    id: str
    profile_id: str | None = None
    workflow_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    user_request: str
    token_usage: dict[str, float | int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "profile_id", mode="before")
    @classmethod
    def serialize_ids(cls, value: object) -> str | None:
        return str(value) if value is not None else None


class AgentExecutionRead(BaseModel):
    id: str
    workflow_id: str
    agent_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    token_usage: dict[str, float | int] = Field(default_factory=dict)
    estimated_cost: float = 0.0
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "workflow_id", mode="before")
    @classmethod
    def serialize_ids(cls, value: object) -> str:
        return str(value)


class AgentMessageRead(BaseModel):
    id: str
    workflow_id: str
    sender: str
    receiver: str
    message_type: str
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "workflow_id", mode="before")
    @classmethod
    def serialize_ids(cls, value: object) -> str:
        return str(value)


class WorkflowExecutionResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    workflow_status: str
    approval_status: str = "not_required"
    execution_plan: list[str]
    agent_results: list[AgentResult]
    agent_messages: list[AgentMessage]
    final_response: str | None = None
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    token_usage: dict[str, float | int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    candidate_opportunities: list[CandidateOpportunity] = Field(default_factory=list)
    ranked_opportunities: list[RankedOpportunity] = Field(default_factory=list)
    pending_approval: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowLogsResponse(BaseModel):
    events: list[dict]


# ---------------------------------------------------------------------------
# Tooling Schemas
# ---------------------------------------------------------------------------


class ToolSource(BaseModel):
    source: str
    url: str | None = None
    retrieved_at: datetime
    confidence: float = 0.0


class ToolSearchResult(BaseModel):
    title: str
    description: str | None = None
    source: ToolSource
    metadata: dict = Field(default_factory=dict)


class ToolSearchResponse(BaseModel):
    tool_name: str
    query: str
    results: list[ToolSearchResult] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    tool_status: str = "available"

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Counseling Schemas
# ---------------------------------------------------------------------------


class CounselingAnalyzeRequest(BaseModel):
    user_request: str = Field(min_length=1)
    student_profile_id: str | None = None
    workflow_type: str = "opportunity_discovery"


class CounselingAnalyzeResponse(BaseModel):
    workflow_id: str
    workflow_type: str = "opportunity_discovery"
    workflow_status: str
    approval_status: str = "not_required"
    execution_plan: list[str] = Field(default_factory=list)
    agent_results: list[AgentResult] = Field(default_factory=list)
    agent_messages: list[AgentMessage] = Field(default_factory=list)
    final_response: str | None = None
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    token_usage: dict[str, float | int] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    candidate_opportunities: list[CandidateOpportunity] = Field(default_factory=list)
    ranked_opportunities: list[RankedOpportunity] = Field(default_factory=list)
    pending_approval: dict | None = None
    message: str = "Counseling analysis started successfully."
    status: str = "running"

    model_config = ConfigDict(from_attributes=True)


class CounselingChatMessage(BaseModel):
    role: str
    content: str


class CounselingChatRequest(BaseModel):
    message: str
    profile_id: str | None = None
    history: list[CounselingChatMessage] = Field(default_factory=list)


class CounselingChatResponse(BaseModel):
    reply: str
    suggested_actions: list[str] = Field(default_factory=list)


__all__ = [
    "AgentMessage",
    "AgentResult",
    "TokenUsage",
    "SupervisorDecision",
    "WorkflowExecutionSummary",
    "WorkflowCreateRequest",
    "ApprovalDecisionRequest",
    "WorkflowRead",
    "AgentExecutionRead",
    "AgentMessageRead",
    "WorkflowExecutionResponse",
    "WorkflowLogsResponse",
    "ToolSource",
    "ToolSearchResult",
    "ToolSearchResponse",
    "CounselingAnalyzeRequest",
    "CounselingAnalyzeResponse",
    "CounselingChatMessage",
    "CounselingChatRequest",
    "CounselingChatResponse",
]
