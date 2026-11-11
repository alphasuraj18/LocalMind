import pytest

from app.rag.chunker import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_one_chunk():
    assert chunk_text("LocalMind RAG testing") == [
        "LocalMind RAG testing"
    ]


def test_chunks_respect_chunk_size():
    text = "A" * 2000
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)


def test_chunks_preserve_overlap():
    text = "A" * 1000
    chunks = chunk_text(text, chunk_size=400, overlap=100)

    assert len(chunks) > 1
    assert chunks[0][-100:] == chunks[1][:100]


def test_invalid_overlap_raises_error():
    with pytest.raises(ValueError):
        chunk_text("Some text", chunk_size=100, overlap=100)


def test_chunks_preserve_all_text_content():
    text = "First section. Second section. Third section."
    chunks = chunk_text(text, chunk_size=20, overlap=5)

    reconstructed = " ".join(chunks)

    for word in text.split():
        assert word in reconstructed
