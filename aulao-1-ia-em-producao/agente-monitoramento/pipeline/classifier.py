"""Step 1: Event classification with 3-layer fallback."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from config.prompts.registry import format_prompt
from observability.logger import get_logger
from observability.metrics import estimate_cost
from schemas.events import ClassifiedEvent, RawEvent
from schemas.llm_responses import ClassificationResult
from schemas.observability import LLMCallRecord

if TYPE_CHECKING:
    from observability.tracer import PipelineTracer
    from protocols.llm import LLMProvider

log = get_logger(__name__)

# Heuristic fallback keywords
_SEVERITY_MAP = {
    "critical": "critical", "fatal": "critical", "OOMKilled": "critical", "panic": "critical",
    "error": "high", "exception": "high", "5xx": "high", "500": "high",
    "warning": "medium", "timeout": "medium", "latency": "medium", "slow": "medium",
}
_TYPE_MAP = {
    "deploy": "deploy", "release": "deploy", "rollback": "deploy",
    "cpu": "metric_alert", "memory": "metric_alert", "p99": "metric_alert",
    "error": "app_error", "exception": "app_error", "traceback": "app_error",
}


def _heuristic_classify(event: RawEvent) -> ClassificationResult:
    text = f"{event.raw_payload} {event.service} {event.source}".lower()
    severity = "low"
    for kw, sev in _SEVERITY_MAP.items():
        if kw.lower() in text:
            severity = sev
            break
    event_type = "log"
    for kw, et in _TYPE_MAP.items():
        if kw.lower() in text:
            event_type = et
            break
    return ClassificationResult(
        event_type=event_type, severity=severity,
        confidence=0.6, reasoning="Heuristic keyword match",
    )


async def classify_event(
    event: RawEvent,
    llm: LLMProvider,
    tracer: PipelineTracer,
    *,
    prompt_version: str = "v1",
) -> ClassifiedEvent:
    """Classify an event using LLM with heuristic fallback."""
    method = "llm"
    fallback_used = False
    result: ClassificationResult | None = None
    record = LLMCallRecord(step="classify", provider=getattr(llm, "provider_name", "unknown"))

    try:
        prompt = format_prompt(
            "classify", prompt_version,
            service=event.service,
            source=event.source,
            raw_payload=event.raw_payload,
            metadata=str(event.metadata),
        )

        start = time.perf_counter()
        result = await llm.generate(
            prompt, ClassificationResult, temperature=0.0, max_tokens=512,
        )
        latency = (time.perf_counter() - start) * 1000

        record.model_id = getattr(llm, "model_id", "unknown")
        record.latency_ms = round(latency, 2)
        record.input_tokens = len(prompt.split()) * 2  # rough estimate for non-real providers
        record.output_tokens = 80
        record.estimated_cost_usd = estimate_cost(record.model_id, record.input_tokens, record.output_tokens)
        record.success = True
        record.parse_success = True

        log.info(
            "classify.llm.success",
            event_id=event.event_id,
            event_type=result.event_type,
            severity=result.severity,
            confidence=result.confidence,
            latency_ms=record.latency_ms,
        )

    except Exception as e:
        log.warning("classify.llm.failed", event_id=event.event_id, error=str(e))
        record.success = False
        record.error_message = str(e)
        fallback_used = True
        method = "heuristic"
        result = _heuristic_classify(event)

    record.fallback_used = fallback_used
    tracer.metrics.record(record)
    tracer.events_classified += 1

    return ClassifiedEvent.from_raw(
        event,
        event_type=result.event_type,
        severity=result.severity,
        classification_confidence=result.confidence,
        classification_method=method,
    )
