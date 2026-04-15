"""Step 7: Alert emission based on risk threshold."""

from __future__ import annotations

from typing import TYPE_CHECKING

from observability.logger import get_logger
from schemas.alerts import Alert, RiskScore
from schemas.events import ClassifiedEvent
from schemas.llm_responses import ExtractionResult, RootCauseResult

if TYPE_CHECKING:
    from protocols.alert_sink import AlertSink

log = get_logger(__name__)


def build_alert(
    event: ClassifiedEvent,
    extraction: ExtractionResult,
    root_cause: RootCauseResult,
    risk: RiskScore,
    pipeline_run_id: str,
) -> Alert:
    """Build an Alert from pipeline results."""
    title = f"{event.severity.upper()} — {event.service}: {event.event_type}"

    return Alert(
        event_id=event.event_id,
        service=event.service,
        severity=event.severity,
        risk_score=risk.score,
        risk_level=risk.level,
        title=title,
        summary=extraction.summary,
        root_cause=root_cause.root_cause,
        recommendations=root_cause.recommendations,
        pipeline_run_id=pipeline_run_id,
    )


async def emit_alert(
    alert: Alert,
    sinks: list[AlertSink],
) -> bool:
    """Send alert to all configured sinks."""
    success = True
    for sink in sinks:
        try:
            sent = await sink.send(alert)
            if not sent:
                log.warning("alert.sink.failed", sink=type(sink).__name__, alert_id=alert.alert_id)
                success = False
        except Exception as e:
            log.error(
                "alert.sink.error",
                sink=type(sink).__name__,
                alert_id=alert.alert_id,
                error=str(e),
            )
            success = False

    log.info(
        "alert.emitted",
        alert_id=alert.alert_id,
        event_id=alert.event_id,
        risk_score=alert.risk_score,
        risk_level=alert.risk_level,
    )
    return success
