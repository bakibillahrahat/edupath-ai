"""
SOP & Documents Domain Exceptions.
"""
from app.core.exceptions import EduPathError


class SOPError(EduPathError):
    """Base error for SOP operations."""


class SOPGenerationError(SOPError):
    """Raised when SOP drafting or revision fails."""


class DocumentNotFoundError(SOPError):
    """Raised when a document cannot be found."""
