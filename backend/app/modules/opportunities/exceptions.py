"""
Opportunities & Catalog Domain Exceptions.
"""
from app.core.exceptions import EduPathError


class OpportunityError(EduPathError):
    """Base error for opportunity operations."""


class OpportunityNotFoundError(OpportunityError):
    """Raised when an opportunity cannot be found."""
