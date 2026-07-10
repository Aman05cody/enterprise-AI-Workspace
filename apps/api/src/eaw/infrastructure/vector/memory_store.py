"""In-memory vector store for local/dev without Qdrant."""

from __future__ import annotations

import math
import threading
from typing import Optional
from uuid import UUID

from eaw.application.ports.vector_store import (
    VectorPoint,
    VectorSearchHit,
    VectorStorePort,
)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class MemoryVectorStore(VectorStorePort):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._points: dict[str, VectorPoint] = {}
        self._vector_size: int | None = None

    def ensure_collection(self, *, vector_size: int) -> None:
        self._vector_size = vector_size

    def upsert(self, points: list[VectorPoint]) -> None:
        with self._lock:
            for p in points:
                self._points[p.id] = p

    def delete_by_document(
        self, *, organization_id: UUID, document_id: UUID
    ) -> None:
        org = str(organization_id)
        doc = str(document_id)
        with self._lock:
            to_del = [
                pid
                for pid, p in self._points.items()
                if p.payload.get("organization_id") == org
                and p.payload.get("document_id") == doc
            ]
            for pid in to_del:
                del self._points[pid]

    def search(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        query_vector: list[float],
        top_k: int = 20,
        document_id: Optional[UUID] = None,
    ) -> list[VectorSearchHit]:
        org = str(organization_id)
        kb = str(knowledge_base_id)
        doc_filter = str(document_id) if document_id else None
        scored: list[VectorSearchHit] = []
        with self._lock:
            for p in self._points.values():
                if p.payload.get("organization_id") != org:
                    continue
                if p.payload.get("knowledge_base_id") != kb:
                    continue
                if doc_filter and p.payload.get("document_id") != doc_filter:
                    continue
                score = _cosine(query_vector, p.vector)
                scored.append(
                    VectorSearchHit(id=p.id, score=score, payload=p.payload)
                )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]


# Process-wide singleton for sync workers + API in same process
_MEMORY_STORE: MemoryVectorStore | None = None


def get_memory_store() -> MemoryVectorStore:
    global _MEMORY_STORE
    if _MEMORY_STORE is None:
        _MEMORY_STORE = MemoryVectorStore()
    return _MEMORY_STORE
