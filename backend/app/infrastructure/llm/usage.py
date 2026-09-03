"""
LLM Token & Cost Usage Tracking.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    usage_available: bool = False


def serialize_usage(usage: Any) -> dict[str, float | int | bool]:
    """Normalize provider and test-double usage objects for persistence."""
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if is_dataclass(usage):
        return asdict(usage)
    return dict(vars(usage))


_MODEL_PRICING: dict[str, dict[str, float]] = {}


def estimate_cost_usd(model_name: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _MODEL_PRICING.get(model_name)
    if pricing is None:
        return 0.0
    return (input_tokens / 1_000_000 * pricing["input_per_1m"]) + (
        output_tokens / 1_000_000 * pricing["output_per_1m"]
    )


__all__ = ["TokenUsage", "serialize_usage", "estimate_cost_usd"]
