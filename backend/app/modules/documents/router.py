"""
Documents & SOP Domain REST Endpoints.
"""
from __future__ import annotations

from app.api.routes.documents import router as documents_router
from app.api.routes.sop import router as sop_router

__all__ = ["documents_router", "sop_router"]
