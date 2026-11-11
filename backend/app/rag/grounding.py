import re


_SOURCE_CITATION_PATTERN = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)


def extract_source_citations(response: str) -> list[int]:
    """Return source numbers explicitly cited using the [Source N] format."""
    if not response:
        return []
    return [int(match.group(1)) for match in _SOURCE_CITATION_PATTERN.finditer(response)]


def has_valid_source_citations(response: str, source_count: int) -> bool:
    """
    Require at least one citation and ensure every cited source number exists.

    This validates citation references only; it does not prove semantic
    entailment between an answer claim and the cited passage.
    """
    if source_count <= 0:
        return False

    citations = extract_source_citations(response)
    return bool(citations) and all(1 <= number <= source_count for number in citations)
