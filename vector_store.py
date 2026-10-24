"""
vector_store.py — Embedding generation and FAISS vector search

Responsibilities:
  1. Load the Sentence Transformer model (once, cached in session).
  2. Generate L2-normalised embeddings for a list of text strings.
  3. Build a FAISS IndexFlatIP (inner-product = cosine on normalised vecs).
  4. Save and load the index + metadata to/from disk.
  5. Run similarity searches and return results with full chunk metadata.

Design notes
  - Index files live in INDEX_DIR as: {doc_id}.faiss + {doc_id}.meta.json
  - A "combined" index (all_docs.faiss) is rebuilt whenever documents change.
  - Scores returned are cosine similarity in [0, 1] (higher = more relevant).
  - We deliberately keep embedding and search code separate from the UI.
"""

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np

from config import DEFAULT_TOP_K, EMBEDDING_DIM, EMBEDDING_MODEL, INDEX_DIR
from utils import get_logger

logger = get_logger(__name__)

# ── Model singleton ────────────────────────────────────────────────────────────
_model = None   # loaded on first use


def get_model():
    """Load the embedding model once and cache it in memory."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        try:
            from sentence_transformers import SentenceTransformer
            # Try loading cached local files first to prevent network timeouts when offline
            try:
                _model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
            except Exception:
                _model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            raise RuntimeError(
                f"Could not load embedding model '{EMBEDDING_MODEL}'. "
                f"Ensure sentence-transformers is installed and "
                f"you have internet access for the first download.\n\nError: {exc}"
            ) from exc
    return _model


# ── Embedding generation ───────────────────────────────────────────────────────

def embed_texts(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """
    Convert a list of text strings to L2-normalised embeddings.

    Returns:
        numpy array of shape (len(texts), EMBEDDING_DIM), dtype float32.
    """
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2 normalise → cosine via inner product
    )
    return embeddings.astype(np.float32)


# ── Index I/O ──────────────────────────────────────────────────────────────────

def _index_path(name: str) -> Path:
    return INDEX_DIR / f"{name}.faiss"

def _meta_path(name: str) -> Path:
    return INDEX_DIR / f"{name}.meta.json"


def save_index(index, metadata: list[dict], name: str) -> None:
    """Persist a FAISS index and its chunk metadata to disk."""
    import faiss
    faiss.write_index(index, str(_index_path(name)))
    with open(_meta_path(name), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info("Saved index '%s' (%d vectors)", name, index.ntotal)


def load_index(name: str) -> tuple:
    """
    Load a FAISS index and its metadata from disk.

    Returns:
        (index, metadata_list) or (None, []) if not found.
    """
    import faiss
    ip = _index_path(name)
    mp = _meta_path(name)
    if not ip.exists() or not mp.exists():
        return None, []
    try:
        index = faiss.read_index(str(ip))
        with open(mp, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        logger.info("Loaded index '%s' (%d vectors)", name, index.ntotal)
        return index, metadata
    except Exception as exc:
        logger.error("Failed to load index '%s': %s", name, exc)
        return None, []


def delete_index(name: str) -> None:
    """Remove a FAISS index and its metadata file."""
    for path in [_index_path(name), _meta_path(name)]:
        if path.exists():
            path.unlink()
            logger.info("Deleted index file: %s", path)


def index_exists(name: str) -> bool:
    return _index_path(name).exists() and _meta_path(name).exists()


# ── Build an index ─────────────────────────────────────────────────────────────

def build_index(chunks: list[dict], name: str) -> tuple:
    """
    Embed a list of chunk dicts and build a new FAISS index.

    Each chunk dict must have at minimum: 'chunk_id', 'text', and metadata fields.

    Returns (index, metadata_list).
    """
    import faiss

    if not chunks:
        raise ValueError("Cannot build an index from an empty chunk list.")

    texts = [c["text"] for c in chunks]
    logger.info("Embedding %d chunks for index '%s'…", len(texts), name)
    embeddings = embed_texts(texts)

    index = faiss.IndexFlatIP(EMBEDDING_DIM)   # inner product on normalised vecs = cosine
    index.add(embeddings)

    # Metadata mirrors the chunk records but stores only what search needs
    metadata = [
        {
            "chunk_id":    c["chunk_id"],
            "doc_id":      c["doc_id"],
            "filename":    c["filename"],
            "page_number": c["page_number"],
            "chunk_seq":   c["chunk_seq"],
            "text":        c["text"],
        }
        for c in chunks
    ]

    save_index(index, metadata, name)
    return index, metadata


# ── Combined (all-documents) index ────────────────────────────────────────────

def rebuild_combined_index(all_chunks: list[dict]) -> bool:
    """
    Rebuild the combined index from all available chunks.
    Called after any document is added or removed.
    Returns True on success.
    """
    if not all_chunks:
        # Nothing to index — remove stale combined index if present
        delete_index("all_docs")
        return True
    try:
        build_index(all_chunks, "all_docs")
        return True
    except Exception as exc:
        logger.error("Failed to rebuild combined index: %s", exc)
        return False


# ── Similarity search ──────────────────────────────────────────────────────────

def search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    doc_id_filter: Optional[str] = None,
) -> list[dict]:
    """
    Embed the query and retrieve the top-k most similar chunks.

    Args:
        query:         The user's question / search string.
        top_k:         Maximum number of results to return.
        doc_id_filter: If set, only return chunks from that document.

    Returns:
        List of result dicts, each containing chunk metadata + 'score'.
        Scores are cosine similarities in roughly [0, 1].
        List may be shorter than top_k if the index is small.
    """
    import faiss

    # Choose which index to search
    if doc_id_filter:
        index, metadata = load_index(doc_id_filter)
        if index is None:
            # Fall back to combined if per-doc index missing
            index, metadata = load_index("all_docs")
    else:
        index, metadata = load_index("all_docs")

    if index is None or index.ntotal == 0:
        logger.warning("No index available for search.")
        return []

    # Embed the query (returns shape [1, dim])
    q_vec = embed_texts([query])

    # Search — k can't exceed total vectors in index
    k = min(top_k, index.ntotal)
    scores, indices = index.search(q_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        chunk = dict(metadata[idx])
        chunk["score"] = float(score)
        # Apply doc filter post-search if needed
        if doc_id_filter and chunk.get("doc_id") != doc_id_filter:
            continue
        results.append(chunk)

    logger.info(
        "Search '%s…' → %d results (top score %.3f)",
        query[:40], len(results), results[0]["score"] if results else 0,
    )
    return results
