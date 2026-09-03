"""
Auth & Identity Route Dependencies.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.infrastructure.database.session import get_db
from app.modules.auth.models import User
from app.modules.auth.service import AuthService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    return AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Required-auth dependency: use on routes that must be logged in."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return await service.get_current_user(session, credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> User | None:
    """Optional-auth dependency: use on routes that work anonymously but
    should personalize/link data when a valid session is present."""
    if credentials is None:
        return None
    try:
        return await service.get_current_user(session, credentials.credentials)
    except AuthenticationError:
        return None
