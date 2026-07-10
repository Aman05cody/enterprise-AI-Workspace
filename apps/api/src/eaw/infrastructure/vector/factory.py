"""Vector store factory."""

from functools import lru_cache

from eaw.application.ports.vector_store import VectorStorePort
from eaw.core.config import get_settings
from eaw.infrastructure.vector.memory_store import get_memory_store
from eaw.infrastructure.vector.qdrant_store import QdrantVectorStore


@lru_cache
def get_vector_store() -> VectorStorePort:
    settings = get_settings()
    backend = (settings.vector_store_backend or "memory").lower()
    if backend == "qdrant":
        return QdrantVectorStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            api_key=settings.qdrant_api_key or "",
        )
    return get_memory_store()
