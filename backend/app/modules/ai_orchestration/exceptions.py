"""
AI Orchestration Domain Exceptions.
"""
from app.core.exceptions import EduPathError, WorkflowError


class WorkflowNotResumableError(WorkflowError):
    """Raised when a workflow run cannot be resumed."""


class AgentExecutionError(EduPathError):
    """Raised when an individual AI agent fails execution."""


__all__ = ["WorkflowError", "WorkflowNotResumableError", "AgentExecutionError"]
