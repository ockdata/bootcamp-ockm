"""Vector store protocol for RAG."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class RAGResult(BaseModel):
    """A single result from a vector store search."""

    doc_id: str
    score: float = 0.0
    content: str = ""
    metadata: dict = Field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    """Any class that can store and search vectors."""

    async def upsert(
        self, doc_id: str, embedding: list[float], metadata: dict,
    ) -> None: ...

    async def search(
        self, query_embedding: list[float], top_k: int = 5,
    ) -> list[RAGResult]: ...
