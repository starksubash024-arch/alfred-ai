"""
llm_service.py — Ollama local LLM integration

Handles:
  1. Checking Ollama server availability.
  2. Listing available models.
  3. Generating grounded answers using retrieved context.
  4. Streaming responses (optional).

Important rules (enforced in the system prompt):
  - Answer only from supplied passages; no hallucination.
  - Say explicitly if the answer isn't in the sources.
  - Use [S1], [S2] citation labels that map to real chunks.
  - Never fabricate filenames, page numbers, or quotations.
"""

import json
import time
from typing import Optional

import requests

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT
from utils import get_logger

logger = get_logger(__name__)

# ── Connectivity ───────────────────────────────────────────────────────────────

def check_ollama() -> dict:
    """
    Test whether the Ollama server is reachable.

    Returns:
        {"available": bool, "models": list[str], "error": str}
    """
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        data   = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return {"available": True, "models": models, "error": ""}
    except requests.ConnectionError:
        return {
            "available": False,
            "models": [],
            "error": (
                "Cannot reach Ollama at {host}. "
                "Make sure Ollama is installed and running.\n\n"
                "Install: https://ollama.com/download\n"
                "Then run: ollama pull {model}"
            ).format(host=OLLAMA_HOST, model=OLLAMA_MODEL),
        }
    except Exception as exc:
        return {"available": False, "models": [], "error": str(exc)}


def model_is_available(model_name: str = OLLAMA_MODEL) -> bool:
    """Return True if the requested model is in the local Ollama model list."""
    status = check_ollama()
    if not status["available"]:
        return False
    return any(model_name in m for m in status["models"])


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a precise document-analysis assistant. Answer questions using ONLY \
the provided document passages below.

Rules you must follow:
1. Base every claim strictly on the supplied passages. Do not add outside knowledge.
2. Cite sources with labels [S1], [S2], etc., where each label refers to the \
   numbered passage in the context block.
3. If the passages do not contain enough information to answer the question, \
   say exactly: "The information needed to answer this question was not found \
   in the provided document sections."
4. If passages contain conflicting information, state the conflict clearly \
   instead of picking one arbitrarily.
5. Clearly distinguish between direct evidence from the text and your \
   logical inference from that evidence.
6. Never fabricate filenames, page numbers, quotations, or citations.
7. Keep the answer concise but complete. Use bullet points for lists.
"""

# ── Context builder ────────────────────────────────────────────────────────────

def build_context(chunks: list[dict], max_chars: int = 6000) -> tuple[str, list[dict]]:
    """
    Format retrieved chunks into a numbered context block for the LLM prompt.

    Respects a character budget so the combined context stays within the
    local model's context window (rough heuristic: 6000 chars ≈ ~1500 tokens).

    Returns:
        (context_text, used_chunks) — only the chunks that fit in the budget.
    """
    used   = []
    parts  = []
    budget = max_chars

    for i, chunk in enumerate(chunks, 1):
        entry = (
            f"[S{i}] Source: {chunk['filename']}, Page {chunk['page_number']}\n"
            f"{chunk['text']}\n"
        )
        if len(entry) > budget:
            break
        parts.append(entry)
        used.append(chunk)
        budget -= len(entry)

    context_text = "\n---\n".join(parts)
    return context_text, used


# ── Answer generation ──────────────────────────────────────────────────────────

def generate_answer(
    question: str,
    chunks: list[dict],
    model: str = OLLAMA_MODEL,
    temperature: float = 0.1,
    stream: bool = False,
) -> dict:
    """
    Generate a grounded answer from the given retrieved chunks.

    Args:
        question:    The user's question.
        chunks:      Retrieved chunks from vector search (with metadata).
        model:       Ollama model name to use.
        temperature: Sampling temperature (low = more factual).
        stream:      If True, yield tokens incrementally (not yet wired to UI).

    Returns:
        {
            "answer":      str,
            "used_chunks": list[dict],   # chunks actually used in context
            "model":       str,
            "duration_ms": int,
            "error":       str or None,
        }
    """
    if not chunks:
        return {
            "answer": (
                "No relevant passages were found in the indexed documents "
                "for your question. Please try rephrasing, or upload a document "
                "that covers this topic."
            ),
            "used_chunks": [],
            "model": model,
            "duration_ms": 0,
            "error": None,
        }

    context_text, used_chunks = build_context(chunks)

    user_message = (
        f"Document passages:\n\n{context_text}\n\n"
        f"Question: {question}\n\n"
        f"Answer (cite sources as [S1], [S2], etc.):"
    )

    payload = {
        "model":  model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    }

    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data   = resp.json()
        answer = data["message"]["content"].strip()
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "answer":      answer,
            "used_chunks": used_chunks,
            "model":       model,
            "duration_ms": elapsed_ms,
            "error":       None,
        }
    except requests.ConnectionError:
        return {
            "answer": "",
            "used_chunks": used_chunks,
            "model": model,
            "duration_ms": 0,
            "error": (
                "Could not connect to Ollama. "
                "Ensure Ollama is running: `ollama serve`"
            ),
        }
    except requests.Timeout:
        return {
            "answer": "",
            "used_chunks": used_chunks,
            "model": model,
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "error": (
                f"Ollama timed out after {OLLAMA_TIMEOUT}s. "
                "The model may still be loading. Try again in a moment."
            ),
        }
    except Exception as exc:
        logger.exception("LLM generation failed")
        return {
            "answer": "",
            "used_chunks": used_chunks,
            "model": model,
            "duration_ms": 0,
            "error": f"LLM error: {exc}",
        }
