import json
from pathlib import Path


DATASET = Path(__file__).parent / "retrieval_dataset.json"


def test_dataset_has_at_least_40_queries():
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    assert len(items) >= 40


def test_every_query_has_explicit_answerability_label():
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    assert all(isinstance(item.get("expected_answerable"), bool) for item in items)


def test_unanswerable_queries_have_no_relevant_chunk_labels():
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    unanswerable = [item for item in items if not item["expected_answerable"]]
    assert len(unanswerable) >= 20
    assert all(item["relevant"] == [] for item in unanswerable)


def test_answerable_queries_have_relevant_chunk_labels():
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    answerable = [item for item in items if item["expected_answerable"]]
    assert len(answerable) >= 24
    assert all(item["relevant"] for item in answerable)


def test_queries_are_unique():
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    queries = [item["query"].strip().lower() for item in items]
    assert len(queries) == len(set(queries))
