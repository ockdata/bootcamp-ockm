"""FAISS-based in-memory vector store for RAG.

Falls back to pure numpy brute-force when FAISS is not available or has
ABI incompatibility with the installed numpy version.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from protocols.vector_store import RAGResult


def _faiss_available() -> bool:
    """Check if FAISS is installed AND actually works with current numpy."""
    try:
        import faiss

        idx = faiss.IndexFlatIP(4)
        vec = np.zeros((1, 4), dtype="float32")
        idx.add(vec)
        return True
    except Exception:
        return False


_USE_FAISS = _faiss_available()


class FAISSStore:
    """In-memory vector store. Uses FAISS when available, numpy brute-force otherwise.

    Implements VectorStore protocol.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim
        self._metadata: dict[int, dict[str, Any]] = {}
        self._doc_ids: dict[int, str] = {}
        self._id_to_idx: dict[str, int] = {}
        self._next_idx = 0
        self._vectors: list[np.ndarray] = []

        if _USE_FAISS:
            import faiss

            self._index = faiss.IndexFlatIP(dim)
        else:
            self._index = None

    async def upsert(
        self,
        doc_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        vec = np.array(embedding, dtype=np.float32)

        if doc_id in self._id_to_idx:
            idx = self._id_to_idx[doc_id]
            self._metadata[idx] = metadata
            self._vectors[idx] = vec
            return

        idx = self._next_idx
        self._next_idx += 1
        self._doc_ids[idx] = doc_id
        self._id_to_idx[doc_id] = idx
        self._metadata[idx] = metadata
        self._vectors.append(vec)

        if self._index is not None:
            self._index.add(vec.reshape(1, -1))

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[RAGResult]:
        if self._next_idx == 0:
            return []

        query = np.array(query_embedding, dtype=np.float32)
        k = min(top_k, self._next_idx)

        if self._index is not None and self._index.ntotal == self._next_idx:
            q = query.reshape(1, -1)
            scores, indices = self._index.search(q, k)
            score_list = scores[0].tolist()
            idx_list = indices[0].tolist()
        else:
            # Numpy brute-force: inner product (cosine on L2-normalized vecs)
            mat = np.array(self._vectors, dtype=np.float32)
            sims = mat @ query
            top_indices = np.argsort(sims)[-k:][::-1]
            idx_list = top_indices.tolist()
            score_list = sims[top_indices].tolist()

        results: list[RAGResult] = []
        for score, idx in zip(score_list, idx_list):
            if idx < 0:
                continue
            meta = self._metadata.get(idx, {})
            results.append(
                RAGResult(
                    doc_id=self._doc_ids.get(idx, ""),
                    score=float(score),
                    content=meta.get("content", ""),
                    metadata=meta,
                )
            )

        return results
