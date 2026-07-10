"""Embedding + vector memory store unit tests."""

from uuid import uuid4

from eaw.application.ports.vector_store import VectorPoint
from eaw.infrastructure.embeddings.hash_embeddings import HashEmbeddingAdapter
from eaw.infrastructure.vector.memory_store import MemoryVectorStore


def test_hash_embedding_normalized() -> None:
    emb = HashEmbeddingAdapter(dimensions=64)
    v = emb.embed_query("enterprise knowledge base")
    assert len(v) == 64
    # unit-ish length
    norm = sum(x * x for x in v) ** 0.5
    assert 0.99 <= norm <= 1.01


def test_memory_search_filters_tenant() -> None:
    store = MemoryVectorStore()
    emb = HashEmbeddingAdapter(dimensions=32)
    store.ensure_collection(vector_size=32)

    org_a, org_b = uuid4(), uuid4()
    kb = uuid4()
    doc = uuid4()

    va = emb.embed_query("remote work policy")
    vb = emb.embed_query("unrelated cooking recipes")

    store.upsert(
        [
            VectorPoint(
                id=str(uuid4()),
                vector=va,
                payload={
                    "organization_id": str(org_a),
                    "knowledge_base_id": str(kb),
                    "document_id": str(doc),
                    "content_preview": "remote work policy allows hybrid",
                    "title": "HR",
                },
            ),
            VectorPoint(
                id=str(uuid4()),
                vector=vb,
                payload={
                    "organization_id": str(org_b),
                    "knowledge_base_id": str(kb),
                    "document_id": str(uuid4()),
                    "content_preview": "pasta carbonara",
                    "title": "Food",
                },
            ),
        ]
    )

    q = emb.embed_query("remote hybrid work")
    hits = store.search(
        organization_id=org_a,
        knowledge_base_id=kb,
        query_vector=q,
        top_k=5,
    )
    assert hits
    assert all(h.payload["organization_id"] == str(org_a) for h in hits)
