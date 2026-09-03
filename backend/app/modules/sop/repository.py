"""
SOP & Documents Domain Repository.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.sop.models import Document, DocumentChunk, SOPDocument


class SOPRepository:
    async def create(self, session: AsyncSession, sop: SOPDocument) -> SOPDocument:
        session.add(sop)
        await session.commit()
        await session.refresh(sop)
        return sop

    async def update(self, session: AsyncSession, sop: SOPDocument) -> SOPDocument:
        await session.commit()
        await session.refresh(sop)
        return sop

    async def get(self, session: AsyncSession, sop_id: UUID) -> SOPDocument | None:
        return await session.get(SOPDocument, sop_id)

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[SOPDocument]:
        result = await session.execute(
            select(SOPDocument).where(SOPDocument.profile_id == profile_id).order_by(SOPDocument.updated_at.desc())
        )
        return list(result.scalars().all())


class DocumentRepository:
    async def create(self, session: AsyncSession, document: Document) -> Document:
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document

    async def get(self, session: AsyncSession, document_id: UUID) -> Document | None:
        result = await session.execute(
            select(Document).where(Document.id == document_id).options(selectinload(Document.chunks))
        )
        return result.scalar_one_or_none()

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[Document]:
        result = await session.execute(
            select(Document)
            .where(Document.profile_id == profile_id)
            .options(selectinload(Document.chunks))
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, document: Document) -> None:
        await session.delete(document)
        await session.commit()

    async def search_similar_chunks(
        self, session: AsyncSession, query_embedding: list[float], *, profile_id: UUID, limit: int = 5
    ) -> list[DocumentChunk]:
        if not query_embedding:
            return []
        result = await session.execute(
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.profile_id == profile_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        return list(result.scalars().all())
