"""Prompt and rerank unit tests."""

from eaw.application.ports.vector_store import VectorSearchHit
from eaw.infrastructure.rag.prompts import build_system_prompt, suggest_followups
from eaw.infrastructure.rag.rerank import compress_passages, rerank_hits


def test_insufficient_prompt() -> None:
    p = build_system_prompt(passages=[], memory_summary=None, insufficient=True)
    assert p.insufficient
    assert "INSUFFICIENT_CONTEXT" in p.system


def test_grounded_prompt() -> None:
    p = build_system_prompt(
        passages=[
            {
                "rank": 1,
                "title": "Policy",
                "content": "Remote work is allowed 3 days per week.",
                "score": 0.9,
            }
        ],
        memory_summary="User asked about HR",
        insufficient=False,
    )
    assert not p.insufficient
    assert "[1] Policy" in p.system
    assert "CONVERSATION MEMORY" in p.system


def test_rerank_and_compress() -> None:
    hits = [
        VectorSearchHit(
            id="a",
            score=0.2,
            payload={"title": "A", "content_preview": "unrelated cooking pasta"},
        ),
        VectorSearchHit(
            id="b",
            score=0.5,
            payload={
                "title": "HR",
                "content_preview": "remote work hybrid policy for employees",
            },
        ),
    ]
    ranked = rerank_hits("remote hybrid work policy", hits, top_n=2)
    assert ranked[0].hit.id == "b"
    compressed = compress_passages(ranked, max_chars=50)
    assert compressed
    assert len(compressed[0].content) <= 50


def test_suggestions() -> None:
    s = suggest_followups("What is PTO?", "answer", True)
    assert len(s) == 3
