"""OpenAI embeddings adapter."""

from __future__ import annotations

import httpx

from eaw.application.ports.embeddings import EmbeddingPort
from eaw.domain.common.errors import AppError


class OpenAIEmbeddingAdapter(EmbeddingPort):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        api_base: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._api_base = api_base.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not self._api_key:
            raise AppError("OPENAI_API_KEY is not configured", details={})
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,
        }
        # text-embedding-3 supports dimensions param
        if self._model.startswith("text-embedding-3"):
            payload["dimensions"] = self._dimensions

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self._api_base}/embeddings",
                headers=headers,
                json=payload,
            )
        if resp.status_code >= 400:
            raise AppError(
                f"OpenAI embeddings failed: {resp.status_code}",
                details={"body": resp.text[:500]},
            )
        data = resp.json()["data"]
        data_sorted = sorted(data, key=lambda x: x["index"])
        return [row["embedding"] for row in data_sorted]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # batch in chunks of 64
        out: list[list[float]] = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            out.extend(self._embed(texts[i : i + batch_size]))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]
