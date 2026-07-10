"""OpenAI-compatible chat completions."""

from __future__ import annotations

from collections.abc import Iterator
import json

import httpx

from eaw.application.ports.llm import ChatMessage, LLMPort, LLMResult
from eaw.domain.common.errors import AppError


class OpenAILLMAdapter(LLMPort):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        api_base: str = "https://api.openai.com/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._api_base = api_base.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        if not self._api_key:
            raise AppError("OPENAI_API_KEY is not configured")
        payload = {
            "model": self._model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                f"{self._api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
        if resp.status_code >= 400:
            raise AppError(
                f"LLM request failed: {resp.status_code}",
                details={"body": resp.text[:500]},
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage") or {}
        return LLMResult(
            content=content,
            model=data.get("model", self._model),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw=data,
        )

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        if not self._api_key:
            raise AppError("OPENAI_API_KEY is not configured")
        payload = {
            "model": self._model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST",
                f"{self._api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as resp:
                if resp.status_code >= 400:
                    body = resp.read().decode("utf-8", errors="replace")
                    raise AppError(
                        f"LLM stream failed: {resp.status_code}",
                        details={"body": body[:500]},
                    )
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                            delta = obj["choices"][0].get("delta") or {}
                            piece = delta.get("content")
                            if piece:
                                yield piece
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
