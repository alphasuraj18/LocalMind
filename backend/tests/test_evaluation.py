import pytest

from app.rag.evaluation import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_precision_at_k():
    retrieved = ["A", "B", "C", "D"]
    relevant = {"A", "C"}

    assert precision_at_k(retrieved, relevant, 4) == 0.5


def test_precision_uses_k_as_denominator_when_fewer_results_exist():
    assert precision_at_k(["A"], {"A"}, 5) == 0.2


def test_precision_at_k_ignores_results_after_k():
    assert precision_at_k(["A", "B", "C"], {"C"}, 2) == 0.0


def test_recall_at_k():
    retrieved = ["A", "B", "C"]
    relevant = {"A", "C", "D"}

    assert recall_at_k(retrieved, relevant, 3) == pytest.approx(2 / 3)


def test_recall_returns_zero_when_no_relevant_items_exist():
    assert recall_at_k(["A", "B"], set(), 2) == 0.0


def test_reciprocal_rank_first_result():
    assert reciprocal_rank(["A", "B"], {"A"}) == 1.0


def test_reciprocal_rank_second_result():
    assert reciprocal_rank(["A", "B"], {"B"}) == 0.5


def test_reciprocal_rank_no_relevant_result():
    assert reciprocal_rank(["A", "B"], {"C"}) == 0.0


def test_reciprocal_rank_empty_relevant_set():
    assert reciprocal_rank(["A", "B"], set()) == 0.0


@pytest.mark.parametrize("k", [0, -1])
def test_precision_rejects_invalid_k(k):
    with pytest.raises(ValueError):
        precision_at_k(["A"], {"A"}, k)


@pytest.mark.parametrize("k", [0, -1])
def test_recall_rejects_invalid_k(k):
    with pytest.raises(ValueError):
        recall_at_k(["A"], {"A"}, k)

def test_mean_reciprocal_rank():
    from app.rag.evaluation import mean_reciprocal_rank

    queries = [
        (["A", "B"], {"A"}),       # RR = 1.0
        (["A", "B"], {"B"}),       # RR = 0.5
        (["A", "B"], {"C"}),       # RR = 0.0
    ]

    assert mean_reciprocal_rank(queries) == pytest.approx(0.5)


def test_mean_reciprocal_rank_empty_input():
    from app.rag.evaluation import mean_reciprocal_rank

    assert mean_reciprocal_rank([]) == 0.0
