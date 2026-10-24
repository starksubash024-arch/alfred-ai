"""
utils.py - Shared helper utilities

Small, reusable functions used across modules.
Nothing AI-specific lives here — just general helpers.
"""

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any

from config import LOG_LEVEL

# ── Logging ───────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for a given module name."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)

logger = get_logger(__name__)

# ── File helpers ──────────────────────────────────────────────────────────────

def compute_file_hash(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of file bytes.
    Used to detect duplicate uploads without comparing filenames.
    """
    return hashlib.sha256(file_bytes).hexdigest()

def safe_filename(filename: str) -> str:
    """
    Sanitise a filename to prevent path traversal attacks.
    Keeps only alphanumerics, dots, hyphens, and underscores.
    """
    name = Path(filename).stem
    ext  = Path(filename).suffix
    safe = re.sub(r"[^\w\-.]", "_", name)
    return f"{safe}{ext}"

def human_readable_size(num_bytes: int) -> str:
    """Convert bytes to a human-readable string like '2.3 MB'."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

def format_duration(seconds: float) -> str:
    """Convert seconds to a readable duration string."""
    if seconds < 1:
        return f"{int(seconds * 1000)} ms"
    if seconds < 60:
        return f"{seconds:.1f} s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs}s"

# ── Text helpers ──────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Basic text cleaning:
    - Collapse multiple blank lines into one.
    - Strip leading/trailing whitespace from each line.
    - Normalise unicode whitespace.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    text  = "\n".join(lines)
    return text.strip()

def truncate_text(text: str, max_chars: int = 300, suffix: str = "…") -> str:
    """Truncate text to max_chars, appending suffix if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + suffix

def count_words(text: str) -> int:
    """Count the number of words in a text string."""
    return len(text.split())

# ── Timing ────────────────────────────────────────────────────────────────────

class Timer:
    """Simple context-manager timer. Use in a `with` block."""
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self._start

    @property
    def elapsed_str(self) -> str:
        return format_duration(self.elapsed)
