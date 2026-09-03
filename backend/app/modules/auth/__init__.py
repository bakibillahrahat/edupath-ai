"""
Auth & Identity Domain Module.
Encapsulates all models, schemas, repositories, services, dependencies, and routes
associated with authentication, OAuth, user identities, and authorization.
"""
from __future__ import annotations

from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_user_optional,
)
from app.modules.auth.models import TimestampMixin, UUIDMixin, User
from app.modules.auth.repository import UserRepository
from app.modules.auth.router import router
from app.modules.auth.schemas import (
    AuthConfigResponse,
    DevLoginRequest,
    TokenResponse,
    UserRead,
)
from app.modules.auth.service import AuthService

__all__ = [
    "router",
    "User",
    "TimestampMixin",
    "UUIDMixin",
    "UserRepository",
    "AuthService",
    "get_current_user",
    "get_current_user_optional",
    "get_auth_service",
    "AuthConfigResponse",
    "UserRead",
    "DevLoginRequest",
    "TokenResponse",
]
