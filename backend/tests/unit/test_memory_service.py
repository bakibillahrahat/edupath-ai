from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest

import app.modules.memory.service as memory_module
from app.modules.memory.service import MemoryService


class _NoEmbeddingProvider:
    """Avoids any real network call in these unit tests -- record_workflow_context
    already handles embedding failures gracefully (embedding stays None)."""

    def embed_text(self, text, model=None):
        raise memory_module.LLMError("embeddings unavailable in tests")


@pytest.fixture(autouse=True)
def _no_real_provider_calls(monkeypatch):
    monkeypatch.setattr(memory_module, "get_openrouter_provider", lambda: _NoEmbeddingProvider())


class FakeMemoryRepository:
    def __init__(self) -> None:
        self.profile_calls: list[UUID] = []
        self.created: list = []
        self.upserted: list = []

    async def list_for_profile(self, session, profile_id):
        self.profile_calls.append(profile_id)
        return [SimpleNamespace(id=UUID("11111111-1111-1111-1111-111111111111"), profile_id=profile_id, memory_type="profile", scope="long_term", content={"note": "remember"}, source="seed", created_at="2026-08-16T00:00:00Z", updated_at="2026-08-16T00:00:00Z")]

    async def create(self, session, memory):
        memory.id = UUID(int=len(self.created) + 1)
        self.created.append(memory)
        return memory

    async def upsert(self, session, memory):
        self.upserted.append(memory)
        memory.id = UUID(int=100)
        return memory


class FakeLongTermMemory:
    async def retrieve_context(self, session, *, profile_id, query_text, limit=5):
        return [{"profile_id": str(profile_id), "query_text": query_text, "limit": limit}]


@pytest.mark.asyncio
async def test_memory_service_loads_context() -> None:
    service = MemoryService(repository=FakeMemoryRepository(), long_term_memory=FakeLongTermMemory())
    result = await service.load_context(SimpleNamespace(), UUID("11111111-1111-1111-1111-111111111111"), "funded phd", limit=3)

    assert result[0]["query_text"] == "funded phd"


@pytest.mark.asyncio
async def test_record_workflow_context_writes_both_current_and_history_rows() -> None:
    """Regression test for the single-row-overwrite bug: every workflow run
    must add a new, never-overwritten history row (scoped by workflow_id),
    in addition to the always-upserted current-preferences row."""
    repository = FakeMemoryRepository()
    service = MemoryService(repository=repository, long_term_memory=FakeLongTermMemory())
    profile_id = UUID("11111111-1111-1111-1111-111111111111")

    await service.record_workflow_context(SimpleNamespace(), profile_id, user_request="first search", workflow_id="wf-1", profile={"gpa": 3.8})
    await service.record_workflow_context(SimpleNamespace(), profile_id, user_request="second search", workflow_id="wf-2", profile={"gpa": 3.8})

    # Two separate history rows accumulated -- neither overwrote the other.
    assert len(repository.created) == 2
    assert [m.scope for m in repository.created] == ["wf-1", "wf-2"]
    assert all(m.memory_type == "workflow_history" for m in repository.created)
    assert repository.created[0].content["last_request"] == "first search"
    assert repository.created[1].content["last_request"] == "second search"

    # The current-preferences row was upserted (called) both times.
    assert len(repository.upserted) == 2
    assert all(m.scope == "current_preferences" for m in repository.upserted)


@pytest.mark.asyncio
async def test_record_workflow_context_noop_without_profile_id() -> None:
    repository = FakeMemoryRepository()
    service = MemoryService(repository=repository, long_term_memory=FakeLongTermMemory())

    result = await service.record_workflow_context(SimpleNamespace(), None, user_request="x", workflow_id="wf-1")

    assert result is None
    assert repository.created == []
    assert repository.upserted == []
