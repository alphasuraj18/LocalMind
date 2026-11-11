def classify_answerability(score: float, threshold: float) -> bool:
    """Classify a query as answerable when its top retrieval score meets threshold."""
    return score >= threshold


def answerability_metrics(
    scores: list[float],
    labels: list[bool],
    threshold: float,
) -> dict:
    """Compute answerability classification metrics for a fixed threshold."""
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have the same length")
    if not scores:
        raise ValueError("at least one score/label pair is required")

    tp = fp = tn = fn = 0
    for score, expected in zip(scores, labels):
        predicted = classify_answerability(float(score), threshold)
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and not expected:
            tn += 1
        else:
            fn += 1

    total = len(scores)
    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    false_acceptance_rate = fp / (fp + tn) if fp + tn else 0.0
    false_rejection_rate = fn / (fn + tp) if fn + tp else 0.0

    return {
        "threshold": float(threshold),
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "false_acceptance_rate": false_acceptance_rate,
        "false_rejection_rate": false_rejection_rate,
    }
