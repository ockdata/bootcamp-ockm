"""BigQuery event store — read raw events, write enriched events and LLM call logs."""

from __future__ import annotations

import json
from datetime import datetime

from google.cloud import bigquery

from observability.logger import get_logger
from schemas.events import EnrichedEvent, RawEvent
from schemas.observability import LLMCallRecord

log = get_logger(__name__)


class BigQueryStore:
    """BigQuery-backed event store. Implements EventStore protocol."""

    def __init__(
        self,
        project_id: str,
        dataset: str,
        raw_table: str = "raw_events",
        enriched_table: str = "enriched_events",
        llm_calls_table: str = "llm_calls",
    ) -> None:
        self.project_id = project_id
        self.dataset = dataset
        self.raw_table = f"{project_id}.{dataset}.{raw_table}"
        self.enriched_table = f"{project_id}.{dataset}.{enriched_table}"
        self.llm_calls_table = f"{project_id}.{dataset}.{llm_calls_table}"
        self._client = bigquery.Client(project=project_id)

    async def fetch_unprocessed(self, limit: int = 10) -> list[RawEvent]:
        query = f"""
            SELECT event_id, timestamp, source, service, raw_payload, metadata, processed
            FROM `{self.raw_table}`
            WHERE processed = FALSE
            ORDER BY timestamp ASC
            LIMIT {limit}
        """
        rows = self._client.query(query).result()
        events = []
        for row in rows:
            metadata = row.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}

            events.append(
                RawEvent(
                    event_id=row["event_id"],
                    timestamp=row["timestamp"],
                    source=row["source"],
                    service=row["service"],
                    raw_payload=row["raw_payload"],
                    metadata=metadata,
                    processed=row["processed"],
                )
            )

        log.info("bq.fetch_unprocessed", count=len(events))
        return events

    async def mark_processed(self, event_ids: list[str]) -> None:
        if not event_ids:
            return
        ids_str = ", ".join(f"'{eid}'" for eid in event_ids)
        query = f"""
            UPDATE `{self.raw_table}`
            SET processed = TRUE
            WHERE event_id IN ({ids_str})
        """
        try:
            self._client.query(query).result()
            log.info("bq.mark_processed", count=len(event_ids))
        except Exception as e:
            # BigQuery doesn't allow UPDATE on rows still in the streaming buffer
            # (~30 min after insert). This is expected when seeding + running demo quickly.
            log.warning(
                "bq.mark_processed.skipped",
                count=len(event_ids),
                reason="streaming buffer (retry after ~30min)",
                error=str(e)[:120],
            )

    async def save_enriched(self, events: list[EnrichedEvent]) -> None:
        if not events:
            return

        rows = []
        for e in events:
            rows.append({
                "event_id": e.event_id,
                "event_type": e.event_type,
                "severity": e.severity,
                "classification_confidence": e.classification_confidence,
                "classification_method": e.classification_method,
                "extracted_summary": e.extracted_summary,
                "is_anomaly": e.is_anomaly,
                "z_score": e.z_score,
                "root_cause": e.root_cause,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
                "recommendations": json.dumps(e.recommendations),
                "pipeline_run_id": e.pipeline_run_id,
                "prompt_version": e.prompt_version,
            })

        errors = self._client.insert_rows_json(self.enriched_table, rows)
        if errors:
            log.error("bq.save_enriched.errors", errors=str(errors))
        else:
            log.info("bq.save_enriched", count=len(rows))

    async def save_llm_calls(self, records: list[LLMCallRecord]) -> None:
        if not records:
            return

        rows = []
        for r in records:
            rows.append({
                "call_id": r.call_id,
                "step": r.step,
                "provider": r.provider,
                "model_id": r.model_id,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
                "latency_ms": r.latency_ms,
                "success": r.success,
                "parse_success": r.parse_success,
                "fallback_used": r.fallback_used,
            })

        errors = self._client.insert_rows_json(self.llm_calls_table, rows)
        if errors:
            log.error("bq.save_llm_calls.errors", errors=str(errors))
        else:
            log.info("bq.save_llm_calls", count=len(rows))
