"""Tests for RAG engine."""

from __future__ import annotations

import pytest

from pipeline.rag import RAGEngine


async def test_index_and_retrieve(rag_engine: RAGEngine):
    await rag_engine.index_document(
        doc_id="runbook/high_cpu",
        content="High CPU usage runbook. Scale horizontally when CPU > 80%.",
        metadata={"type": "runbook"},
    )
    await rag_engine.index_document(
        doc_id="runbook/memory_leak",
        content="Memory leak runbook. OOMKilled indicates container exceeded memory limit.",
        metadata={"type": "runbook"},
    )

    results = await rag_engine.retrieve("CPU high usage scaling")
    assert len(results) > 0
    assert results[0].doc_id in ("runbook/high_cpu", "runbook/memory_leak")


async def test_retrieve_context_formatted(rag_engine: RAGEngine):
    await rag_engine.index_document(
        doc_id="postmortem/2024_12",
        content="Checkout outage caused by NullPointerException in shipping calculator.",
        metadata={"type": "postmortem", "source": "postmortems/2024_12_outage.md"},
    )

    context = await rag_engine.retrieve_context("checkout shipping error")
    assert "postmortem" in context.lower() or "checkout" in context.lower()


async def test_retrieve_empty_store(rag_engine: RAGEngine):
    results = await rag_engine.retrieve("anything")
    assert results == []


async def test_retrieve_context_empty(rag_engine: RAGEngine):
    context = await rag_engine.retrieve_context("anything")
    assert "nenhum" in context.lower()


async def test_index_documents_batch(rag_engine: RAGEngine):
    docs = [
        {"id": "doc1", "content": "First document about CPU alerts", "metadata": {"type": "runbook"}},
        {"id": "doc2", "content": "Second document about memory issues", "metadata": {"type": "runbook"}},
        {"id": "doc3", "content": "Third document about deploy changelog", "metadata": {"type": "changelog"}},
    ]
    count = await rag_engine.index_documents(docs)
    assert count == 3

    results = await rag_engine.retrieve("memory issues")
    assert len(results) == 3  # returns all (top_k=3)
