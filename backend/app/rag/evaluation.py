def _validate_k(k: int) -> None:
    if k <= 0:
        raise ValueError("k must be greater than zero")


def precision_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    _validate_k(k)
    top_k = retrieved[:k]
    return sum(item in relevant for item in top_k) / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    _validate_k(k)

    if not relevant:
        return 0.0

    top_k = retrieved[:k]
    found = sum(item in relevant for item in top_k)
    return found / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0

    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank

    return 0.0

def mean_reciprocal_rank(
    queries: list[tuple[list[str], set[str]]]
) -> float:
    if not queries:
        return 0.0

    return sum(
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in queries
    ) / len(queries)
