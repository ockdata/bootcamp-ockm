"""Tests for the classification pipeline step."""

from __future__ import annotations

import pytest

from observability.tracer import PipelineTracer
from pipeline.classifier import classify_event
from schemas.events import RawEvent


@pytest.fixture
def tracer() -> PipelineTracer:
    return PipelineTracer()


async def test_classify_error_event(dummy_llm, tracer):
    event = RawEvent(
        source="application",
        service="checkout",
        raw_payload="ERROR NullPointerException in ShippingCalculator",
    )
    result = await classify_event(event, dummy_llm, tracer)

    assert result.event_type == "app_error"
    assert result.severity == "high"
    assert result.classification_confidence > 0
    assert result.classification_method == "llm"  # DummyLLM counts as "llm"


async def test_classify_critical_event(dummy_llm, tracer):
    event = RawEvent(
        source="cloud_logging",
        service="inventory",
        raw_payload="CRITICAL OOMKilled container exceeded memory limit",
    )
    result = await classify_event(event, dummy_llm, tracer)

    assert result.severity == "critical"
    assert result.event_type == "metric_alert"  # "memory" keyword


async def test_classify_deploy_event(dummy_llm, tracer):
    event = RawEvent(
        source="deploy",
        service="checkout",
        raw_payload="DEPLOY checkout v2.15.0 → v2.15.1",
    )
    result = await classify_event(event, dummy_llm, tracer)

    assert result.event_type == "deploy"
    assert result.severity == "low"


async def test_classify_info_event(dummy_llm, tracer):
    event = RawEvent(
        source="cloud_logging",
        service="frontend",
        raw_payload="INFO Health check passed. Response time: 45ms",
    )
    result = await classify_event(event, dummy_llm, tracer)

    assert result.severity == "low"


async def test_classify_tracks_metrics(dummy_llm, tracer):
    event = RawEvent(
        source="application",
        service="test",
        raw_payload="ERROR something went wrong",
    )
    await classify_event(event, dummy_llm, tracer)

    assert tracer.events_classified == 1
    assert tracer.metrics.total_calls == 1
