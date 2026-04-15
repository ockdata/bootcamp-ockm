from __future__ import annotations

import pytest

from pipeline.rag import RAGEngine
from providers.dummy_llm import DummyLLM
from providers.faiss_store import FAISSStore
from providers.local_embeddings import LocalEmbeddings
from providers.terminal_sink import TerminalSink
from schemas.events import RawEvent


@pytest.fixture
def dummy_llm() -> DummyLLM:
    return DummyLLM()


@pytest.fixture
def embedder() -> LocalEmbeddings:
    return LocalEmbeddings()


@pytest.fixture
def vector_store() -> FAISSStore:
    return FAISSStore(dim=64)


@pytest.fixture
def rag_engine(embedder, vector_store) -> RAGEngine:
    return RAGEngine(embedder=embedder, store=vector_store, top_k=3)


@pytest.fixture
def terminal_sink() -> TerminalSink:
    return TerminalSink()


@pytest.fixture
def sample_events() -> list[RawEvent]:
    return [
        RawEvent(
            source="cloud_logging",
            service="checkout",
            raw_payload=(
                "ERROR checkout-pod-7f8d9 NullPointerException in "
                "ShippingCalculator.calculate() — address.getCep() returned null"
            ),
            metadata={"pod": "checkout-pod-7f8d9", "version": "v2.15.0"},
        ),
        RawEvent(
            source="application",
            service="payments",
            raw_payload=(
                "CRITICAL payments-pod-3a1b2 Gateway timeout after 10000ms "
                "for transaction txn_9182736. HTTP 504."
            ),
            metadata={"gateway": "gateway-alpha"},
        ),
        RawEvent(
            source="cloud_logging",
            service="inventory",
            raw_payload=(
                "CRITICAL inventory-pod-5c4d3 OOMKilled: container exceeded "
                "memory limit (2Gi). RSS=2.1GB."
            ),
            metadata={"restart_count": 3},
        ),
        RawEvent(
            source="deploy",
            service="checkout",
            raw_payload=(
                "DEPLOY checkout v2.15.0 → v2.15.1. "
                "Changes: fix null check, add Redis cache."
            ),
            metadata={"deployer": "ci-bot"},
        ),
        RawEvent(
            source="cloud_logging",
            service="frontend",
            raw_payload=(
                "INFO frontend-pod-a1b2c Health check passed. "
                "Response time: 45ms. Active users: 1247."
            ),
            metadata={"response_ms": 45},
        ),
    ]
