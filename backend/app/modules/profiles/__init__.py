"""
Profiles Domain Module.
Encapsulates student profile models, schemas, repository, service, and API router.
"""
from app.modules.profiles.exceptions import (
    ProfileAlreadyExistsError,
    ProfileError,
    ProfileNotFoundError,
)
from app.modules.profiles.models import StudentProfile
from app.modules.profiles.repository import ProfileRepository
from app.modules.profiles.router import router
from app.modules.profiles.schemas import (
    StudentProfileCreate,
    StudentProfileRead,
    StudentProfileUpdate,
)
from app.modules.profiles.service import ProfileService

__all__ = [
    "router",
    "StudentProfile",
    "ProfileRepository",
    "ProfileService",
    "StudentProfileCreate",
    "StudentProfileRead",
    "StudentProfileUpdate",
    "ProfileError",
    "ProfileNotFoundError",
    "ProfileAlreadyExistsError",
]
