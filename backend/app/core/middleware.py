"""
Core Application Middleware & Exception Handlers.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    AuthDisabledError,
    AuthenticationError,
    EduPathError,
    LLMError,
    LLMQuotaError,
    ToolError,
    WorkflowError,
)
from app.core.logging import get_logger

logger = get_logger(component="api")


def setup_cors(app: FastAPI) -> None:
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EduPathError)
    async def edupath_error_handler(request: Request, exc: EduPathError) -> JSONResponse:
        if isinstance(exc, LLMQuotaError):
            retry_after = int(exc.retry_after) if exc.retry_after else 30
            logger.warning(
                "llm_quota_exhausted",
                path=request.url.path,
                provider=exc.provider,
                model=exc.model,
                retry_after=retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "AI service quota temporarily exhausted. Please try again later.",
                    "type": exc.__class__.__name__,
                    "provider": exc.provider,
                    "model": exc.model,
                    "status_code": exc.status_code or 429,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        if isinstance(exc, AuthenticationError):
            return JSONResponse(status_code=401, content={"detail": str(exc), "type": exc.__class__.__name__})
        if isinstance(exc, AuthDisabledError):
            return JSONResponse(status_code=403, content={"detail": str(exc), "type": exc.__class__.__name__})
        if isinstance(exc, (LLMError, ToolError)):
            logger.warning("external_dependency_failure", path=request.url.path, error_type=exc.__class__.__name__)
            return JSONResponse(status_code=503, content={"detail": "An external service is currently unavailable", "type": exc.__class__.__name__})
        if isinstance(exc, WorkflowError):
            logger.exception("workflow_failure", path=request.url.path, error_type=exc.__class__.__name__)
            return JSONResponse(status_code=500, content={"detail": "Workflow execution failed", "type": exc.__class__.__name__})
        return JSONResponse(status_code=400, content={"detail": str(exc), "type": exc.__class__.__name__})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors(), "type": "ValidationError"})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_request_error", path=request.url.path, error_type=exc.__class__.__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "type": "InternalServerError"})
