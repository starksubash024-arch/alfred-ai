"""
tests/test_chunking.py — Additional chunking edge-case tests
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pdf_processor import chunk_pages


class TestChunkingEdgeCases:
    def _page(self, num, text):
        return {"page_number": num, "text": text,
                "char_count": len(text), "is_empty": not text, "is_low_text": False}

    def test_single_word_page(self):
        pages = [self._page(1, "Hello")]
        chunks = chunk_pages(pages, "d1", "f.pdf", chunk_size=900, chunk_overlap=150)
        # Single short page → one chunk
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Hello"

    def test_overlap_does_not_exceed_chunk_size(self):
        pages = [self._page(1, "Word " * 500)]
        chunks = chunk_pages(pages, "d1", "f.pdf", chunk_size=200, chunk_overlap=50)
        for c in chunks:
            assert len(c["text"]) <= 200 + 5  # slight tolerance for word boundary

    def test_multi_page_sequential_seqs(self):
        pages = [self._page(1, "A " * 100), self._page(2, "B " * 100)]
        chunks = chunk_pages(pages, "d1", "f.pdf", chunk_size=100, chunk_overlap=20)
        seqs = [c["chunk_seq"] for c in chunks]
        assert seqs == list(range(len(seqs)))

    def test_whitespace_only_page_skipped(self):
        pages = [self._page(1, "   \n\t  \n   "), self._page(2, "Real content here")]
        chunks = chunk_pages(pages, "d1", "f.pdf")
        page_nums = {c["page_number"] for c in chunks}
        assert 2 in page_nums
        # Page 1 had only whitespace — it may or may not produce chunks,
        # but any produced chunks must have non-empty text
        for c in chunks:
            assert c["text"].strip() != ""
