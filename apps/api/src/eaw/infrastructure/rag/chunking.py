"""Text cleaning and chunking."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    index: int
    content: str
    token_count: int
    metadata: dict


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    # Rough heuristic: ~4 chars per token
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[TextChunk]:
    """Character-window chunker with overlap (token-estimate sized)."""
    cleaned = clean_text(text)
    if not cleaned:
        return []

    # Work in approximate token units via char windows
    size_chars = max(100, chunk_size * 4)
    overlap_chars = max(0, min(chunk_overlap * 4, size_chars // 2))

    chunks: list[TextChunk] = []
    start = 0
    idx = 0
    n = len(cleaned)

    while start < n:
        end = min(n, start + size_chars)
        # Prefer break on paragraph/sentence boundary
        if end < n:
            window = cleaned[start:end]
            break_at = max(
                window.rfind("\n\n"),
                window.rfind("\n"),
                window.rfind(". "),
            )
            if break_at > size_chars * 0.4:
                end = start + break_at + 1

        content = cleaned[start:end].strip()
        if content:
            chunks.append(
                TextChunk(
                    index=idx,
                    content=content,
                    token_count=estimate_tokens(content),
                    metadata={"char_start": start, "char_end": end},
                )
            )
            idx += 1

        if end >= n:
            break
        start = max(0, end - overlap_chars)

    return chunks
