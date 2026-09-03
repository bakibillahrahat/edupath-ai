"""
EduPath AI Backend Entrypoint.
Feature-Based Modular Monolith Architecture.
"""
from fastapi import FastAPI

from app.api.router import api_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import setup_cors, setup_exception_handlers

configure_logging(settings.log_level)
logger = get_logger(component="api")

app = FastAPI(
    title="EduPath AI API",
    description="Multi-Agent AI Student Opportunity Assistant",
    version="0.1.0",
)

setup_cors(app)
setup_exception_handlers(app)

app.include_router(health_router)
app.include_router(api_router)
