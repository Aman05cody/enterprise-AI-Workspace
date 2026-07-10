"""Vector store port."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID


@dataclass
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSearchHit:
    id: str
    score: float
    payload: dict[str, Any]


class VectorStorePort(ABC):
    @abstractmethod
    def ensure_collection(self, *, vector_size: int) -> None:
        ...

    @abstractmethod
    def upsert(self, points: list[VectorPoint]) -> None:
        ...

    @abstractmethod
    def delete_by_document(
        self, *, organization_id: UUID, document_id: UUID
    ) -> None:
        ...

    @abstractmethod
    def search(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        query_vector: list[float],
        top_k: int = 20,
        document_id: Optional[UUID] = None,
    ) -> list[VectorSearchHit]:
        ...
