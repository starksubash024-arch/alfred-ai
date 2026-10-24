"""
config.py - Application configuration

Loads settings from environment variables (or .env file).
Every configurable value in the app comes from here,
so you only need to change one file to adjust behaviour.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (safe to call even if file is missing)
load_dotenv()

# ── Project root ──────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.resolve()

# ── App identity ──────────────────────────────────────────────────────────────
APP_NAME = os.getenv("APP_NAME", "RAG Document Assistant")
APP_TAGLINE = "Your documents. One intelligent workspace."
APP_VERSION = "1.0.0"

# ── Ollama / LLM ─────────────────────────────────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ── Storage ───────────────────────────────────────────────────────────────────
UPLOAD_DIR = ROOT_DIR / os.getenv("UPLOAD_DIR", "data/uploads")
INDEX_DIR  = ROOT_DIR / os.getenv("INDEX_DIR",  "data/indexes")
DB_PATH    = ROOT_DIR / os.getenv("DB_PATH",    "data/rag_assistant.db")

# Ensure directories exist at import time
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Upload limits ─────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf"}

# ── Chunking ──────────────────────────────────────────────────────────────────
DEFAULT_CHUNK_SIZE    = int(os.getenv("DEFAULT_CHUNK_SIZE", "900"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "150"))

# ── Retrieval ─────────────────────────────────────────────────────────────────
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM   = 384   # dimension for all-MiniLM-L6-v2

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Summarization ─────────────────────────────────────────────────────────────
MAX_CHUNKS_FOR_SUMMARY = 20   # max chunks sent per summarization call
SUMMARY_CHUNK_SIZE     = 1500 # characters per summary chunk (map step)
