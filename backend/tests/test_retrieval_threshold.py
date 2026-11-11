from types import SimpleNamespace

import numpy as np
import pytest

from app.rag.pipeline import RAGPipeline


class FakeEmbedder:
    def encode_query(self, query):
        return np.array([[1.0, 0.0]], dtype=np.float32)


class FakeStore:
    texts = ["high", "medium", "low"]

    def __init__(self, results):
        self.results = results
        self.requested_top_k = None

    def search(self, query_embedding, top_k):
        self.requested_top_k = top_k
        return self.results


def make_pipeline(results, threshold=0.45):
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.embedder = FakeEmbedder()
    pipeline.store = FakeStore(results)
    pipeline.min_similarity_score = threshold
    return pipeline


def test_retrieve_keeps_results_at_or_above_threshold():
    pipeline = make_pipeline([
        {"text": "high", "score": 0.81},
        {"text": "boundary", "score": 0.45},
        {"text": "low", "score": 0.44},
    ])

    results = pipeline.retrieve("question", top_k=3)

    assert [item["text"] for item in results] == ["high", "boundary"]
    assert pipeline.store.requested_top_k == 3


def test_retrieve_returns_empty_when_all_results_below_threshold():
    pipeline = make_pipeline([
        {"text": "low", "score": 0.2455},
        {"text": "lower", "score": 0.10},
    ])

    assert pipeline.retrieve("unrelated question") == []


def test_retrieve_can_override_threshold_per_call():
    pipeline = make_pipeline([
        {"text": "candidate", "score": 0.40},
    ], threshold=0.45)

    assert pipeline.retrieve("question", min_similarity_score=0.35)


def test_retrieve_returns_empty_when_store_has_no_texts():
    pipeline = make_pipeline([{"text": "high", "score": 0.9}])
    pipeline.store.texts = []

    assert pipeline.retrieve("question") == []


@pytest.mark.parametrize("threshold", [-1.01, 1.01])
def test_retrieve_rejects_out_of_range_threshold(threshold):
    pipeline = make_pipeline([], threshold=0.45)

    with pytest.raises(ValueError):
        pipeline.retrieve("question", min_similarity_score=threshold)


def test_constructor_rejects_invalid_threshold(monkeypatch):
    monkeypatch.setenv("LOCALMIND_MIN_RETRIEVAL_SCORE", "not-a-number")

    with pytest.raises(ValueError):
        RAGPipeline.__new__(RAGPipeline).__init__()
