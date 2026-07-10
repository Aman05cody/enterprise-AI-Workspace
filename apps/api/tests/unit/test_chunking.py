"""Chunking unit tests."""

from eaw.infrastructure.rag.chunking import chunk_text, clean_text


def test_clean_text() -> None:
    assert "hello" in clean_text("  hello \n\n\n world  ")


def test_chunk_overlap() -> None:
    text = ("Section A. " * 50) + ("Section B. " * 50)
    chunks = chunk_text(text, chunk_size=40, chunk_overlap=10)
    assert len(chunks) >= 2
    assert chunks[0].index == 0
    assert all(c.content for c in chunks)


def test_empty() -> None:
    assert chunk_text("   ") == []
