"""
Memory Domain Service.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.modules.memory.long_term import LongTermMemory
from app.modules.memory.models import Memory
from app.modules.memory.repository import MemoryRepository
from app.modules.memory.schemas import MemoryRead


class MemoryService:
    def __init__(self, repository: MemoryRepository | None = None, long_term_memory: LongTermMemory | None = None) -> None:
        self._repository = repository or MemoryRepository()
        self._long_term_memory = long_term_memory or LongTermMemory()

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[MemoryRead]:
        items = await self._repository.list_for_profile(session, profile_id)
        return [MemoryRead.model_validate(item) for item in items]

    async def load_context(self, session: AsyncSession, profile_id: UUID | None, query_text: str, limit: int = 5) -> list[dict]:
        if profile_id is None:
            return []

        return await self._long_term_memory.retrieve_context(
            session,
            profile_id=profile_id,
            query_text=query_text,
            limit=limit,
        )

    async def record_workflow_context(self, session: AsyncSession, profile_id: UUID | None, *, user_request: str, workflow_id: str, profile: dict | None = None) -> dict | None:
        if profile_id is None:
            return None
        content = {"last_request": user_request, "profile_signals": profile or {}, "workflow_id": workflow_id}
        embedding = None
        try:
            embedding = get_openrouter_provider().embed_text(user_request, model=settings.embedding_model)
        except LLMError:
            pass

        current = Memory(
            profile_id=profile_id, memory_type="workflow_preferences", scope="current_preferences",
            content=content, source="workflow", embedding=embedding,
        )
        await self._repository.upsert(session, current)

        history_entry = Memory(
            profile_id=profile_id, memory_type="workflow_history", scope=workflow_id,
            content=content, source="workflow", embedding=embedding,
        )
        saved = await self._repository.create(session, history_entry)
        return {"id": str(saved.id), "memory_type": saved.memory_type, "scope": saved.scope}

__all__ = ["MemoryService", "get_openrouter_provider", "LLMError"]
