"""Step 4: RAG engine — retrieves relevant runbooks, postmortems, and changelogs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from observability.logger import get_logger
from protocols.vector_store import RAGResult

if TYPE_CHECKING:
    from protocols.embeddings import EmbeddingProvider
    from protocols.vector_store import VectorStore

log = get_logger(__name__)


class RAGEngine:
    """Retrieval-Augmented Generation engine.

    Embeds a query, searches the vector store, and returns formatted context.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        top_k: int = 3,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.top_k = top_k

    async def retrieve(self, query: str) -> list[RAGResult]:
        """Retrieve relevant documents for a query."""
        embedding = await self.embedder.embed(query)
        results = await self.store.search(embedding, top_k=self.top_k)

        log.info(
            "rag.search",
            query=query[:80],
            results_count=len(results),
            top_score=round(results[0].score, 4) if results else 0.0,
        )
        return results

    async def retrieve_context(self, query: str, max_chars_per_doc: int = 500) -> str:
        """Retrieve and format context string for LLM consumption.

        Args:
            query: Search query.
            max_chars_per_doc: Max characters per document to avoid bloating prompts.
        """
        results = await self.retrieve(query)
        if not results:
            return "Nenhum documento relevante encontrado."

        sections: list[str] = []
        for i, r in enumerate(results, 1):
            source = r.metadata.get("source", "unknown")
            doc_type = r.metadata.get("type", "document")
            content = r.content[:max_chars_per_doc]
            if len(r.content) > max_chars_per_doc:
                content += "..."
            sections.append(
                f"[{i}] ({doc_type}) {r.doc_id} (score: {r.score:.3f})\n"
                f"Fonte: {source}\n"
                f"{content}\n"
            )

        return "\n---\n".join(sections)

    async def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Index a single document into the vector store."""
        embedding = await self.embedder.embed(content)
        meta = metadata or {}
        meta["content"] = content
        await self.store.upsert(doc_id, embedding, meta)
        log.info("rag.indexed", doc_id=doc_id, content_len=len(content))

    async def index_documents(
        self,
        documents: list[dict],
    ) -> int:
        """Index multiple documents. Each dict needs 'id', 'content', and optionally 'metadata'."""
        count = 0
        for doc in documents:
            await self.index_document(
                doc_id=doc["id"],
                content=doc["content"],
                metadata=doc.get("metadata", {}),
            )
            count += 1
        return count
