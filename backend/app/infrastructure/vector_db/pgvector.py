"""
Infrastructure PGVector Adapter.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.modules.memory.repository import MemoryRepository


class MemoryVectorStore:
    def __init__(self, repository: MemoryRepository | None = None, provider=None) -> None:
        self._repository = repository or MemoryRepository()
        self._provider = provider or get_openrouter_provider()

    async def search_similar(
        self,
        session: AsyncSession,
        *,
        profile_id: UUID | None,
        query_text: str,
        limit: int = 5,
    ) -> list[dict]:
        query_embedding = await self._embed_query(query_text)
        if not query_embedding:
            memories = await self._repository.list_for_profile(session, profile_id) if profile_id else []
            return [self._serialize(memory) for memory in memories[:limit]]

        memories = await self._repository.search_similar(session, query_embedding, profile_id=profile_id, limit=limit)
        return [self._serialize(memory) for memory in memories]

    async def _embed_query(self, query_text: str) -> list[float]:
        if not query_text.strip():
            return []

        try:
            return self._provider.embed_text(query_text, model=settings.embedding_model)
        except LLMError:
            return []

    def _serialize(self, memory) -> dict:
        return {
            "id": str(memory.id),
            "profile_id": str(memory.profile_id) if memory.profile_id else None,
            "memory_type": memory.memory_type,
            "scope": memory.scope,
            "content": memory.content,
            "source": memory.source,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
        }


VectorStore = MemoryVectorStore

__all__ = ["MemoryVectorStore", "VectorStore"]
