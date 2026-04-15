"""Hash-based local embeddings for demo and testing (no external API needed)."""

from __future__ import annotations

import hashlib
import math


EMBEDDING_DIM = 64


class LocalEmbeddings:
    """Deterministic embeddings using hash projection. Implements EmbeddingProvider protocol."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        return self._hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> list[float]:
        """Create a deterministic pseudo-embedding from text via SHA-256 chunks."""
        text_normalized = text.lower().strip()
        raw: list[float] = []

        # Generate enough hash bytes for the desired dimension
        rounds = math.ceil(self.dim / 32) + 1
        for i in range(rounds):
            h = hashlib.sha256(f"{text_normalized}::{i}".encode()).digest()
            for byte in h:
                raw.append((byte / 255.0) * 2 - 1)  # scale to [-1, 1]

        vec = raw[: self.dim]

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]
