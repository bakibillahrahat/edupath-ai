"""
Opportunities & Admissions Catalog Domain Module.
"""
from app.modules.opportunities.exceptions import (
    OpportunityError,
    OpportunityNotFoundError,
)
from app.modules.opportunities.models import (
    Opportunity,
    Professor,
    Program,
    University,
)
from app.modules.opportunities.repository import (
    CatalogRepository,
    OpportunityRepository,
    ProfessorRepository,
    UniversityRepository,
)
from app.modules.opportunities.router import router
from app.modules.opportunities.schemas import (
    CandidateOpportunity,
    OpportunityRead,
    ProfessorRead,
    ProgramRead,
    RankedOpportunity,
    UniversityRead,
)
from app.modules.opportunities.service import CatalogSyncService, OpportunityService

__all__ = [
    "router",
    "Opportunity",
    "University",
    "Professor",
    "Program",
    "OpportunityRepository",
    "UniversityRepository",
    "ProfessorRepository",
    "CatalogRepository",
    "OpportunityService",
    "CatalogSyncService",
    "OpportunityRead",
    "UniversityRead",
    "ProfessorRead",
    "ProgramRead",
    "CandidateOpportunity",
    "RankedOpportunity",
    "OpportunityError",
    "OpportunityNotFoundError",
]
