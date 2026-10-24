"""
analytics.py — Data aggregation for the Analytics dashboard

Fetches real stored data from SQLite and returns plain Python dicts/lists
ready to be turned into Plotly charts. Nothing is invented here.
"""

import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import database as db
from utils import get_logger

logger = get_logger(__name__)


def get_document_stats() -> list[dict]:
    """
    Return per-document stats: filename, page_count, chunk_count, status, index_time.
    """
    docs = db.list_documents()
    return [
        {
            "filename":    d["filename"],
            "page_count":  d["page_count"],
            "chunk_count": d["chunk_count"],
            "status":      d["status"],
            "index_time":  d.get("index_time"),
            "doc_id":      d["id"],
        }
        for d in docs
    ]


def get_status_distribution() -> dict[str, int]:
    """Return count of documents in each status."""
    docs = db.list_documents()
    counts: dict[str, int] = Counter(d["status"] for d in docs)
    return dict(counts)


def get_query_timeline(days: int = 30) -> list[dict]:
    """
    Return the number of queries per day over the last `days` days.
    Result: [{"date": "YYYY-MM-DD", "count": int}, ...]
    """
    queries = db.list_queries(limit=10000)
    cutoff  = time.time() - days * 86400

    day_counts: dict[str, int] = defaultdict(int)
    for q in queries:
        if q["timestamp"] >= cutoff:
            day = datetime.fromtimestamp(q["timestamp"]).strftime("%Y-%m-%d")
            day_counts[day] += 1

    # Fill in zero-count days
    result = []
    for i in range(days):
        d = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append({"date": d, "count": day_counts.get(d, 0)})

    return result


def get_retrieval_score_distribution(limit: int = 200) -> list[float]:
    """
    Return a flat list of retrieval scores from recent queries.
    Scores come from the actual FAISS cosine-similarity search.

    Note: these are retrieval scores, not accuracy metrics.
    """
    # Scores are not stored in the DB directly; we re-read recent search results.
    # For now return an empty list — the page will show a meaningful empty state.
    # When the search function logs scores we can expose them here.
    return []


def get_insights() -> dict:
    """
    Return high-level summary numbers for the analytics sidebar.
    """
    stats = db.get_stats()
    docs  = db.list_documents()

    most_recent = None
    if docs:
        indexed = [d for d in docs if d["status"] == "indexed"]
        if indexed:
            newest = max(indexed, key=lambda d: d.get("index_time") or 0)
            most_recent = newest["filename"]

    return {
        "total_indexed_pages":  stats["page_total"],
        "total_indexed_chunks": stats["chunk_total"],
        "total_queries":        stats["query_count"],
        "most_recent_doc":      most_recent,
    }


def get_evaluation_history() -> list[dict]:
    """
    Return stored evaluation run records (if any).
    Returns empty list when no evaluations have been run yet.
    """
    # Placeholder: evaluation.py writes results here eventually.
    return []
