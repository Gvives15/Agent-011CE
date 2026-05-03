from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float


def compute_cost_usd(*, prompt_tokens: int, completion_tokens: int, pricing: ModelPricing) -> float:
    return (prompt_tokens * pricing.input_usd_per_million_tokens + completion_tokens * pricing.output_usd_per_million_tokens) / 1_000_000.0
