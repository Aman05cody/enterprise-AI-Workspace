"""Hybrid retrieval + re-ranking for enterprise RAG."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eaw.application.ports.embeddings import EmbeddingPort
from eaw.application.ports.vector_store import VectorSearchHit, VectorStorePort
from eaw.application.services.org_service import OrgService
from eaw.core.config import Settings
from eaw.domain.common.enums import MembershipRole
from eaw.domain.tenancy.policies import can_read_knowledge, require_role
from eaw.infrastructure.db.models.ingestion import DocumentChunk
from eaw.infrastructure.db.models.knowledge import KnowledgeBase
from eaw.infrastructure.rag.rerank import RankedPassage, compress_passages, rerank_hits


class RetrievalService:
    def __init__(
        self,
        db: Session,
        org_service: OrgService,
        embeddings: EmbeddingPort,
        vectors: VectorStorePort,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.org = org_service
        self.embeddings = embeddings
        self.vectors = vectors
        from eaw.core.config import get_settings

        self.settings = settings or get_settings()

    def _assert_kb_access(self, kb_id: UUID, user_id: UUID) -> KnowledgeBase:
        kb = self.db.get(KnowledgeBase, kb_id)
        if kb is None or kb.deleted_at is not None:
            from eaw.domain.common.errors import NotFoundError

            raise NotFoundError("Knowledge base not found")
        mem = self.org.get_membership(kb.organization_id, user_id)
        if not can_read_knowledge(mem.role):
            require_role(mem.role, MembershipRole.GUEST, action="search knowledge")
        return kb

    def semantic_search(
        self,
        *,
        kb_id: UUID,
        user_id: UUID,
        query: str,
        top_k: int = 10,
    ) -> list[VectorSearchHit]:
        kb = self._assert_kb_access(kb_id, user_id)
        qvec = self.embeddings.embed_query(query)
        self.vectors.ensure_collection(vector_size=len(qvec))
        return self.vectors.search(
            organization_id=kb.organization_id,
            knowledge_base_id=kb.id,
            query_vector=qvec,
            top_k=top_k,
        )

    def _keyword_hits(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        query: str,
        limit: int = 15,
    ) -> list[VectorSearchHit]:
        like = f"%{query.strip()}%"
        rows = list(
            self.db.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.organization_id == organization_id,
                    DocumentChunk.knowledge_base_id == knowledge_base_id,
                    DocumentChunk.content.ilike(like),
                )
                .limit(limit)
            ).all()
        )

        hits: list[VectorSearchHit] = []
        for r in rows:
            # crude keyword score
            score = 0.35
            hits.append(
                VectorSearchHit(
                    id=str(r.id),
                    score=score,
                    payload={
                        "organization_id": str(r.organization_id),
                        "knowledge_base_id": str(r.knowledge_base_id),
                        "document_id": str(r.document_id),
                        "chunk_id": str(r.id),
                        "chunk_index": r.chunk_index,
                        "title": (r.metadata_ or {}).get("title") or "Source",
                        "content_preview": r.content[:800],
                        "content": r.content,
                        "source": "keyword",
                    },
                )
            )
        return hits

    def hybrid_retrieve(
        self,
        *,
        kb_id: UUID,
        user_id: UUID,
        query: str,
        top_k: int | None = None,
        rerank_top_n: int | None = None,
    ) -> tuple[list[RankedPassage], float]:
        """
        Dense + keyword retrieval, re-rank, compress.
        Returns passages and confidence (0-1).
        """
        kb = self._assert_kb_access(kb_id, user_id)
        top_k = top_k or self.settings.rag_top_k
        rerank_top_n = rerank_top_n or self.settings.rag_rerank_top_n

        dense = self.semantic_search(
            kb_id=kb.id, user_id=user_id, query=query, top_k=top_k
        )
        # Enrich dense payloads with full chunk content when possible
        dense = self._enrich_hits(dense)

        keyword = self._keyword_hits(
            organization_id=kb.organization_id,
            knowledge_base_id=kb.id,
            query=query,
            limit=min(15, top_k),
        )

        merged = self._merge_hits(dense, keyword)
        ranked = rerank_hits(query, merged, top_n=rerank_top_n)
        compressed = compress_passages(
            ranked, max_chars=self.settings.rag_max_context_chars
        )

        confidence = 0.0
        if compressed:
            # map top score to 0..1 (dense scores vary by backend)
            top = max(p.score for p in compressed)
            confidence = max(0.0, min(1.0, top if top <= 1.5 else top / 2.0))
            # boost slightly when multiple sources agree
            if len(compressed) >= 3:
                confidence = min(1.0, confidence + 0.05)

        return compressed, confidence

    def _enrich_hits(self, hits: list[VectorSearchHit]) -> list[VectorSearchHit]:
        out: list[VectorSearchHit] = []
        for h in hits:
            payload = dict(h.payload)
            if not payload.get("content"):
                # try load from DB by chunk id
                try:
                    cid = UUID(str(payload.get("chunk_id") or h.id))
                    chunk = self.db.get(DocumentChunk, cid)
                    if chunk:
                        payload["content"] = chunk.content
                        payload["content_preview"] = chunk.content[:800]
                        if not payload.get("title"):
                            payload["title"] = (chunk.metadata_ or {}).get("title")
                except Exception:  # noqa: BLE001
                    pass
            out.append(VectorSearchHit(id=h.id, score=h.score, payload=payload))
        return out

    def _merge_hits(
        self, dense: list[VectorSearchHit], keyword: list[VectorSearchHit]
    ) -> list[VectorSearchHit]:
        by_id: dict[str, VectorSearchHit] = {}
        for h in dense + keyword:
            existing = by_id.get(h.id)
            if existing is None or h.score > existing.score:
                by_id[h.id] = h
            elif existing and h.payload.get("content") and not existing.payload.get(
                "content"
            ):
                # keep higher score but merge content
                payload = dict(existing.payload)
                payload["content"] = h.payload.get("content")
                by_id[h.id] = VectorSearchHit(
                    id=existing.id, score=existing.score, payload=payload
                )
        return list(by_id.values())
