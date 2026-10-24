"""
tests/test_evaluation.py — Unit tests for the evaluation module

Tests:
  - hit_rate: correct page found / not found
  - reciprocal_rank: correct 1/rank calculation
  - check_citations: covered in test_citations.py (imported here for smoke test)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation import hit_rate, reciprocal_rank


def _results(page_nums: list[int]) -> list[dict]:
    return [{"page_number": p, "score": 0.9 - i * 0.05}
            for i, p in enumerate(page_nums)]


class TestHitRate:
    def test_hit_at_first(self):
        assert hit_rate(_results([5, 2, 3]), expected_page=5) is True

    def test_hit_at_last(self):
        assert hit_rate(_results([1, 2, 5]), expected_page=5) is True

    def test_miss(self):
        assert hit_rate(_results([1, 2, 3]), expected_page=5) is False

    def test_empty_results(self):
        assert hit_rate([], expected_page=1) is False

    def test_page_not_in_list(self):
        assert hit_rate(_results([10, 20, 30]), expected_page=15) is False


class TestReciprocalRank:
    def test_rank_1(self):
        rr = reciprocal_rank(_results([5, 2, 3]), expected_page=5)
        assert rr == pytest.approx(1.0)

    def test_rank_2(self):
        rr = reciprocal_rank(_results([1, 5, 3]), expected_page=5)
        assert rr == pytest.approx(0.5)

    def test_rank_3(self):
        rr = reciprocal_rank(_results([1, 2, 5]), expected_page=5)
        assert rr == pytest.approx(1 / 3)

    def test_not_found(self):
        rr = reciprocal_rank(_results([1, 2, 3]), expected_page=9)
        assert rr == 0.0

    def test_empty(self):
        assert reciprocal_rank([], expected_page=1) == 0.0
