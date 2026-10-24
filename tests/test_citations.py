"""
tests/test_citations.py — Unit tests for citation checking

Tests that the check_citations function correctly identifies
valid and invalid [S1] [S2] citation labels in an answer.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation import check_citations


def _make_chunks(n: int) -> list[dict]:
    """Create n fake chunks for testing."""
    return [
        {"chunk_id": f"doc_{i}", "doc_id": "d1", "filename": "test.pdf",
         "page_number": i + 1, "text": f"Chunk text {i}"}
        for i in range(n)
    ]


class TestCheckCitations:
    def test_valid_single_citation(self):
        answer = "According to [S1] the answer is clear."
        result = check_citations(answer, _make_chunks(3))
        assert result["valid"] is True
        assert "[S1]" in result["valid_labels"]
        assert result["invalid_labels"] == []

    def test_valid_multiple_citations(self):
        answer = "See [S1] and [S2] for details."
        result = check_citations(answer, _make_chunks(3))
        assert result["valid"] is True
        assert "[S1]" in result["valid_labels"]
        assert "[S2]" in result["valid_labels"]

    def test_invalid_citation_out_of_range(self):
        answer = "According to [S5] this is true."  # only 3 chunks
        result = check_citations(answer, _make_chunks(3))
        assert result["valid"] is False
        assert "[S5]" in result["invalid_labels"]

    def test_no_citations(self):
        answer = "The answer has no citations."
        result = check_citations(answer, _make_chunks(3))
        # valid is False because no citations present
        assert result["cited"] == []

    def test_mixed_valid_invalid(self):
        answer = "From [S1] and [S10] we know this."
        result = check_citations(answer, _make_chunks(3))
        assert result["valid"] is False
        assert "[S1]" in result["valid_labels"]
        assert "[S10]" in result["invalid_labels"]

    def test_empty_chunks(self):
        answer = "According to [S1] something happened."
        result = check_citations(answer, [])
        assert result["valid"] is False
        assert "[S1]" in result["invalid_labels"]

    def test_duplicate_citations_deduplicated(self):
        answer = "See [S1] again [S1] for more."
        result = check_citations(answer, _make_chunks(2))
        # [S1] appears twice but should be counted once
        assert result["cited"].count("[S1]") == 1

    def test_s_boundary_case(self):
        # [S0] is invalid — 1-indexed only
        answer = "As stated in [S0]."
        result = check_citations(answer, _make_chunks(3))
        assert "[S0]" in result["invalid_labels"]
