"""
Memory Embeddings Adapter.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.llm import OpenRouterClient
from app.infrastructure.llm.openrouter import get_openrouter_provider


def embed_memory_text(text: str, provider=None) -> list[float]:
    if not text.strip():
        return []
    llm = provider or get_openrouter_provider()
    try:
        return llm.embed_text(text, model=settings.embedding_model)
    except LLMError:
        return []
