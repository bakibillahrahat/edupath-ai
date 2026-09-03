"""
Tracker Domain Exceptions.
"""
from app.core.exceptions import EduPathError


class TrackerError(EduPathError):
    """Base error for application tracker operations."""


class ApplicationNotFoundError(TrackerError):
    """Raised when an application entry cannot be found."""


__all__ = ["TrackerError", "ApplicationNotFoundError"]
