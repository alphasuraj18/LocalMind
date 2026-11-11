import numpy as np
import pytest

from app.rag.vector_store import VectorStore


def make_store():
    store = VectorStore(dimension=3)

    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype="float32",
    )

    texts = [
        "Python programming",
        "Machine learning",
        "Database systems",
    ]

    metadata = [
        {"source": "python.txt", "chunk": 1},
        {"source": "ml.txt", "chunk": 1},
        {"source": "database.txt", "chunk": 1},
    ]

    store.add(embeddings, texts, metadata)
    return store


def test_add_vectors_and_metadata():
    store = make_store()

    assert store.index.ntotal == 3
    assert len(store.texts) == 3
    assert len(store.metadata) == 3


def test_search_returns_most_similar_result_first():
    store = make_store()

    results = store.search(
        np.array([0.0, 1.0, 0.0], dtype="float32"),
        top_k=3,
    )

    assert results[0]["text"] == "Machine learning"
    assert results[0]["source"] == "ml.txt"
    assert results[0]["score"] == pytest.approx(1.0)


def test_search_respects_top_k():
    store = make_store()

    results = store.search(
        np.array([1.0, 0.0, 0.0], dtype="float32"),
        top_k=1,
    )

    assert len(results) == 1
    assert results[0]["text"] == "Python programming"


def test_delete_by_source_removes_matching_vectors():
    store = make_store()

    removed = store.delete_by_source("ml.txt")

    assert removed == 1
    assert store.index.ntotal == 2
    assert len(store.texts) == 2
    assert len(store.metadata) == 2
    assert all(item["source"] != "ml.txt" for item in store.metadata)


def test_delete_unknown_source_changes_nothing():
    store = make_store()

    removed = store.delete_by_source("unknown.txt")

    assert removed == 0
    assert store.index.ntotal == 3


def test_add_rejects_mismatched_embedding_count():
    store = VectorStore(dimension=3)

    embeddings = np.array(
        [[1.0, 0.0, 0.0]],
        dtype="float32",
    )

    with pytest.raises(ValueError):
        store.add(embeddings, ["one", "two"])


def test_save_and_load_preserves_data(tmp_path):
    original = make_store()

    original.save(str(tmp_path))

    restored = VectorStore.load(str(tmp_path), dimension=3)

    assert restored.index.ntotal == 3
    assert restored.texts == original.texts
    assert restored.metadata == original.metadata

    results = restored.search(
        np.array([0.0, 0.0, 1.0], dtype="float32"),
        top_k=1,
    )

    assert results[0]["text"] == "Database systems"
    assert results[0]["source"] == "database.txt"
