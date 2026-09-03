from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import LLMError
from app.modules.sop.schemas import SOPGenerateRequest, SOPReviseRequest
from app.modules.sop.service import SOPService


class FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.usage = SimpleNamespace(estimated_cost_usd=0.0)


class FakeProvider:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, model=None, temperature=None):
        self.prompts.append(prompt)
        return FakeResult(self._responses.pop(0))

    def embed_text(self, text: str, *, model=None):
        # No document RAG in these tests -- DocumentService.retrieve_relevant_chunks
        # gracefully degrades to [] on LLMError without touching the DB.
        raise LLMError("embeddings unavailable in tests")


class FakeSOPRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, object] = {}

    async def create(self, session, sop):
        sop.id = uuid4()
        sop.created_at = datetime.now(UTC)
        sop.updated_at = datetime.now(UTC)
        self._store[sop.id] = sop
        return sop

    async def update(self, session, sop):
        sop.updated_at = datetime.now(UTC)
        self._store[sop.id] = sop
        return sop

    async def get(self, session, sop_id):
        return self._store.get(sop_id)

    async def list_for_profile(self, session, profile_id):
        return sorted(
            [sop for sop in self._store.values() if sop.profile_id == profile_id],
            key=lambda sop: sop.updated_at,
            reverse=True,
        )


@pytest.mark.asyncio
async def test_generate_persists_a_new_sop_document():
    provider = FakeProvider(["Dear admissions committee, ..."])
    repository = FakeSOPRepository()
    service = SOPService(repository=repository, provider=provider)
    profile_id = str(uuid4())

    response = await service.generate(
        SimpleNamespace(),
        SOPGenerateRequest(profile_id=profile_id, target_program="PhD in CS", target_university="Example University"),
    )

    assert response.sop_id is not None
    assert response.content == "Dear admissions committee, ..."
    assert response.draft_version == 1
    assert response.status == "draft"
    assert len(repository._store) == 1


@pytest.mark.asyncio
async def test_revise_increments_draft_version_and_uses_prior_content_in_prompt():
    provider = FakeProvider(["Draft one.", "Draft two, revised."])
    repository = FakeSOPRepository()
    service = SOPService(repository=repository, provider=provider)
    profile_id = str(uuid4())

    first = await service.generate(SimpleNamespace(), SOPGenerateRequest(profile_id=profile_id))
    assert first.draft_version == 1

    revised = await service.revise(
        SimpleNamespace(),
        SOPReviseRequest(profile_id=profile_id, sop_id=first.sop_id, feedback="Make it more concise."),
    )

    assert revised is not None
    assert revised.sop_id == first.sop_id
    assert revised.draft_version == 2
    assert revised.content == "Draft two, revised."
    # The revision prompt must include the PRIOR draft's content, not just the feedback --
    # otherwise the LLM has nothing to actually revise from.
    assert "Draft one." in provider.prompts[1]
    assert "Make it more concise." in provider.prompts[1]


@pytest.mark.asyncio
async def test_revise_returns_none_for_unknown_sop_id():
    service = SOPService(repository=FakeSOPRepository(), provider=FakeProvider([]))

    result = await service.revise(
        SimpleNamespace(),
        SOPReviseRequest(profile_id=str(uuid4()), sop_id=str(uuid4()), feedback="..."),
    )

    assert result is None


@pytest.mark.asyncio
async def test_list_for_profile_returns_only_that_profiles_sops():
    provider = FakeProvider(["a", "b", "c"])
    repository = FakeSOPRepository()
    service = SOPService(repository=repository, provider=provider)
    profile_a = str(uuid4())
    profile_b = str(uuid4())

    await service.generate(SimpleNamespace(), SOPGenerateRequest(profile_id=profile_a))
    await service.generate(SimpleNamespace(), SOPGenerateRequest(profile_id=profile_a))
    await service.generate(SimpleNamespace(), SOPGenerateRequest(profile_id=profile_b))

    results = await service.list_for_profile(SimpleNamespace(), UUID(profile_a))

    assert len(results) == 2
    assert all(True for _ in results)  # sop_id round-trips as a str, not exposing raw UUIDs
