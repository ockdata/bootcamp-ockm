"""Event schemas flowing through the pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class RawEvent(BaseModel):
    """An unprocessed event ingested from BigQuery or synthetic source."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: Literal["cloud_logging", "application", "deploy"] = "application"
    service: str = "unknown"
    raw_payload: str = ""
    metadata: dict = Field(default_factory=dict)
    processed: bool = False


class ClassifiedEvent(BaseModel):
    """Event after classification step."""

    event_id: str
    timestamp: datetime
    source: str
    service: str
    raw_payload: str
    metadata: dict = Field(default_factory=dict)

    # Classification fields
    event_type: Literal["log", "metric_alert", "app_error", "deploy", "unknown"] = "unknown"
    severity: Literal["low", "medium", "high", "critical"] = "low"
    classification_confidence: float = 0.0
    classification_method: Literal["llm", "heuristic", "fallback"] = "fallback"

    @classmethod
    def from_raw(cls, raw: RawEvent, **kwargs) -> ClassifiedEvent:
        return cls(
            event_id=raw.event_id,
            timestamp=raw.timestamp,
            source=raw.source,
            service=raw.service,
            raw_payload=raw.raw_payload,
            metadata=raw.metadata,
            **kwargs,
        )


class EnrichedEvent(BaseModel):
    """Fully enriched event — final output of the pipeline."""

    event_id: str
    timestamp: datetime
    source: str
    service: str
    raw_payload: str
    metadata: dict = Field(default_factory=dict)

    # Classification
    event_type: str = "unknown"
    severity: str = "low"
    classification_confidence: float = 0.0
    classification_method: str = "fallback"

    # Extraction
    extracted_summary: str = ""

    # Anomaly detection
    is_anomaly: bool = False
    z_score: float = 0.0

    # Root cause
    root_cause: str = ""

    # Risk
    risk_score: int = 0
    risk_level: Literal["low", "medium", "high", "critical"] = "low"

    # Recommendations
    recommendations: list[str] = Field(default_factory=list)

    # Pipeline metadata
    pipeline_run_id: str = ""
    prompt_version: str = ""

    @classmethod
    def from_classified(cls, event: ClassifiedEvent, **kwargs) -> EnrichedEvent:
        return cls(
            event_id=event.event_id,
            timestamp=event.timestamp,
            source=event.source,
            service=event.service,
            raw_payload=event.raw_payload,
            metadata=event.metadata,
            event_type=event.event_type,
            severity=event.severity,
            classification_confidence=event.classification_confidence,
            classification_method=event.classification_method,
            **kwargs,
        )
