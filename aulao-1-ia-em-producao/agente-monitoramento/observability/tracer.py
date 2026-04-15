"""Pipeline tracing — tracks run_id, step timings, and results."""

from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

from observability.logger import get_logger
from observability.metrics import MetricsCollector
from schemas.observability import PipelineRunRecord

log = get_logger(__name__)


class PipelineTracer:
    """Tracks a single pipeline run with timing and metrics."""

    def __init__(self, prompt_version: str = "v1") -> None:
        self.run_id = str(uuid4())
        self.prompt_version = prompt_version
        self.metrics = MetricsCollector()
        self._started_at = datetime.utcnow()
        self._step_start: float | None = None
        self._current_step: str = ""

        self.events_processed = 0
        self.events_classified = 0
        self.anomalies_detected = 0
        self.alerts_emitted = 0

    def start_step(self, step_name: str) -> None:
        self._current_step = step_name
        self._step_start = time.perf_counter()
        log.info("pipeline.step.start", step=step_name, run_id=self.run_id)

    def end_step(self, step_name: str) -> float:
        elapsed = 0.0
        if self._step_start is not None:
            elapsed = (time.perf_counter() - self._step_start) * 1000
        log.info(
            "pipeline.step.end",
            step=step_name,
            run_id=self.run_id,
            latency_ms=round(elapsed, 2),
        )
        self._step_start = None
        return elapsed

    def to_record(self) -> PipelineRunRecord:
        summary = self.metrics.summary()
        return PipelineRunRecord(
            run_id=self.run_id,
            started_at=self._started_at,
            finished_at=datetime.utcnow(),
            events_processed=self.events_processed,
            events_classified=self.events_classified,
            anomalies_detected=self.anomalies_detected,
            alerts_emitted=self.alerts_emitted,
            total_llm_calls=summary["total_calls"],
            total_input_tokens=summary["total_input_tokens"],
            total_output_tokens=summary["total_output_tokens"],
            total_cost_usd=summary["total_cost_usd"],
            avg_latency_ms=summary["avg_latency_ms"],
            fallback_rate=summary["fallback_rate"],
            prompt_version=self.prompt_version,
            llm_calls=list(self.metrics.records),
        )
