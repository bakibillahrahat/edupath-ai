from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.counseling import router as counseling_router
from app.api.routes.documents import router as documents_router
from app.api.routes.memory import router as memory_router
from app.api.routes.opportunities import router as opportunities_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.sop import router as sop_router
from app.api.routes.workflows import router as workflows_router
from app.modules.tracker.router import router as tracker_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(counseling_router)
api_router.include_router(documents_router)
api_router.include_router(profiles_router)
api_router.include_router(opportunities_router)
api_router.include_router(memory_router)
api_router.include_router(sop_router)
api_router.include_router(workflows_router)
api_router.include_router(tracker_router)

