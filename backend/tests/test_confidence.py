import pytest

from app.rag.confidence import answerability_metrics, classify_answerability


def test_classifies_score_at_threshold_as_answerable():
    assert classify_answerability(0.60, 0.60)


def test_classifies_score_below_threshold_as_unanswerable():
    assert not classify_answerability(0.599, 0.60)


def test_answerability_confusion_matrix_and_rates():
    result = answerability_metrics(
        scores=[0.9, 0.8, 0.2, 0.1],
        labels=[True, False, False, True],
        threshold=0.5,
    )
    assert result["true_positive"] == 1
    assert result["false_positive"] == 1
    assert result["true_negative"] == 1
    assert result["false_negative"] == 1
    assert result["accuracy"] == 0.5
    assert result["false_acceptance_rate"] == 0.5
    assert result["false_rejection_rate"] == 0.5


def test_rejects_mismatched_input_lengths():
    with pytest.raises(ValueError):
        answerability_metrics([0.2], [True, False], 0.5)


def test_rejects_empty_inputs():
    with pytest.raises(ValueError):
        answerability_metrics([], [], 0.5)
