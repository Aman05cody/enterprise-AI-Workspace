"""Embedding provider factory."""

from functools import lru_cache

from eaw.application.ports.embeddings import EmbeddingPort
from eaw.core.config import get_settings
from eaw.infrastructure.embeddings.hash_embeddings import HashEmbeddingAdapter
from eaw.infrastructure.embeddings.openai_embeddings import OpenAIEmbeddingAdapter


@lru_cache
def get_embedding_adapter() -> EmbeddingPort:
    settings = get_settings()
    provider = (settings.embedding_provider or "hash").lower()

    if provider == "openai":
        dims = settings.embedding_dimensions
        if settings.embedding_model.startswith("text-embedding-3"):
            dims = settings.embedding_dimensions
        return OpenAIEmbeddingAdapter(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=dims,
            api_base=settings.openai_api_base,
        )

    if provider == "sentence_transformers":
        try:
            from eaw.infrastructure.embeddings.st_embeddings import (  # type: ignore
                SentenceTransformerEmbeddingAdapter,
            )

            return SentenceTransformerEmbeddingAdapter(
                model_name=settings.embedding_model or "all-MiniLM-L6-v2",
                dimensions=settings.embedding_dimensions,
            )
        except Exception:
            # Fall back to hash if ST not installed
            return HashEmbeddingAdapter(dimensions=settings.embedding_dimensions)

    return HashEmbeddingAdapter(dimensions=settings.embedding_dimensions)
