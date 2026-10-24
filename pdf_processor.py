"""
pdf_processor.py — PDF ingestion and text extraction

Uses PyMuPDF (fitz) to:
  1. Open and validate a PDF file.
  2. Extract text page-by-page.
  3. Detect empty / scanned pages.
  4. Return structured page data with metadata.
  5. Split pages into overlapping text chunks.

Key design decisions
  - Page numbers are 1-based throughout (matches what users see in a PDF reader).
  - Chunks carry full provenance: doc_id, filename, page, sequence number.
  - Empty chunks are dropped; very short chunks are flagged but kept.
"""

import hashlib
import time
from pathlib import Path
from typing import Optional

from config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    MAX_UPLOAD_SIZE_BYTES,
)
from utils import Timer, clean_text, compute_file_hash, get_logger, safe_filename

logger = get_logger(__name__)

# Minimum characters on a page before we flag it as "low text"
LOW_TEXT_THRESHOLD = 50


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_pdf(filename: str, file_bytes: bytes) -> tuple[bool, str]:
    """
    Check that an uploaded file is a valid PDF within size limits.

    Returns:
        (True, "")          — file is valid
        (False, reason)     — file is invalid; reason explains why
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Only PDF files are accepted. Received: {ext or 'no extension'}"

    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        mb = len(file_bytes) / (1024 * 1024)
        return False, (
            f"File is {mb:.1f} MB, which exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB limit."
        )

    # Check PDF magic bytes: must start with %PDF
    if not file_bytes.startswith(b"%PDF"):
        return False, "File does not appear to be a valid PDF (missing PDF header)."

    return True, ""


# ── Extraction ─────────────────────────────────────────────────────────────────

def extract_pages(file_bytes: bytes, filename: str) -> dict:
    """
    Open a PDF from bytes and extract text from every page.

    Returns a dict with:
        - success (bool)
        - filename, file_hash, file_size
        - page_count
        - pages: list of {page_number, text, char_count, is_empty, is_low_text}
        - warnings: list of human-readable warning strings
        - error (str or None)
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {
            "success": False,
            "error": "PyMuPDF is not installed. Run: pip install PyMuPDF",
        }

    result = {
        "success": True,
        "filename": safe_filename(filename),
        "original_filename": filename,
        "file_hash": compute_file_hash(file_bytes),
        "file_size": len(file_bytes),
        "page_count": 0,
        "pages": [],
        "warnings": [],
        "error": None,
    }

    try:
        with Timer() as t:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            result["page_count"] = len(doc)

            empty_pages = []
            low_text_pages = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                raw_text = page.get_text("text")          # plain text
                cleaned  = clean_text(raw_text)
                char_count = len(cleaned)
                one_based  = page_num + 1                 # 1-based page numbers

                is_empty    = char_count == 0
                is_low_text = 0 < char_count < LOW_TEXT_THRESHOLD

                if is_empty:
                    empty_pages.append(one_based)
                elif is_low_text:
                    low_text_pages.append(one_based)

                result["pages"].append({
                    "page_number": one_based,
                    "text":        cleaned,
                    "char_count":  char_count,
                    "is_empty":    is_empty,
                    "is_low_text": is_low_text,
                })

            doc.close()

        result["processing_ms"] = int(t.elapsed * 1000)

        # Build warnings
        if empty_pages:
            result["warnings"].append(
                f"Pages with no text detected (possibly blank or image-only): "
                f"{_format_page_list(empty_pages)}"
            )
        if low_text_pages:
            result["warnings"].append(
                f"Pages with very little text (may be partially scanned): "
                f"{_format_page_list(low_text_pages)}"
            )

        total_chars = sum(p["char_count"] for p in result["pages"])
        if total_chars == 0:
            result["warnings"].append(
                "No readable text found in this PDF. "
                "It may be a scanned image-only document. "
                "OCR (e.g. Tesseract) would be required to extract text from scanned PDFs."
            )
            result["success"] = False
            result["error"] = "No extractable text found."

    except Exception as exc:
        logger.exception("Failed to extract PDF: %s", filename)
        result["success"] = False
        result["error"] = f"Could not read PDF: {exc}"

    return result


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_pages(
    pages: list[dict],
    doc_id: str,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    """
    Split extracted page texts into overlapping chunks.

    Strategy
    ---------
    For each page:
      1. If the page text fits in one chunk, emit it as-is.
      2. Otherwise slide a window of `chunk_size` characters with
         `chunk_overlap` characters of back-overlap.

    Each chunk record carries:
        chunk_id, doc_id, filename, page_number,
        chunk_seq (global counter), text, char_count

    Empty or whitespace-only chunks are skipped.
    """
    chunks = []
    seq    = 0

    for page in pages:
        text = page["text"]
        if not text.strip():
            continue  # skip blank pages

        page_num = page["page_number"]
        page_chunks = _slide_window(text, chunk_size, chunk_overlap)

        for part in page_chunks:
            part = part.strip()
            if not part:
                continue
            chunk_id = f"{doc_id}_{seq:05d}"
            chunks.append({
                "chunk_id":    chunk_id,
                "doc_id":      doc_id,
                "filename":    filename,
                "page_number": page_num,
                "chunk_seq":   seq,
                "text":        part,
                "char_count":  len(part),
            })
            seq += 1

    logger.info(
        "Chunked '%s': %d pages → %d chunks (size=%d, overlap=%d)",
        filename, len(pages), len(chunks), chunk_size, chunk_overlap,
    )
    return chunks


def _slide_window(text: str, size: int, overlap: int) -> list[str]:
    """Return list of overlapping text windows from a string."""
    if len(text) <= size:
        return [text]

    step   = size - overlap
    start  = 0
    result = []
    while start < len(text):
        end = start + size
        result.append(text[start:end])
        start += step
    return result


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_page_list(pages: list[int]) -> str:
    """Format a list of page numbers as a compact string, e.g. '1, 3-5, 8'."""
    if not pages:
        return ""
    pages = sorted(pages)
    ranges = []
    start = end = pages[0]
    for p in pages[1:]:
        if p == end + 1:
            end = p
        else:
            ranges.append(str(start) if start == end else f"{start}–{end}")
            start = end = p
    ranges.append(str(start) if start == end else f"{start}–{end}")
    return ", ".join(ranges)


def make_doc_id(file_hash: str) -> str:
    """Create a short document ID from the full content hash."""
    return file_hash[:16]
