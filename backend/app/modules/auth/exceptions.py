"""
Auth Domain Exceptions.
"""
from app.core.exceptions import AuthDisabledError, AuthenticationError, EduPathError


class AuthError(EduPathError):
    """Base error for authentication operations."""


__all__ = ["AuthError", "AuthenticationError", "AuthDisabledError"]
