"""Grounded echo LLM for offline/dev without API keys."""

from __future__ import annotations

from collections.abc import Iterator
import re

from eaw.application.ports.llm import ChatMessage, LLMPort, LLMResult


class EchoLLMAdapter(LLMPort):
    """
    Builds a grounded-style answer from CONTEXT blocks in the system prompt.
    Used when LLM_PROVIDER=echo (default for local).
    """

    def __init__(self, model: str = "echo-grounded-v1") -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def _answer_from_messages(self, messages: list[ChatMessage]) -> str:
        system = next((m.content for m in messages if m.role == "system"), "")
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")

        if "INSUFFICIENT_CONTEXT" in system or "NO_RELEVANT_CONTEXT" in system:
            return (
                "I don't have enough information in the knowledge base to answer "
                "that question reliably. Please upload or index relevant documents, "
                "or rephrase your question."
            )

        # Parse [n] title ... blocks
        blocks = re.findall(
            r"\[(\d+)\]\s*(.+?)\n(.*?)(?=\n\[\d+\]|\Z)",
            system,
            flags=re.S,
        )
        if not blocks:
            return (
                "I don't have enough information in the knowledge base to answer "
                "that question reliably."
            )

        parts = [
            f"Based on the retrieved sources regarding: {user.strip()[:200]}",
            "",
        ]
        for num, title, body in blocks[:6]:
            excerpt = " ".join(body.strip().split())[:400]
            parts.append(f"[{num}] {title.strip()}: {excerpt}")
        parts.append("")
        parts.append(
            "Summary: The answer above is grounded only in the cited sources. "
            "If details are missing from those sources, they were not invented."
        )
        return "\n".join(parts)

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        content = self._answer_from_messages(messages)
        return LLMResult(
            content=content[: max_tokens * 4],
            model=self._model,
            input_tokens=sum(len(m.content) // 4 for m in messages),
            output_tokens=len(content) // 4,
        )

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        content = self.complete(
            messages, temperature=temperature, max_tokens=max_tokens
        ).content
        # Stream word-ish chunks
        words = content.split(" ")
        buf: list[str] = []
        for i, w in enumerate(words):
            buf.append(w)
            if len(buf) >= 4 or i == len(words) - 1:
                yield (" ".join(buf) + (" " if i < len(words) - 1 else ""))
                buf = []
