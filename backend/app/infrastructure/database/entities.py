"""
Central Database Entities Facade.
Re-exports models from their respective domain modules for backward compatibility.
Each domain module owns and defines its own tables.
"""
from __future__ import annotations

from app.modules.auth.models import TimestampMixin, UUIDMixin, User
from app.modules.profiles.models import StudentProfile
from app.modules.opportunities.models import Opportunity, Professor, Program, University
from app.modules.ai_orchestration.models import AgentExecution, AgentMessage, WorkflowExecution
from app.modules.sop.models import Document, DocumentChunk, SOPDocument
from app.modules.tracker.models import Application
from app.modules.memory.models import Memory

__all__ = [
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "StudentProfile",
    "University",
    "Professor",
    "Program",
    "Opportunity",
    "Application",
    "Document",
    "DocumentChunk",
    "SOPDocument",
    "WorkflowExecution",
    "AgentExecution",
    "AgentMessage",
    "Memory",
]
