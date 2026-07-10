"""Lightweight re-ranking (lexical + score blend). Cross-encoder optional later."""

from __future__ import annotations

import re
from dataclasses import dataclass

from eaw.application.ports.vector_store import VectorSearchHit


@dataclass
class RankedPassage:
    hit: VectorSearchHit
    score: float
    content: str
    title: str
    rank: int = 0


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def rerank_hits(
    query: str,
    hits: list[VectorSearchHit],
    *,
    top_n: int = 6,
) -> list[RankedPassage]:
    """
    Blend dense score with simple lexical overlap.
    Acts as a portable stand-in for a cross-encoder (can swap adapter later).
    """
    q_tokens = _tokenize(query)
    ranked: list[RankedPassage] = []
    for h in hits:
        content = (h.payload.get("content_preview") or h.payload.get("content") or "")
        title = h.payload.get("title") or "Source"
        c_tokens = _tokenize(f"{title} {content}")
        overlap = len(q_tokens & c_tokens) / max(1, len(q_tokens))
        blended = 0.7 * float(h.score) + 0.3 * overlap
        ranked.append(
            RankedPassage(hit=h, score=blended, content=content, title=title)
        )
    ranked.sort(key=lambda r: r.score, reverse=True)
    top = ranked[:top_n]
    for i, r in enumerate(top, start=1):
        r.rank = i
    return top


def compress_passages(
    passages: list[RankedPassage],
    *,
    max_chars: int = 12000,
) -> list[RankedPassage]:
    """Greedy context budget packing; drops low-value tail content."""
    out: list[RankedPassage] = []
    used = 0
    for p in passages:
        text = p.content.strip()
        if not text:
            continue
        # Prefer first paragraphs within budget
        if used + len(text) > max_chars:
            remaining = max_chars - used
            if remaining < 200:
                break
            text = text[:remaining]
            p = RankedPassage(
                hit=p.hit,
                score=p.score,
                content=text,
                title=p.title,
                rank=p.rank,
            )
        out.append(p)
        used += len(text)
        if used >= max_chars:
            break
    # re-number
    for i, p in enumerate(out, start=1):
        p.rank = i
    return out
