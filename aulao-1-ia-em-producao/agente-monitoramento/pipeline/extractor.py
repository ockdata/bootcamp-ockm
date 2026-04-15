"""Step 2: Structured extraction from events with LLM + regex fallback."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from config.prompts.registry import format_prompt
from observability.logger import get_logger
from observability.metrics import estimate_cost
from schemas.events import ClassifiedEvent
from schemas.llm_responses import ExtractionResult
from schemas.observability import LLMCallRecord

if TYPE_CHECKING:
    from observability.tracer import PipelineTracer
    from protocols.llm import LLMProvider

log = get_logger(__name__)


def _regex_extract(event: ClassifiedEvent) -> ExtractionResult:
    """Regex-based fallback extraction."""
    payload = event.raw_payload

    # Try to find error codes
    error_match = re.search(r"(HTTP\s*\d{3}|OOMKilled|TIMEOUT|SIGKILL|ECONNREFUSED)", payload, re.I)
    error_code = error_match.group(0) if error_match else ""

    # Truncate payload for summary
    summary = payload[:200].strip()
    if len(payload) > 200:
        summary += "..."

    return ExtractionResult(
        summary=summary,
        affected_component=event.service,
        error_code=error_code,
        user_impact="Unknown — extracted via regex fallback",
    )


async def extract_fields(
    event: ClassifiedEvent,
    llm: LLMProvider,
    tracer: PipelineTracer,
    *,
    prompt_version: str = "v1",
) -> ExtractionResult:
    """Extract structured fields from a classified event."""
    record = LLMCallRecord(step="extract", provider=getattr(llm, "provider_name", "unknown"))

    try:
        prompt = format_prompt(
            "extract", prompt_version,
            service=event.service,
            event_type=event.event_type,
            severity=event.severity,
            raw_payload=event.raw_payload,
            metadata=str(event.metadata),
        )

        start = time.perf_counter()
        result = await llm.generate(
            prompt, ExtractionResult, temperature=0.0, max_tokens=512,
        )
        latency = (time.perf_counter() - start) * 1000

        record.model_id = getattr(llm, "model_id", "unknown")
        record.latency_ms = round(latency, 2)
        record.input_tokens = len(prompt.split()) * 2
        record.output_tokens = 100
        record.estimated_cost_usd = estimate_cost(record.model_id, record.input_tokens, record.output_tokens)
        record.success = True
        record.parse_success = True

        log.info(
            "extract.llm.success",
            event_id=event.event_id,
            summary=result.summary[:80],
            latency_ms=record.latency_ms,
        )

        tracer.metrics.record(record)
        return result

    except Exception as e:
        log.warning("extract.llm.failed", event_id=event.event_id, error=str(e))
        record.success = False
        record.fallback_used = True
        record.error_message = str(e)
        tracer.metrics.record(record)
        return _regex_extract(event)
