"""Tests for workflow-level quota handling and FastAPI 429 responses."""
from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import LLMQuotaError
from app.main import app
from app.modules.ai_orchestration.schemas import WorkflowCreateRequest
from app.modules.ai_orchestration.service import WorkflowService


class _RecordingRepository:
    def __init__(self) -> None:
        self.created = None
        self.failed_error: str | None = None

    async def create_workflow_execution(self, session, *, profile_id, workflow_type, user_request, started_at):
        from uuid import uuid4
        self.created = type("Rec", (), {"id": uuid4()})()
        return self.created

    async def fail_workflow_execution(self, session, workflow_id, error, *, completed_at):
        self.failed_error = error


class _FailingProvider:
    """Provider that raises LLMQuotaError on the first structured call (the supervisor)."""

    def __init__(self) -> None:
        self.calls = 0

    def generate_structured(self, prompt, *, response_model, model=None, temperature=None, system_instruction=None, context=None):
        self.calls += 1
        raise LLMQuotaError(
            "OpenRouter rate limit exhausted for model openrouter/free: Quota exceeded",
            provider="openrouter",
            model="openrouter/free",
            status_code=429,
            retry_after=27,
            quota_message="Quota exceeded",
        )


class _NoOpMemory:
    async def load_context(self, session, profile_id, query_text, limit=5):
        return []


class _NoOpTooling:
    async def build_context(self, session, query):
        return []


@pytest.mark.asyncio
async def test_workflow_propagates_quota_error() -> None:
    """Quota errors from any agent must surface as LLMQuotaError, not be wrapped as WorkflowError."""
    repository = _RecordingRepository()

    class _QuotingGraph:
        def invoke(self, state, config=None):
            raise LLMQuotaError(
                "OpenRouter rate limit exhausted for model openrouter/free: Quota exceeded",
                provider="openrouter",
                model="openrouter/free",
                status_code=429,
                retry_after=27,
                quota_message="Quota exceeded",
            )

    service = WorkflowService(
        repository=repository,
        graph=_QuotingGraph(),
        memory_service=_NoOpMemory(),
        tooling_service=_NoOpTooling(),
    )

    with pytest.raises(LLMQuotaError) as exc_info:
        await service.execute(None, WorkflowCreateRequest(user_request="I want a funded PhD in AI in USA."))

    err = exc_info.value
    assert err.provider == "openrouter"
    assert err.retry_after == 27
    assert repository.failed_error is not None
    assert "OpenRouter rate limit exhausted" in repository.failed_error


def test_fastapi_returns_429_for_quota_error(monkeypatch) -> None:
    """The HTTP layer must map LLMQuotaError to 429 with the requested body shape."""
    from app.modules.ai_orchestration.router import get_workflow_service

    class _QuotingService:
        def __init__(self) -> None:
            self.calls: list[WorkflowCreateRequest] = []

        async def execute(self, session, request: WorkflowCreateRequest):
            self.calls.append(request)
            raise LLMQuotaError(
                "OpenRouter rate limit exhausted for model openrouter/free: Quota exceeded",
                provider="openrouter",
                model="openrouter/free",
                status_code=429,
                retry_after=27,
                quota_message="Quota exceeded",
            )

    service = _QuotingService()
    app.dependency_overrides[get_workflow_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/workflows",
                json={"user_request": "I want a funded PhD in AI in USA.", "workflow_type": "opportunity_discovery"},
            )
    finally:
        app.dependency_overrides.pop(get_workflow_service, None)

    assert response.status_code == 429
    body = response.json()
    assert body["type"] == "LLMQuotaError"
    assert body["provider"] == "openrouter"
    assert body["model"] == "openrouter/free"
    assert body["retry_after"] == 27
    assert "Retry-After" in response.headers
    assert response.headers["Retry-After"] == "27"


def test_supervisor_propagates_quota_error() -> None:
    """The supervisor must not silently absorb quota errors and continue with a fallback plan."""
    from app.modules.ai_orchestration.agents.supervisor.agent import build_supervisor_agent
    from app.core.exceptions import LLMQuotaError

    class _QuotaProvider:
        def generate_structured(self, prompt, *, response_model, model=None, temperature=None, system_instruction=None, context=None):
            raise LLMQuotaError(
                "OpenRouter rate limit exhausted for model openrouter/free: Quota exceeded",
                provider="openrouter",
                model="openrouter/free",
                status_code=429,
                retry_after=27,
                quota_message="Quota exceeded",
            )

    supervisor = build_supervisor_agent(provider=_QuotaProvider())

    with pytest.raises(LLMQuotaError):
        supervisor(
            {
                "user_request": "I want a funded PhD in AI in USA.",
                "user_input": "I want a funded PhD in AI in USA.",
                "execution_plan": [],
                "plan_index": 0,
                "agent_results": [],
                "agent_messages": [],
                "errors": [],
            }
        )


def test_profile_agent_propagates_quota_error() -> None:
    """Profile agent must not silently absorb quota errors."""
    from app.modules.ai_orchestration.agents.profile.agent import build_profile_agent
    from app.core.exceptions import LLMQuotaError

    class _QuotaProvider:
        def generate_structured(self, prompt, *, response_model, model=None, temperature=None, system_instruction=None, context=None):
            raise LLMQuotaError(
                "OpenRouter rate limit exhausted for model openrouter/free: Quota exceeded",
                provider="openrouter",
                model="openrouter/free",
                status_code=429,
                retry_after=27,
                quota_message="Quota exceeded",
            )

    agent = build_profile_agent(provider=_QuotaProvider())
    with pytest.raises(LLMQuotaError):
        agent({"user_request": "I want a funded PhD in AI in USA.", "user_input": "I want a funded PhD in AI in USA."})
