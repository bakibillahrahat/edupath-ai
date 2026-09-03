from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.sop.models import SOPDocument
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.modules.sop.repository import SOPRepository
from app.modules.sop.document_service import DocumentService
from app.modules.sop.schemas import SOPGenerateRequest, SOPResponse, SOPReviseRequest


def _to_response(sop: SOPDocument) -> SOPResponse:
    return SOPResponse(
        sop_id=str(sop.id),
        title=sop.title or "Untitled SOP",
        content=sop.content or "",
        status=sop.status,
        draft_version=sop.draft_version,
        created_at=sop.created_at,
        updated_at=sop.updated_at,
    )


class SOPService:
    def __init__(self, repository: SOPRepository | None = None, provider=None, document_service: DocumentService | None = None) -> None:
        self._repository = repository or SOPRepository()
        self._provider = provider or get_openrouter_provider()
        # DocumentService uses the LLM only for embed_text (RAG chunking),
        # which now goes through OpenRouter as well -- it must NOT reuse
        # self._provider if the provider instance is generation-only.
        self._document_service = document_service or DocumentService()

    async def generate(self, session: AsyncSession, request: SOPGenerateRequest) -> SOPResponse:
        base_request = request.prompt or (
            f"Draft a statement of purpose targeting "
            f"{request.target_program or 'the target program'} at {request.target_university or 'the target university'}."
        )

        document_context = ""
        try:
            chunks = await self._document_service.retrieve_relevant_chunks(
                session, UUID(request.profile_id), base_request, limit=5
            )
        except ValueError:
            chunks = []  # malformed profile_id -- let the FK/DB layer surface that error normally
        if chunks:
            document_context = "\n\nRelevant excerpts from the student's uploaded documents (CV, transcript, etc.):\n" + "\n---\n".join(chunks)

        prompt = (
            f"{base_request}"
            f"{document_context}\n\n"
            "Only use information that would realistically come from the student's own profile/documents above -- "
            "never invent specific publications, awards, GPA, or work history not provided."
        )
        result = self._provider.generate(
            prompt,
            model=settings.openrouter_model,
            temperature=settings.openrouter_temperature,
        )

        sop = SOPDocument(
            profile_id=UUID(request.profile_id),
            title=f"SOP Draft - {request.target_program or 'General'}",
            content=result.text,
            draft_version=1,
            status="draft",
        )
        sop = await self._repository.create(session, sop)
        return _to_response(sop)

    async def revise(self, session: AsyncSession, request: SOPReviseRequest) -> SOPResponse | None:
        sop = await self._repository.get(session, UUID(request.sop_id))
        if sop is None:
            return None

        prompt = f"""
You are revising an existing statement of purpose based on feedback.

Current draft:
{sop.content}

Feedback to address:
{request.feedback}

Return the full revised statement of purpose. Only use information already present in the
current draft or feedback -- never invent new publications, awards, GPA, or work history.
"""
        result = self._provider.generate(
            prompt,
            model=settings.openrouter_model,
            temperature=settings.openrouter_temperature,
        )

        sop.content = result.text
        sop.draft_version += 1
        sop.status = "draft"
        sop = await self._repository.update(session, sop)
        return _to_response(sop)

    async def get(self, session: AsyncSession, sop_id: UUID) -> SOPResponse | None:
        sop = await self._repository.get(session, sop_id)
        return _to_response(sop) if sop else None

    async def list_for_profile(self, session: AsyncSession, profile_id: UUID) -> list[SOPResponse]:
        sops = await self._repository.list_for_profile(session, profile_id)
        return [_to_response(sop) for sop in sops]
