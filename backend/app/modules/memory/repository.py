"""
Memory Domain Repository.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models import Memory


class MemoryRepository:
    async def create(self, session: AsyncSession, memory: Memory) -> Memory:
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        return memory

    async def upsert(self, session: AsyncSession, memory: Memory) -> Memory:
        existing = await session.scalar(
            select(Memory).where(
                Memory.profile_id == memory.profile_id,
                Memory.memory_type == memory.memory_type,
                Memory.scope == memory.scope,
            )
        )
        if existing is not None:
            existing.content = memory.content
            existing.source = memory.source
            existing.embedding = memory.embedding
            await session.commit()
            await session.refresh(existing)
            return existing
        return await self.create(session, memory)

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[Memory]:
        result = await session.execute(
            select(Memory).where(Memory.profile_id == profile_id).order_by(Memory.created_at.desc())
        )
        return list(result.scalars().all())

    async def search_similar(
        self,
        session: AsyncSession,
        query_embedding: list[float],
        *,
        profile_id: UUID | None = None,
        limit: int = 5,
    ) -> list[Memory]:
        if not query_embedding:
            return []

        stmt = select(Memory)
        if profile_id is not None:
            stmt = stmt.where(Memory.profile_id == profile_id)

        stmt = stmt.order_by(Memory.embedding.cosine_distance(query_embedding)).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
