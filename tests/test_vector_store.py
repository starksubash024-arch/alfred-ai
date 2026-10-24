"""
tests/test_vector_store.py — Unit tests for vector store operations

Tests cover:
  - embed_texts returns correct shape and dtype
  - build_index builds a valid FAISS index
  - search returns results with required metadata keys
  - search on empty / missing index returns []
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import tempfile
from pathlib import Path


# ── embed_texts ────────────────────────────────────────────────────────────────

class TestEmbedTexts:
    def test_output_shape(self):
        from vector_store import embed_texts
        texts = ["Hello world", "Python RAG pipeline"]
        emb = embed_texts(texts)
        assert emb.shape == (2, 384)   # all-MiniLM-L6-v2 → 384 dims

    def test_output_dtype(self):
        from vector_store import embed_texts
        emb = embed_texts(["test"])
        assert emb.dtype == np.float32

    def test_normalised(self):
        from vector_store import embed_texts
        emb = embed_texts(["normalised embedding test"])
        norms = np.linalg.norm(emb, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_single_text(self):
        from vector_store import embed_texts
        emb = embed_texts(["only one"])
        assert emb.shape[0] == 1

    def test_different_texts_different_embeddings(self):
        from vector_store import embed_texts
        e1 = embed_texts(["The cat sat on the mat"])
        e2 = embed_texts(["Machine learning is fascinating"])
        sim = float(np.dot(e1[0], e2[0]))
        assert sim < 0.99   # should not be nearly identical


# ── build_index + search ───────────────────────────────────────────────────────

class TestBuildAndSearch:
    @pytest.fixture(autouse=True)
    def patch_index_dir(self, tmp_path, monkeypatch):
        """Redirect INDEX_DIR to a temp directory for test isolation."""
        import config as cfg
        import vector_store as vs
        monkeypatch.setattr(cfg, "INDEX_DIR", tmp_path)
        monkeypatch.setattr(vs, "INDEX_DIR", tmp_path)

    def _make_chunks(self):
        return [
            {"chunk_id": "d1_00000", "doc_id": "d1", "filename": "a.pdf",
             "page_number": 1, "chunk_seq": 0, "text": "Artificial intelligence and machine learning"},
            {"chunk_id": "d1_00001", "doc_id": "d1", "filename": "a.pdf",
             "page_number": 2, "chunk_seq": 1, "text": "Deep learning neural networks"},
            {"chunk_id": "d1_00002", "doc_id": "d1", "filename": "a.pdf",
             "page_number": 3, "chunk_seq": 2, "text": "Python programming and software development"},
        ]

    def test_build_index_creates_files(self, tmp_path):
        from vector_store import build_index
        chunks = self._make_chunks()
        build_index(chunks, "d1")
        assert (tmp_path / "d1.faiss").exists()
        assert (tmp_path / "d1.meta.json").exists()

    def test_search_returns_results(self):
        from vector_store import build_index, search
        chunks = self._make_chunks()
        build_index(chunks, "all_docs")
        results = search("machine learning AI", top_k=2)
        assert len(results) >= 1

    def test_search_result_keys(self):
        from vector_store import build_index, search
        chunks = self._make_chunks()
        build_index(chunks, "all_docs")
        results = search("neural network", top_k=3)
        assert len(results) > 0
        required_keys = {"chunk_id", "doc_id", "filename", "page_number", "text", "score"}
        assert required_keys.issubset(set(results[0].keys()))

    def test_search_scores_in_range(self):
        from vector_store import build_index, search
        build_index(self._make_chunks(), "all_docs")
        results = search("python development", top_k=3)
        for r in results:
            assert -0.1 <= r["score"] <= 1.1

    def test_search_empty_index(self):
        from vector_store import search
        # No index built — should return []
        results = search("anything", top_k=5)
        assert results == []

    def test_empty_chunk_list_raises(self):
        from vector_store import build_index
        with pytest.raises(ValueError, match="empty"):
            build_index([], "empty_test")

    def test_top_k_respected(self):
        from vector_store import build_index, search
        chunks = self._make_chunks()
        build_index(chunks, "all_docs")
        results = search("AI", top_k=1)
        assert len(results) <= 1

    def test_doc_filter(self):
        from vector_store import build_index, search
        chunks = self._make_chunks()
        # Build per-doc index
        build_index(chunks, "d1")
        results = search("machine learning", top_k=5, doc_id_filter="d1")
        # All results should belong to d1
        for r in results:
            assert r["doc_id"] == "d1"
