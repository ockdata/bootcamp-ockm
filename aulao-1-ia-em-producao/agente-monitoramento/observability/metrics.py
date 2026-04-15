"""Token counting, cost estimation, and LLM call tracking."""

from __future__ import annotations

from schemas.observability import LLMCallRecord

# Cost per 1M tokens (USD) — approximate as of 2025-02
_COST_TABLE: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-20250414": {"input": 0.80, "output": 4.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "dummy-heuristic-v1": {"input": 0.0, "output": 0.0},
}


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for a given model and token counts."""
    rates = _COST_TABLE.get(model_id, {"input": 3.0, "output": 15.0})
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return round(cost, 6)


class MetricsCollector:
    """Collects LLM call records during a pipeline run."""

    def __init__(self) -> None:
        self.records: list[LLMCallRecord] = []

    def record(self, rec: LLMCallRecord) -> None:
        self.records.append(rec)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(r.estimated_cost_usd for r in self.records), 6)

    @property
    def total_calls(self) -> int:
        return len(self.records)

    @property
    def avg_latency_ms(self) -> float:
        if not self.records:
            return 0.0
        return round(sum(r.latency_ms for r in self.records) / len(self.records), 2)

    @property
    def fallback_rate(self) -> float:
        if not self.records:
            return 0.0
        fallbacks = sum(1 for r in self.records if r.fallback_used)
        return round(fallbacks / len(self.records), 4)

    def summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "avg_latency_ms": self.avg_latency_ms,
            "fallback_rate": self.fallback_rate,
        }
