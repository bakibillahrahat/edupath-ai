"""
SOP & Documents Domain REST Endpoints.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.modules.sop.document_service import DocumentService, DocumentValidationError
from app.modules.sop.schemas import (
    DocumentRead,
    DocumentType,
    SOPGenerateRequest,
    SOPResponse,
    SOPReviseRequest,
)
from app.modules.sop.service import SOPService

sop_router = APIRouter(prefix="/sop", tags=["sop"])
documents_router = APIRouter(prefix="/documents", tags=["documents"])


def get_sop_service() -> SOPService:
    return SOPService()


def get_document_service() -> DocumentService:
    return DocumentService()


# ---------------------------------------------------------------------------
# SOP Endpoints
# ---------------------------------------------------------------------------


@sop_router.post("/generate", response_model=SOPResponse)
async def generate_sop(
    request: SOPGenerateRequest,
    session: AsyncSession = Depends(get_db),
    service: SOPService = Depends(get_sop_service),
) -> SOPResponse:
    return await service.generate(session, request)


@sop_router.post("/revise", response_model=SOPResponse)
async def revise_sop(
    request: SOPReviseRequest,
    session: AsyncSession = Depends(get_db),
    service: SOPService = Depends(get_sop_service),
) -> SOPResponse:
    response = await service.revise(session, request)
    if response is None:
        raise HTTPException(status_code=404, detail="SOP not found")
    return response


@sop_router.get("/{sop_id}", response_model=SOPResponse)
async def get_sop(
    sop_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: SOPService = Depends(get_sop_service),
) -> SOPResponse:
    response = await service.get(session, sop_id)
    if response is None:
        raise HTTPException(status_code=404, detail="SOP not found")
    return response


@sop_router.get("", response_model=list[SOPResponse])
async def list_sops(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: SOPService = Depends(get_sop_service),
) -> list[SOPResponse]:
    return await service.list_for_profile(session, profile_id)


# ---------------------------------------------------------------------------
# Documents Endpoints
# ---------------------------------------------------------------------------


@documents_router.post("", response_model=DocumentRead)
async def upload_document(
    profile_id: UUID = Form(...),
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    raw = await file.read()
    try:
        return await service.upload(
            session, profile_id=profile_id, filename=file.filename or "upload", document_type=document_type, raw=raw
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@documents_router.get("", response_model=list[DocumentRead])
async def list_documents(
    profile_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentRead]:
    return await service.list_for_profile(session, profile_id)


@documents_router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_db),
    service: DocumentService = Depends(get_document_service),
) -> dict:
    deleted = await service.delete(session, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}


# Combined module router
router = APIRouter()
router.include_router(sop_router)
router.include_router(documents_router)

__all__ = [
    "router",
    "sop_router",
    "documents_router",
    "generate_sop",
    "revise_sop",
    "get_sop",
    "list_sops",
    "upload_document",
    "list_documents",
    "delete_document",
    "get_sop_service",
    "get_document_service",
]
