"""
Shared Kernel Layer.
Contains strictly cross-domain primitives (enums, types, constants).
"""
from app.shared.enums import ApplicationStage, DegreeLevel, WorkflowStatus
from app.shared.types import IDType, JSONDict, UUIDStr

__all__ = [
    "DegreeLevel",
    "WorkflowStatus",
    "ApplicationStage",
    "JSONDict",
    "UUIDStr",
    "IDType",
]
