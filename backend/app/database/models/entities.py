"""
Central Database Entities Facade.
Re-exports models from their respective domain modules for backward compatibility.
Each domain module owns and defines its own tables.
"""
from __future__ import annotations

from app.modules.profile.models import StudentProfile, TimestampMixin, UUIDMixin, User
from app.modules.catalog.models import Opportunity, Professor, Program, University
from app.modules.counseling.models import AgentExecution, AgentMessage, WorkflowExecution
from app.modules.documents.models import Document, DocumentChunk, SOPDocument
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
