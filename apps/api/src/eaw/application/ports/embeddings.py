"""Embedding provider port."""

from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document chunks."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
