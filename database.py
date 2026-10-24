"""
database.py — SQLite persistence layer

Handles all database operations: documents, chunks, query history,
and activity events. Uses Python's built-in sqlite3 module — no ORM needed.

Tables:
  documents    — one row per uploaded PDF
  chunks       — one row per text chunk extracted from a PDF
  queries      — one row per question asked
  activity     — one row per app event (upload, index, query, etc.)
"""

import sqlite3
import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DB_PATH
from utils import get_logger

logger = get_logger(__name__)


# ── Connection ─────────────────────────────────────────────────────────────────

@contextmanager
def get_conn():
    """Context manager that yields a SQLite connection and commits/rolls back."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row          # row["column"] syntax
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema initialisation ──────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,          -- SHA-256 content hash (first 16 hex chars)
    filename      TEXT NOT NULL,
    file_hash     TEXT NOT NULL UNIQUE,      -- full SHA-256
    file_size     INTEGER NOT NULL,          -- bytes
    page_count    INTEGER NOT NULL DEFAULT 0,
    chunk_count   INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'pending',
    error_msg     TEXT,
    upload_time   REAL NOT NULL,             -- Unix timestamp
    index_time    REAL,                      -- when indexing finished
    processing_ms INTEGER                   -- how long processing took
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    TEXT PRIMARY KEY,            -- doc_id + "_" + seq
    doc_id      TEXT NOT NULL,
    filename    TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    chunk_seq   INTEGER NOT NULL,
    text        TEXT NOT NULL,
    char_count  INTEGER NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS queries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question    TEXT NOT NULL,
    answer      TEXT,
    doc_filter  TEXT,                        -- NULL means all docs
    top_k       INTEGER,
    timestamp   REAL NOT NULL,
    duration_ms INTEGER,
    source_refs TEXT                         -- JSON list of chunk_ids
);

CREATE TABLE IF NOT EXISTS activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,               -- 'upload','index','query','delete','error'
    description TEXT NOT NULL,
    detail      TEXT,                        -- extra JSON or text
    timestamp   REAL NOT NULL,
    doc_id      TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id   ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_queries_ts      ON queries(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_ts     ON activity(timestamp);
"""


def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database initialised at %s", DB_PATH)


# ── Document CRUD ──────────────────────────────────────────────────────────────

def insert_document(doc: dict) -> None:
    """Insert a new document record."""
    sql = """
    INSERT INTO documents
        (id, filename, file_hash, file_size, page_count, status, upload_time)
    VALUES
        (:id, :filename, :file_hash, :file_size, :page_count, :status, :upload_time)
    """
    with get_conn() as conn:
        conn.execute(sql, doc)


def get_document(doc_id: str) -> Optional[dict]:
    """Return a document by its ID, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return dict(row) if row else None


def get_document_by_hash(file_hash: str) -> Optional[dict]:
    """Return an existing document with the same content hash, or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        return dict(row) if row else None


def list_documents() -> list[dict]:
    """Return all documents, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY upload_time DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_document_status(
    doc_id: str,
    status: str,
    chunk_count: int = 0,
    processing_ms: int = 0,
    error_msg: str = "",
) -> None:
    """Update processing result for a document."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE documents
               SET status=?, chunk_count=?, processing_ms=?,
                   error_msg=?, index_time=?
               WHERE id=?""",
            (status, chunk_count, processing_ms, error_msg or None,
             time.time(), doc_id),
        )


def delete_document(doc_id: str) -> None:
    """Delete a document and its chunks (cascade via FK)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    logger.info("Deleted document %s", doc_id)


# ── Chunk CRUD ─────────────────────────────────────────────────────────────────

def insert_chunks(chunks: list[dict]) -> None:
    """Bulk-insert extracted text chunks."""
    sql = """
    INSERT OR IGNORE INTO chunks
        (chunk_id, doc_id, filename, page_number, chunk_seq, text, char_count)
    VALUES
        (:chunk_id, :doc_id, :filename, :page_number, :chunk_seq, :text, :char_count)
    """
    with get_conn() as conn:
        conn.executemany(sql, chunks)


def get_chunks_for_doc(doc_id: str) -> list[dict]:
    """Return all chunks for a given document, in order."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE doc_id=? ORDER BY page_number, chunk_seq",
            (doc_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_chunks() -> list[dict]:
    """Return every chunk across all documents."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks ORDER BY doc_id, page_number, chunk_seq"
        ).fetchall()
        return [dict(r) for r in rows]


# ── Query history ──────────────────────────────────────────────────────────────

def insert_query(q: dict) -> int:
    """Insert a query record and return its rowid."""
    sql = """
    INSERT INTO queries (question, answer, doc_filter, top_k, timestamp, duration_ms, source_refs)
    VALUES (:question, :answer, :doc_filter, :top_k, :timestamp, :duration_ms, :source_refs)
    """
    with get_conn() as conn:
        cur = conn.execute(sql, q)
        return cur.lastrowid


def list_queries(limit: int = 100) -> list[dict]:
    """Return recent queries, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM queries ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Activity feed ──────────────────────────────────────────────────────────────

def log_activity(event_type: str, description: str,
                 detail: str = "", doc_id: str = "") -> None:
    """Append an event to the activity log."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO activity (event_type, description, detail, timestamp, doc_id)
               VALUES (?, ?, ?, ?, ?)""",
            (event_type, description, detail or None,
             time.time(), doc_id or None),
        )


def list_activity(limit: int = 20) -> list[dict]:
    """Return the most recent activity events."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM activity ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Aggregate stats ────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return dashboard KPI numbers."""
    with get_conn() as conn:
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status='indexed'"
        ).fetchone()[0]
        page_total = conn.execute(
            "SELECT COALESCE(SUM(page_count),0) FROM documents WHERE status='indexed'"
        ).fetchone()[0]
        chunk_total = conn.execute(
            "SELECT COALESCE(SUM(chunk_count),0) FROM documents WHERE status='indexed'"
        ).fetchone()[0]
        query_count = conn.execute(
            "SELECT COUNT(*) FROM queries"
        ).fetchone()[0]
    return {
        "doc_count":   doc_count,
        "page_total":  page_total,
        "chunk_total": chunk_total,
        "query_count": query_count,
    }
