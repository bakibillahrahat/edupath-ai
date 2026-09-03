"""
Documents & SOP Domain Schemas.
"""
from __future__ import annotations

from app.schemas.document import DocumentRead, DocumentType
from app.schemas.sop import SOPGenerateRequest, SOPRead, SOPResponse, SOPReviseRequest

__all__ = [
    "DocumentRead",
    "DocumentType",
    "SOPGenerateRequest",
    "SOPReviseRequest",
    "SOPResponse",
    "SOPRead",
]
