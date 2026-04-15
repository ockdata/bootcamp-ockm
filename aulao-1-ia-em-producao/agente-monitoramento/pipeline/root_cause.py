"""Step 5: Root cause analysis using LLM + RAG context."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from config.prompts.registry import format_prompt
from config.settings import get_settings
from observability.logger import get_logger
from observability.metrics import estimate_cost
from schemas.events import ClassifiedEvent
from schemas.llm_responses import ExtractionResult, RootCauseResult
from schemas.observability import LLMCallRecord

if TYPE_CHECKING:
    from observability.tracer import PipelineTracer
    from pipeline.rag import RAGEngine
    from protocols.llm import LLMProvider

log = get_logger(__name__)


async def analyze_root_cause(
    event: ClassifiedEvent,
    extraction: ExtractionResult,
    is_anomaly: bool,
    z_score: float,
    rag_engine: RAGEngine,
    llm: LLMProvider,
    tracer: PipelineTracer,
    *,
    prompt_version: str = "v1",
) -> RootCauseResult:
    """Perform root cause analysis combining LLM reasoning with RAG context."""
    record = LLMCallRecord(step="root_cause", provider=getattr(llm, "provider_name", "unknown"))

    # Build query for RAG
    query = f"{event.service} {event.event_type} {event.severity} {extraction.summary}"
    rag_context = await rag_engine.retrieve_context(query)

    try:
        prompt = format_prompt(
            "root_cause", prompt_version,
            service=event.service,
            event_type=event.event_type,
            severity=event.severity,
            summary=extraction.summary,
            is_anomaly=str(is_anomaly),
            z_score=str(z_score),
            raw_payload=event.raw_payload,
            rag_context=rag_context,
        )

        start = time.perf_counter()
        settings = get_settings()
        result = await llm.generate(
            prompt, RootCauseResult, temperature=0.0, max_tokens=settings.llm_max_tokens,
        )
        latency = (time.perf_counter() - start) * 1000

        record.model_id = getattr(llm, "model_id", "unknown")
        record.latency_ms = round(latency, 2)
        record.input_tokens = len(prompt.split()) * 2
        record.output_tokens = 200
        record.estimated_cost_usd = estimate_cost(record.model_id, record.input_tokens, record.output_tokens)
        record.success = True
        record.parse_success = True

        log.info(
            "root_cause.llm.success",
            event_id=event.event_id,
            root_cause=result.root_cause[:80],
            confidence=result.confidence,
            latency_ms=record.latency_ms,
        )

        tracer.metrics.record(record)
        return result

    except Exception as e:
        log.warning("root_cause.llm.failed", event_id=event.event_id, error=str(e))
        record.success = False
        record.fallback_used = True
        record.error_message = str(e)
        tracer.metrics.record(record)

        return RootCauseResult(
            root_cause=f"Unable to determine root cause (LLM failed: {type(e).__name__})",
            confidence=0.1,
            contributing_factors=["LLM analysis unavailable"],
            recommendations=["Manual investigation required", "Check service logs"],
        )
