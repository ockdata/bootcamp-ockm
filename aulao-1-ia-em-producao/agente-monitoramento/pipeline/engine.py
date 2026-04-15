"""Pipeline engine — orchestrates all steps for a batch of events."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from observability.logger import get_logger
from observability.tracer import PipelineTracer
from pipeline.alerter import build_alert, emit_alert
from pipeline.anomaly import AnomalyDetector
from pipeline.classifier import classify_event
from pipeline.extractor import extract_fields
from pipeline.rag import RAGEngine
from pipeline.risk import compute_risk_score
from pipeline.root_cause import analyze_root_cause
from schemas.alerts import Alert
from schemas.events import EnrichedEvent, RawEvent

if TYPE_CHECKING:
    from protocols.alert_sink import AlertSink
    from protocols.llm import LLMProvider

log = get_logger(__name__)


class PipelineEngine:
    """Main pipeline orchestrator.

    Processes events through:
    1. Classification (LLM + fallback)
    2. Extraction (LLM + regex fallback)
    3. Anomaly detection (EWMA + z-score)
    4. RAG retrieval
    5. Root cause analysis (LLM + RAG)
    6. Risk scoring (deterministic)
    7. Alert emission
    """

    def __init__(
        self,
        llm: LLMProvider,
        rag_engine: RAGEngine,
        alert_sinks: list[AlertSink],
        *,
        prompt_version: str = "v1",
        alert_threshold: int = 60,
        anomaly_state_file: str | None = None,
    ) -> None:
        self.llm = llm
        self.rag_engine = rag_engine
        self.alert_sinks = alert_sinks
        self.prompt_version = prompt_version
        self.alert_threshold = alert_threshold
        self.anomaly_detector = AnomalyDetector(state_file=anomaly_state_file)

    async def process_batch(
        self,
        events: list[RawEvent],
        on_event_done: Callable[[], None] | None = None,
    ) -> tuple[list[EnrichedEvent], list[Alert], PipelineTracer]:
        """Process a batch of raw events through the full pipeline.

        Args:
            events: Raw events to process.
            on_event_done: Optional callback invoked after each event finishes.
        """
        tracer = PipelineTracer(prompt_version=self.prompt_version)
        enriched_events: list[EnrichedEvent] = []
        alerts: list[Alert] = []

        log.info(
            "pipeline.batch.start",
            run_id=tracer.run_id,
            batch_size=len(events),
            prompt_version=self.prompt_version,
        )

        for event in events:
            tracer.events_processed += 1

            try:
                enriched, alert = await self._process_single(event, tracer)
                enriched_events.append(enriched)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                log.error(
                    "pipeline.event.error",
                    event_id=event.event_id,
                    error=str(e),
                    run_id=tracer.run_id,
                )

            if on_event_done is not None:
                on_event_done()

        log.info(
            "pipeline.batch.done",
            run_id=tracer.run_id,
            events_processed=tracer.events_processed,
            anomalies=tracer.anomalies_detected,
            alerts=tracer.alerts_emitted,
            **tracer.metrics.summary(),
        )

        # Persist EWMA state for next run
        self.anomaly_detector.save_state()

        return enriched_events, alerts, tracer

    async def _process_single(
        self,
        event: RawEvent,
        tracer: PipelineTracer,
    ) -> tuple[EnrichedEvent, Alert | None]:
        """Process a single event through all pipeline steps."""

        # --- Step 1: Classify ---
        tracer.start_step("classify")
        classified = await classify_event(
            event, self.llm, tracer, prompt_version=self.prompt_version,
        )
        tracer.end_step("classify")

        # --- Step 2: Extract ---
        tracer.start_step("extract")
        extraction = await extract_fields(
            classified, self.llm, tracer, prompt_version=self.prompt_version,
        )
        tracer.end_step("extract")

        # --- Step 3: Anomaly detection ---
        tracer.start_step("anomaly")
        anomaly = self.anomaly_detector.detect(
            service=classified.service,
            event_type=classified.event_type,
            severity=classified.severity,
        )
        if anomaly.is_anomaly:
            tracer.anomalies_detected += 1
        tracer.end_step("anomaly")

        # --- Step 4 + 5: RAG + Root cause ---
        tracer.start_step("root_cause")
        rca = await analyze_root_cause(
            classified, extraction,
            anomaly.is_anomaly, anomaly.z_score,
            self.rag_engine, self.llm, tracer,
            prompt_version=self.prompt_version,
        )
        tracer.end_step("root_cause")

        # --- Step 6: Risk scoring ---
        tracer.start_step("risk")
        risk = compute_risk_score(
            severity=classified.severity,
            event_type=classified.event_type,
            service=classified.service,
            is_anomaly=anomaly.is_anomaly,
            z_score=anomaly.z_score,
            classification_confidence=classified.classification_confidence,
        )
        tracer.end_step("risk")

        # Build enriched event
        enriched = EnrichedEvent.from_classified(
            classified,
            extracted_summary=extraction.summary,
            is_anomaly=anomaly.is_anomaly,
            z_score=anomaly.z_score,
            root_cause=rca.root_cause,
            risk_score=risk.score,
            risk_level=risk.level,
            recommendations=rca.recommendations,
            pipeline_run_id=tracer.run_id,
            prompt_version=self.prompt_version,
        )

        # --- Step 7: Alert (if above threshold) ---
        alert: Alert | None = None
        if risk.score >= self.alert_threshold:
            tracer.start_step("alert")
            alert = build_alert(classified, extraction, rca, risk, tracer.run_id)
            await emit_alert(alert, self.alert_sinks)
            tracer.alerts_emitted += 1
            tracer.end_step("alert")

        return enriched, alert
