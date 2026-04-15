"""End-to-end pipeline test with all dummy providers."""

from __future__ import annotations

import pytest

from pipeline.engine import PipelineEngine
from pipeline.rag import RAGEngine
from providers.dummy_llm import DummyLLM
from providers.terminal_sink import TerminalSink
from schemas.events import RawEvent


@pytest.fixture
def engine(dummy_llm, rag_engine, terminal_sink) -> PipelineEngine:
    return PipelineEngine(
        llm=dummy_llm,
        rag_engine=rag_engine,
        alert_sinks=[terminal_sink],
        prompt_version="v1",
        alert_threshold=40,  # low threshold to trigger alerts in tests
    )


async def test_e2e_processes_all_events(engine, sample_events):
    enriched, alerts, tracer = await engine.process_batch(sample_events)

    assert len(enriched) == len(sample_events)
    assert tracer.events_processed == len(sample_events)
    assert tracer.events_classified == len(sample_events)
    assert tracer.metrics.total_calls > 0


async def test_e2e_enriched_fields_populated(engine, sample_events):
    enriched, _, tracer = await engine.process_batch(sample_events)

    for e in enriched:
        assert e.event_id
        assert e.event_type != ""
        assert e.severity in ("low", "medium", "high", "critical")
        assert e.classification_method in ("llm", "heuristic", "fallback")
        assert e.extracted_summary != ""
        assert e.risk_score >= 0
        assert e.risk_level in ("low", "medium", "high", "critical")
        assert e.pipeline_run_id == tracer.run_id
        assert e.prompt_version == "v1"


async def test_e2e_critical_events_generate_alerts(engine):
    events = [
        RawEvent(
            source="cloud_logging",
            service="checkout",
            raw_payload="CRITICAL OOMKilled container checkout exceeded memory limit. Fatal error.",
            metadata={"restart_count": 5},
        ),
    ]
    _, alerts, tracer = await engine.process_batch(events)

    # Critical event on checkout service should generate alert
    assert len(alerts) >= 1
    assert alerts[0].severity == "critical"
    assert alerts[0].service == "checkout"
    assert tracer.alerts_emitted >= 1


async def test_e2e_info_events_no_alerts():
    """Info events should not trigger alerts with default threshold."""
    llm = DummyLLM()
    from providers.faiss_store import FAISSStore
    from providers.local_embeddings import LocalEmbeddings

    rag = RAGEngine(LocalEmbeddings(), FAISSStore(dim=64), top_k=3)
    sink = TerminalSink()

    engine = PipelineEngine(
        llm=llm,
        rag_engine=rag,
        alert_sinks=[sink],
        alert_threshold=80,  # high threshold
    )

    events = [
        RawEvent(
            source="cloud_logging",
            service="frontend",
            raw_payload="INFO Health check passed. All good.",
        ),
    ]
    _, alerts, _ = await engine.process_batch(events)
    assert len(alerts) == 0


async def test_e2e_tracer_metrics(engine, sample_events):
    _, _, tracer = await engine.process_batch(sample_events)

    record = tracer.to_record()
    assert record.run_id == tracer.run_id
    assert record.events_processed == len(sample_events)
    assert record.total_llm_calls > 0
    assert record.prompt_version == "v1"
