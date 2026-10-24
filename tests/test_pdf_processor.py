"""
tests/test_pdf_processor.py — Unit tests for PDF ingestion and chunking

Tests cover:
  - File validation (valid, wrong type, too large, bad magic bytes)
  - Text extraction result structure
  - Chunking: correct count, metadata, no empty chunks
  - Edge cases: empty page list, zero-length text
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdf_processor import validate_pdf, chunk_pages, make_doc_id, _slide_window
from config import MAX_UPLOAD_SIZE_BYTES


# ── validate_pdf ───────────────────────────────────────────────────────────────

class TestValidatePdf:
    def test_valid_pdf_bytes(self):
        # Minimal valid PDF header
        ok, msg = validate_pdf("test.pdf", b"%PDF-1.4 fake content")
        assert ok is True
        assert msg == ""

    def test_wrong_extension(self):
        ok, msg = validate_pdf("report.docx", b"%PDF-1.4 content")
        assert ok is False
        assert "docx" in msg.lower() or "pdf" in msg.lower()

    def test_no_extension(self):
        ok, msg = validate_pdf("report", b"%PDF-1.4")
        assert ok is False

    def test_too_large(self):
        big_bytes = b"%PDF-1.4" + b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)
        ok, msg = validate_pdf("big.pdf", big_bytes)
        assert ok is False
        assert "MB" in msg or "limit" in msg.lower()

    def test_bad_magic_bytes(self):
        ok, msg = validate_pdf("fake.pdf", b"Not a real PDF content here")
        assert ok is False
        assert "pdf" in msg.lower() or "header" in msg.lower()

    def test_exact_size_limit(self):
        # Exactly at limit — should be valid
        exact = b"%PDF-1.4" + b"x" * (MAX_UPLOAD_SIZE_BYTES - 8)
        ok, _ = validate_pdf("exact.pdf", exact)
        assert ok is True


# ── _slide_window ──────────────────────────────────────────────────────────────

class TestSlideWindow:
    def test_short_text_single_chunk(self):
        text = "Hello world"
        result = _slide_window(text, size=100, overlap=20)
        assert len(result) == 1
        assert result[0] == text

    def test_multiple_windows(self):
        text = "a" * 200
        result = _slide_window(text, size=100, overlap=20)
        # step = 100-20 = 80, so we need ceil(200/80) windows
        assert len(result) >= 2

    def test_overlap_content(self):
        text = "A" * 50 + "B" * 50
        result = _slide_window(text, size=60, overlap=20)
        # Second window should overlap with last 20 chars of first
        assert len(result) >= 2

    def test_no_empty_windows(self):
        text = "x" * 500
        result = _slide_window(text, size=100, overlap=30)
        assert all(len(w) > 0 for w in result)

    def test_exact_size_text(self):
        text = "a" * 100
        result = _slide_window(text, size=100, overlap=0)
        assert len(result) == 1


# ── chunk_pages ────────────────────────────────────────────────────────────────

class TestChunkPages:
    def _make_pages(self, texts):
        return [
            {"page_number": i + 1, "text": t, "char_count": len(t),
             "is_empty": len(t) == 0, "is_low_text": 0 < len(t) < 50}
            for i, t in enumerate(texts)
        ]

    def test_basic_chunking(self):
        pages = self._make_pages(["Hello world. " * 20])
        chunks = chunk_pages(pages, doc_id="abc123", filename="test.pdf",
                             chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 0

    def test_chunk_metadata(self):
        pages = self._make_pages(["Sample text " * 30])
        chunks = chunk_pages(pages, doc_id="docXYZ", filename="doc.pdf",
                             chunk_size=150, chunk_overlap=30)
        for c in chunks:
            assert c["doc_id"]   == "docXYZ"
            assert c["filename"] == "doc.pdf"
            assert c["page_number"] == 1
            assert len(c["text"]) > 0
            assert c["chunk_id"].startswith("docXYZ_")

    def test_no_empty_chunks(self):
        pages = self._make_pages(["Real text " * 50, "", "More text " * 20])
        chunks = chunk_pages(pages, doc_id="abc", filename="f.pdf",
                             chunk_size=200, chunk_overlap=40)
        assert all(c["text"].strip() != "" for c in chunks)

    def test_empty_pages_skipped(self):
        pages = self._make_pages(["", "", ""])
        chunks = chunk_pages(pages, doc_id="emp", filename="e.pdf")
        assert len(chunks) == 0

    def test_page_numbers_preserved(self):
        pages = self._make_pages(["Page one content " * 20, "Page two content " * 20])
        chunks = chunk_pages(pages, doc_id="pn", filename="pn.pdf",
                             chunk_size=100, chunk_overlap=10)
        page_nums = {c["page_number"] for c in chunks}
        assert 1 in page_nums
        assert 2 in page_nums

    def test_chunk_ids_unique(self):
        pages = self._make_pages(["Text " * 100])
        chunks = chunk_pages(pages, doc_id="uid", filename="u.pdf",
                             chunk_size=80, chunk_overlap=10)
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_sequential_chunk_seq(self):
        pages = self._make_pages(["Word " * 200])
        chunks = chunk_pages(pages, doc_id="sq", filename="s.pdf",
                             chunk_size=100, chunk_overlap=20)
        seqs = [c["chunk_seq"] for c in chunks]
        assert seqs == list(range(len(seqs)))


# ── make_doc_id ────────────────────────────────────────────────────────────────

class TestMakeDocId:
    def test_length(self):
        doc_id = make_doc_id("a" * 64)
        assert len(doc_id) == 16

    def test_deterministic(self):
        h = "abcdef1234567890" * 4
        assert make_doc_id(h) == make_doc_id(h)

    def test_different_hashes(self):
        assert make_doc_id("a" * 64) != make_doc_id("b" * 64)
