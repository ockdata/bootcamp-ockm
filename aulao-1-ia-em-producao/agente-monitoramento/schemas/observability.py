"""Observability schemas for LLM calls and pipeline runs."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class LLMCallRecord(BaseModel):
    """Record of a single LLM API call for cost and performance tracking."""

    model_config = ConfigDict(protected_namespaces=())

    call_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    step: str = ""  # "classify", "extract", "root_cause"
    provider: str = ""  # "anthropic", "openai", "dummy"
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    parse_success: bool = True
    fallback_used: bool = False
    error_message: str = ""


class PipelineRunRecord(BaseModel):
    """Summary of a full pipeline run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    events_processed: int = 0
    events_classified: int = 0
    anomalies_detected: int = 0
    alerts_emitted: int = 0
    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    fallback_rate: float = 0.0
    prompt_version: str = ""
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)
