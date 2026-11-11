import pytest

from app.rag.grounding import (
    extract_source_citations,
    has_valid_source_citations,
)


def test_extracts_source_numbers():
    answer = "Python is interpreted [Source 1]. It has libraries [Source 2]."
    assert extract_source_citations(answer) == [1, 2]


def test_citation_matching_is_case_insensitive():
    assert extract_source_citations("Claim [source 2].") == [2]


def test_accepts_valid_citations():
    assert has_valid_source_citations(
        "The document describes Python [Source 1].", source_count=2
    )


def test_rejects_missing_citations():
    assert not has_valid_source_citations(
        "The document describes Python.", source_count=2
    )


def test_rejects_out_of_range_citations():
    assert not has_valid_source_citations(
        "The document describes Python [Source 3].", source_count=2
    )


def test_rejects_mixed_valid_and_invalid_citations():
    assert not has_valid_source_citations(
        "Python is useful [Source 1]. It is fast [Source 4].",
        source_count=2,
    )


@pytest.mark.parametrize("source_count", [0, -1])
def test_rejects_citations_when_no_sources_exist(source_count):
    assert not has_valid_source_citations(
        "A claim [Source 1].", source_count=source_count
    )


def test_empty_response_has_no_citations():
    assert extract_source_citations("") == []
    assert not has_valid_source_citations("", source_count=1)
