"""
Profile Domain Exceptions.
"""
from app.core.exceptions import EduPathError


class ProfileError(EduPathError):
    """Base error for profile operations."""


class ProfileNotFoundError(ProfileError):
    """Raised when a profile cannot be found."""


class ProfileAlreadyExistsError(ProfileError):
    """Raised when a profile already exists for the given user or email."""
