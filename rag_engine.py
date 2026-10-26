"""
rag_engine.py — End-to-end RAG pipeline coordinator

Combines pdf_processor, vector_store, database, and llm_service into
a single, easy-to-call interface used by every UI page.

Functions:
  ingest_pdf(file_bytes, filename)   — validate → extract → chunk → embed → index
  query(question, ...)               — search → build context → generate answer
  delete_document(doc_id)            — remove from DB, index, and disk
"""

import time
from pathlib import Path
from typing import Optional

import database as db
from config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, DEFAULT_TOP_K, UPLOAD_DIR
from llm_service import generate_answer
from pdf_processor import chunk_pages, extract_pages, make_doc_id, validate_pdf
from utils import Timer, get_logger, human_readable_size
from vector_store import (
    build_index,
    delete_index,
    index_exists,
    rebuild_combined_index,
    search,
)

logger = get_logger(__name__)


# ── Ingest ─────────────────────────────────────────────────────────────────────

def ingest_pdf(
    file_bytes: bytes,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    progress_callback=None,   # optional callable(pct: float, msg: str)
) -> dict:
    """
    Full ingestion pipeline for one PDF file.

    Steps:
      1. Validate the file.
      2. Check for duplicate (by content hash).
      3. Extract text page-by-page.
      4. Chunk the text.
      5. Store chunk records in SQLite.
      6. Build a per-document FAISS index.
      7. Rebuild the combined index.
      8. Save the file to disk.
      9. Update document status in DB.

    Returns a result dict:
      {success, doc_id, filename, page_count, chunk_count,
       warnings, error, duplicate, processing_ms}
    """

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)
        logger.info("[%.0f%%] %s", pct * 100, msg)

    # ── 1. Validate ────────────────────────────────────────────────────────────
    progress(0.05, "Validating file…")
    valid, reason = validate_pdf(filename, file_bytes)
    if not valid:
        return {"success": False, "error": reason, "duplicate": False}

    # ── 2. Duplicate check ─────────────────────────────────────────────────────
    progress(0.10, "Checking for duplicates…")
    from utils import compute_file_hash
    file_hash = compute_file_hash(file_bytes)
    doc_id    = make_doc_id(file_hash)

    existing = db.get_document_by_hash(file_hash)
    if existing:
        if existing.get("status") == "indexed":
            return {
                "success":    True,
                "duplicate":  True,
                "doc_id":     existing["id"],
                "filename":   existing["filename"],
                "page_count": existing["page_count"],
                "chunk_count": existing["chunk_count"],
                "warnings":   [],
                "error":      None,
                "processing_ms": 0,
            }
        else:
            # Previous indexing attempt was interrupted or ended in error/indexing state.
            # Clean up the partial document and its chunks before re-indexing.
            logger.info("Cleaning up incomplete document %s (status=%s) before re-indexing", filename, existing.get("status"))
            try:
                delete_document(existing["id"])
            except Exception as exc:
                logger.warning("Could not cleanly delete partial document %s: %s", existing["id"], exc)

    # ── 3. Insert placeholder document record ──────────────────────────────────
    safe_name = filename
    db.insert_document({
        "id":          doc_id,
        "filename":    safe_name,
        "file_hash":   file_hash,
        "file_size":   len(file_bytes),
        "page_count":  0,
        "status":      "indexing",
        "upload_time": time.time(),
    })
    db.log_activity("upload", f"Uploaded '{filename}'", doc_id=doc_id)

    # ── 4. Extract text ────────────────────────────────────────────────────────
    progress(0.20, "Extracting text from PDF…")
    with Timer() as t:
        extraction = extract_pages(file_bytes, filename)

    if not extraction["success"]:
        db.update_document_status(doc_id, "error", error_msg=extraction["error"])
        db.log_activity("error", f"Extraction failed: {filename}", extraction["error"], doc_id)
        return {"success": False, "error": extraction["error"], "duplicate": False, "doc_id": doc_id}

    pages = extraction["pages"]

    # ── 5. Chunk ───────────────────────────────────────────────────────────────
    progress(0.40, f"Chunking {len(pages)} pages…")
    chunks = chunk_pages(pages, doc_id, safe_name, chunk_size, chunk_overlap)

    if not chunks:
        msg = "No text chunks could be extracted. The PDF may contain only images."
        db.update_document_status(doc_id, "error", error_msg=msg)
        return {"success": False, "error": msg, "duplicate": False, "doc_id": doc_id}

    # ── 6. Persist chunks in DB ────────────────────────────────────────────────
    progress(0.55, f"Storing {len(chunks)} chunks…")
    db.insert_chunks(chunks)

    # ── 7. Build per-document FAISS index ─────────────────────────────────────
    progress(0.65, "Generating embeddings…")
    try:
        build_index(chunks, doc_id)
    except Exception as exc:
        db.update_document_status(doc_id, "error", error_msg=str(exc))
        db.log_activity("error", "Embedding failed", str(exc), doc_id)
        return {"success": False, "error": f"Embedding failed: {exc}", "duplicate": False, "doc_id": doc_id}

    # ── 8. Rebuild combined index ──────────────────────────────────────────────
    progress(0.80, "Updating global search index…")
    all_chunks = db.get_all_chunks()
    rebuild_combined_index(all_chunks)

    # ── 9. Save file to disk ───────────────────────────────────────────────────
    progress(0.90, "Saving file…")
    file_path = UPLOAD_DIR / f"{doc_id}.pdf"
    file_path.write_bytes(file_bytes)

    # ── 10. Finalise DB record ─────────────────────────────────────────────────
    processing_ms = int(t.elapsed * 1000)
    db.update_document_status(
        doc_id, "indexed",
        chunk_count=len(chunks),
        processing_ms=processing_ms,
    )
    # Update page count
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE documents SET page_count=? WHERE id=?",
            (extraction["page_count"], doc_id),
        )
    db.log_activity(
        "index",
        f"Indexed '{filename}' — {extraction['page_count']} pages, {len(chunks)} chunks",
        doc_id=doc_id,
    )
    progress(1.0, "Done!")

    return {
        "success":      True,
        "duplicate":    False,
        "doc_id":       doc_id,
        "filename":     safe_name,
        "page_count":   extraction["page_count"],
        "chunk_count":  len(chunks),
        "warnings":     extraction.get("warnings", []),
        "error":        None,
        "processing_ms": processing_ms,
    }


# ── Query ──────────────────────────────────────────────────────────────────────

def query(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    doc_id_filter: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> dict:
    """
    Full RAG query pipeline.

    Steps:
      1. Retrieve top-k relevant chunks via vector search.
      2. Generate a grounded answer with source citations.
      3. Log the query to the DB.

    Returns:
        {answer, used_chunks, model, duration_ms, error, query_id}
    """
    from config import OLLAMA_MODEL
    if model is None:
        model = OLLAMA_MODEL

    start = time.perf_counter()

    # 1. Retrieve
    retrieved = search(question, top_k=top_k, doc_id_filter=doc_id_filter)

    # 2. Generate
    result = generate_answer(question, retrieved, model=model, temperature=temperature)

    total_ms = int((time.perf_counter() - start) * 1000)
    result["duration_ms"] = total_ms

    # 3. Log
    import json
    source_refs = json.dumps([c["chunk_id"] for c in result.get("used_chunks", [])])
    qid = db.insert_query({
        "question":   question,
        "answer":     result.get("answer", ""),
        "doc_filter": doc_id_filter,
        "top_k":      top_k,
        "timestamp":  time.time(),
        "duration_ms": total_ms,
        "source_refs": source_refs,
    })
    db.log_activity("query", f"Asked: {question[:80]}", doc_id=doc_id_filter or "")
    result["query_id"] = qid

    return result


# ── Delete ─────────────────────────────────────────────────────────────────────

def delete_document(doc_id: str) -> dict:
    """
    Completely remove a document:
      1. Delete chunks from DB (cascade).
      2. Delete per-doc FAISS index files.
      3. Delete the saved PDF file.
      4. Rebuild the combined index without this document.
      5. Remove the DB record.

    Returns {"success": bool, "error": str}
    """
    try:
        # Remove index files
        delete_index(doc_id)

        # Remove saved PDF
        pdf_file = UPLOAD_DIR / f"{doc_id}.pdf"
        if pdf_file.exists():
            pdf_file.unlink()

        # Remove from DB (chunks cascade via FK)
        db.delete_document(doc_id)

        # Rebuild combined index
        remaining = db.get_all_chunks()
        rebuild_combined_index(remaining)

        db.log_activity("delete", f"Deleted document {doc_id}", doc_id=doc_id)
        logger.info("Document %s deleted successfully.", doc_id)
        return {"success": True, "error": None}

    except Exception as exc:
        logger.exception("Failed to delete document %s", doc_id)
        return {"success": False, "error": str(exc)}
