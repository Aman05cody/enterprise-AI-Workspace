"""Qdrant vector store adapter."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from eaw.application.ports.vector_store import (
    VectorPoint,
    VectorSearchHit,
    VectorStorePort,
)


class QdrantVectorStore(VectorStorePort):
    def __init__(
        self,
        *,
        url: str,
        collection: str,
        api_key: str = "",
    ) -> None:
        from qdrant_client import QdrantClient

        self.collection = collection
        kwargs = {"url": url}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = QdrantClient(**kwargs)
        self._vector_size: int | None = None

    def ensure_collection(self, *, vector_size: int) -> None:
        from qdrant_client.http import models as qm

        self._vector_size = vector_size
        names = [c.name for c in self._client.get_collections().collections]
        if self.collection not in names:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(
                    size=vector_size,
                    distance=qm.Distance.COSINE,
                ),
            )
            # Payload indexes for multi-tenant filters
            for field in (
                "organization_id",
                "knowledge_base_id",
                "document_id",
            ):
                try:
                    self._client.create_payload_index(
                        collection_name=self.collection,
                        field_name=field,
                        field_schema=qm.PayloadSchemaType.KEYWORD,
                    )
                except Exception:  # noqa: BLE001
                    pass

    def upsert(self, points: list[VectorPoint]) -> None:
        from qdrant_client.http import models as qm

        if not points:
            return
        self._client.upsert(
            collection_name=self.collection,
            points=[
                qm.PointStruct(
                    id=p.id,
                    vector=p.vector,
                    payload=p.payload,
                )
                for p in points
            ],
        )

    def delete_by_document(
        self, *, organization_id: UUID, document_id: UUID
    ) -> None:
        from qdrant_client.http import models as qm

        self._client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="organization_id",
                            match=qm.MatchValue(value=str(organization_id)),
                        ),
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=str(document_id)),
                        ),
                    ]
                )
            ),
        )

    def search(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        query_vector: list[float],
        top_k: int = 20,
        document_id: Optional[UUID] = None,
    ) -> list[VectorSearchHit]:
        from qdrant_client.http import models as qm

        must = [
            qm.FieldCondition(
                key="organization_id",
                match=qm.MatchValue(value=str(organization_id)),
            ),
            qm.FieldCondition(
                key="knowledge_base_id",
                match=qm.MatchValue(value=str(knowledge_base_id)),
            ),
        ]
        if document_id:
            must.append(
                qm.FieldCondition(
                    key="document_id",
                    match=qm.MatchValue(value=str(document_id)),
                )
            )

        results = self._client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=qm.Filter(must=must),
            limit=top_k,
            with_payload=True,
        )
        return [
            VectorSearchHit(
                id=str(r.id),
                score=float(r.score),
                payload=dict(r.payload or {}),
            )
            for r in results
        ]
