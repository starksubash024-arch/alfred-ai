"""
evaluation.py — Retrieval evaluation metrics

Implements:
  - Hit Rate @ k  : fraction of test questions where the correct page appears in top-k
  - MRR           : Mean Reciprocal Rank (how high the right answer ranks)
  - Citation check: verifies that cited [S1] labels map to real retrieved chunks

Honest labelling rules:
  - Automated metrics measure retrieval quality, NOT factual correctness.
  - Answer faithfulness requires human review.
  - We never invent scores.
"""

import json
import time
from pathlib import Path
from typing import Optional

from vector_store import search
from utils import get_logger

logger = get_logger(__name__)

EVAL_CASES_PATH = Path(__file__).parent / "evaluation_cases.json"


# ── Load test cases ────────────────────────────────────────────────────────────

def load_eval_cases() -> list[dict]:
    """
    Load evaluation cases from evaluation_cases.json.

    Each case must have:
      - "question": str
      - "expected_page": int          (1-based page number expected in results)
      - "doc_id": str (optional)      (limit search to this document)
    """
    if not EVAL_CASES_PATH.exists():
        return []
    try:
        with open(EVAL_CASES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Could not load eval cases: %s", exc)
        return []


# ── Metrics ────────────────────────────────────────────────────────────────────

def hit_rate(results: list[dict], expected_page: int) -> bool:
    """Return True if expected_page appears anywhere in results."""
    return any(r.get("page_number") == expected_page for r in results)


def reciprocal_rank(results: list[dict], expected_page: int) -> float:
    """Return 1/(rank) where rank is the 1-based position of expected_page, 0 if not found."""
    for i, r in enumerate(results, 1):
        if r.get("page_number") == expected_page:
            return 1.0 / i
    return 0.0


# ── Run evaluation ─────────────────────────────────────────────────────────────

def run_evaluation(top_k: int = 5) -> dict:
    """
    Run evaluation on all test cases from evaluation_cases.json.

    Returns:
        {
            "hit_rate":  float,   # fraction of questions with correct page in top-k
            "mrr":       float,   # Mean Reciprocal Rank
            "n_cases":   int,
            "top_k":     int,
            "details":   list[dict],  # per-question breakdown
            "timestamp": float,
            "error":     str or None,
        }
    """
    cases = load_eval_cases()
    if not cases:
        return {
            "error": (
                "No evaluation cases found. "
                "Add cases to evaluation_cases.json and re-run."
            ),
            "hit_rate": 0.0,
            "mrr": 0.0,
            "n_cases": 0,
            "top_k": top_k,
            "details": [],
            "timestamp": time.time(),
        }

    hits = 0
    rr_total = 0.0
    details  = []

    for case in cases:
        question      = case["question"]
        expected_page = case.get("expected_page", -1)
        doc_filter    = case.get("doc_id")

        results = search(question, top_k=top_k, doc_id_filter=doc_filter)

        h  = hit_rate(results, expected_page)
        rr = reciprocal_rank(results, expected_page)
        hits     += int(h)
        rr_total += rr

        details.append({
            "question":      question,
            "expected_page": expected_page,
            "hit":           h,
            "rr":            round(rr, 4),
            "top_pages":     [r.get("page_number") for r in results[:top_k]],
            "top_scores":    [round(r.get("score", 0), 4) for r in results[:top_k]],
        })

    n = len(cases)
    return {
        "hit_rate":  round(hits / n, 4) if n else 0.0,
        "mrr":       round(rr_total / n, 4) if n else 0.0,
        "n_cases":   n,
        "top_k":     top_k,
        "details":   details,
        "timestamp": time.time(),
        "error":     None,
    }


# ── Citation checker ───────────────────────────────────────────────────────────

def check_citations(answer: str, used_chunks: list[dict]) -> dict:
    """
    Verify that every [S{n}] citation in the answer maps to a real chunk.

    Returns:
        {
            "valid":   bool,
            "cited":   list[str],   # labels found in the answer
            "valid_labels": list,
            "invalid_labels": list,  # labels with no matching chunk
        }
    """
    import re
    labels_in_answer = re.findall(r"\[S(\d+)\]", answer)
    unique_labels    = list(dict.fromkeys(labels_in_answer))  # preserve order, deduplicate

    valid_labels   = []
    invalid_labels = []

    for label in unique_labels:
        idx = int(label) - 1  # [S1] → index 0
        if 0 <= idx < len(used_chunks):
            valid_labels.append(f"[S{label}]")
        else:
            invalid_labels.append(f"[S{label}]")

    return {
        "valid":          len(invalid_labels) == 0 and len(unique_labels) > 0,
        "cited":          [f"[S{l}]" for l in unique_labels],
        "valid_labels":   valid_labels,
        "invalid_labels": invalid_labels,
    }
