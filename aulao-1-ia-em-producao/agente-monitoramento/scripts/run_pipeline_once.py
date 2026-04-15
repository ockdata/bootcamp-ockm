"""Run the pipeline once on a single batch — for testing and quick validation."""

from __future__ import annotations

import asyncio

from config.settings import get_settings
from observability.logger import setup_logging
from pipeline.engine import PipelineEngine
from pipeline.rag import RAGEngine
from providers.dummy_llm import DummyLLM
from providers.faiss_store import FAISSStore
from providers.local_embeddings import LocalEmbeddings
from providers.terminal_sink import TerminalSink
from schemas.events import RawEvent
from scripts.seed_bigquery import SYNTHETIC_EVENTS
from scripts.seed_rag import seed_rag


async def main() -> None:
    settings = get_settings()
    setup_logging(level=settings.log_level, fmt="console")

    # Build providers
    llm = DummyLLM()
    rag_engine, doc_count = await seed_rag(settings.rag_data_dir)
    terminal = TerminalSink()

    # Build engine
    engine = PipelineEngine(
        llm=llm,
        rag_engine=rag_engine,
        alert_sinks=[terminal],
        prompt_version=settings.prompt_version,
        alert_threshold=settings.alert_risk_threshold,
    )

    # Build events from synthetic data
    events = [
        RawEvent(
            source=e["source"],
            service=e["service"],
            raw_payload=e["raw_payload"],
            metadata=e["metadata"],
        )
        for e in SYNTHETIC_EVENTS[:5]
    ]

    # Run
    enriched, alerts, tracer = await engine.process_batch(events)

    print(f"\n{'='*60}")
    print(f"Processados: {len(enriched)} eventos")
    print(f"Alertas: {len(alerts)}")
    print(f"Anomalias: {tracer.anomalies_detected}")
    print(f"LLM calls: {tracer.metrics.total_calls}")
    print(f"Custo estimado: ${tracer.metrics.total_cost_usd}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
