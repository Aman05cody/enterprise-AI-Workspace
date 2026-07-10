"""Deterministic local embeddings for offline/dev (not for production quality)."""

from __future__ import annotations

import hashlib
import math
import struct

from eaw.application.ports.embeddings import EmbeddingPort


class HashEmbeddingAdapter(EmbeddingPort):
    """
    Hash-based pseudo-embeddings so the full pipeline runs without API keys.
    Replace with OpenAI / sentence-transformers in production.
    """

    def __init__(self, dimensions: int = 384) -> None:
        self._dim = max(8, dimensions)

    @property
    def model_name(self) -> str:
        return f"hash-embedding-{self._dim}"

    @property
    def dimensions(self) -> int:
        return self._dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = text.lower().split() or [""]
        for token in tokens:
            # Expand token into multiple 4-byte floats via successive hashes
            seed = token.encode("utf-8")
            for i in range(self._dim):
                digest = hashlib.sha256(seed + i.to_bytes(4, "little")).digest()
                # Map two bytes to a stable float in [-1, 1]
                val = int.from_bytes(digest[0:2], "little") / 65535.0  # [0, 1]
                signed = (val * 2.0) - 1.0
                vec[i] += signed
        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-12:
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)
