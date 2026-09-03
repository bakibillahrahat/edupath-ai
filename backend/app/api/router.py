"""
Central API Router.
Mounts feature module routers under /api/v1 prefix.
"""
from fastapi import APIRouter

from app.modules.ai_orchestration import router as ai_orchestration_router
from app.modules.auth import router as auth_router
from app.modules.memory import router as memory_router
from app.modules.opportunities import router as opportunities_router
from app.modules.profiles import router as profiles_router
from app.modules.sop import router as sop_router
from app.modules.tracker import router as tracker_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(profiles_router)
api_router.include_router(opportunities_router)
api_router.include_router(sop_router)
api_router.include_router(memory_router)
api_router.include_router(ai_orchestration_router)
api_router.include_router(tracker_router)
