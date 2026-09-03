"""
Long Term Memory Retriever.
"""
from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.vector_db.pgvector import MemoryVectorStore


class LongTermMemory:
    def __init__(self, vector_store: MemoryVectorStore | None = None) -> None:
        self._vector_store = vector_store or MemoryVectorStore()

    async def retrieve_context(
        self,
        session: AsyncSession,
        *,
        profile_id: UUID | None,
        query_text: str,
        limit: int = 5,
    ) -> list[dict]:
        return await self._vector_store.search_similar(
            session,
            profile_id=profile_id,
            query_text=query_text,
            limit=limit,
        )


__all__ = ["LongTermMemory"]
