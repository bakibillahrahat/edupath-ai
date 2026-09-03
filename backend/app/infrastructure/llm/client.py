"""
Infrastructure LLM Client Interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.infrastructure.llm.base import LLMCallContext, LLMResult
from app.infrastructure.llm.usage import TokenUsage


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs: Any) -> LLMResult:
        ...


__all__ = ["BaseLLMClient", "LLMResult", "LLMCallContext", "TokenUsage"]
