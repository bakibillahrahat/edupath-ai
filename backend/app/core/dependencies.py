"""
Core Application Dependencies.
Common cross-cutting dependencies for FastAPI routes.
"""
from __future__ import annotations

from app.infrastructure.database.session import get_db
from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_user_optional,
)

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "get_auth_service",
]
