"""
summarizer.py — Document summarisation using map-reduce

For long documents, sends chunks in small batches to the LLM (map step),
then combines the partial summaries into a final summary (reduce step).

Output sections:
  - executive_summary
  - key_takeaways (list)
  - main_topics (list)
  - important_definitions (list)
  - dates_and_figures (list)
  - action_items (list)
  - concise_summary (short paragraph)
  - source_pages (list of page numbers referenced)
"""

import json
import time
from typing import Optional

import requests

from config import MAX_CHUNKS_FOR_SUMMARY, OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT
from utils import get_logger, truncate_text

logger = get_logger(__name__)


# ── Prompt templates ───────────────────────────────────────────────────────────

_MAP_PROMPT = """\
You are a document analyst. Read the following excerpt from a document and \
extract only what is explicitly stated. Do NOT add information from outside the text.

Document excerpt (pages {pages}):
---
{text}
---

Provide a JSON object with these keys:
  "summary": short paragraph summarising this excerpt,
  "key_points": list of up to 5 important points (verbatim or close paraphrase),
  "topics": list of main topics mentioned,
  "definitions": list of {{"term": "...", "definition": "..."}} pairs,
  "dates_figures": list of important dates or numeric facts,
  "action_items": list of recommendations or action items (only if explicitly present)

Return ONLY valid JSON, no prose outside the JSON block.
"""

_REDUCE_PROMPT = """\
You are a document analyst. Combine the following partial summaries of different \
sections of the same document into a single coherent summary. \
Do NOT introduce information not present in the partial summaries.

Partial summaries (JSON):
{partials}

Produce a final JSON object with:
  "executive_summary": 2–4 sentence overview,
  "concise_summary": 1 sentence,
  "key_takeaways": list of up to 8 key points,
  "main_topics": list of main topics,
  "important_definitions": list of {{"term": "...", "definition": "..."}} pairs,
  "dates_and_figures": list of important dates or numeric facts,
  "action_items": list of recommendations (only if present in source material)

Return ONLY valid JSON.
"""


# ── LLM helper ─────────────────────────────────────────────────────────────────

def _call_llm(prompt: str, model: str = OLLAMA_MODEL) -> Optional[str]:
    """Send a prompt to Ollama and return the text response, or None on error."""
    payload = {
        "model":  model,
        "stream": False,
        "options": {"temperature": 0.1},
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return None


def _parse_json(text: str) -> dict:
    """Extract and parse a JSON block from LLM output."""
    # Try to find a JSON block between ``` markers
    import re
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    # Otherwise try to parse the whole string
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: find first { … } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


# ── Map step ───────────────────────────────────────────────────────────────────

def _map_chunk_batch(chunks: list[dict], model: str) -> Optional[dict]:
    """Summarise a single batch of chunks (map step)."""
    text  = "\n\n".join(c["text"] for c in chunks)
    pages = sorted({c["page_number"] for c in chunks})
    page_str = ", ".join(str(p) for p in pages)

    prompt   = _MAP_PROMPT.format(text=text, pages=page_str)
    response = _call_llm(prompt, model)
    if not response:
        return None

    result = _parse_json(response)
    result["source_pages"] = pages
    return result


# ── Reduce step ────────────────────────────────────────────────────────────────

def _reduce_partials(partials: list[dict], model: str) -> dict:
    """Combine multiple partial summaries into one final summary (reduce step)."""
    partials_json = json.dumps(partials, ensure_ascii=False, indent=2)
    prompt        = _REDUCE_PROMPT.format(partials=partials_json)
    response      = _call_llm(prompt, model)
    if not response:
        return {}
    return _parse_json(response)


# ── Public API ─────────────────────────────────────────────────────────────────

def summarise_document(
    chunks: list[dict],
    model: str = OLLAMA_MODEL,
    batch_size: int = 6,
) -> dict:
    """
    Summarise a document using map-reduce.

    Args:
        chunks:     All text chunks for the document (from DB or vector store).
        model:      Ollama model name.
        batch_size: Number of chunks per map call (keep small for local models).

    Returns:
        Summary dict with keys:
          executive_summary, concise_summary, key_takeaways, main_topics,
          important_definitions, dates_and_figures, action_items,
          source_pages, error (None on success)
    """
    if not chunks:
        return {"error": "No text chunks available for summarisation."}

    # Use at most MAX_CHUNKS_FOR_SUMMARY chunks to avoid very long runs
    working_chunks = chunks[:MAX_CHUNKS_FOR_SUMMARY]
    logger.info(
        "Summarising %d chunks (of %d total) in batches of %d",
        len(working_chunks), len(chunks), batch_size,
    )

    # ── Map ────────────────────────────────────────────────────────────────────
    partials = []
    for i in range(0, len(working_chunks), batch_size):
        batch   = working_chunks[i : i + batch_size]
        partial = _map_chunk_batch(batch, model)
        if partial:
            partials.append(partial)
        else:
            logger.warning("Map batch %d returned no result.", i // batch_size)

    if not partials:
        return {"error": "Summarisation failed — Ollama returned no output. Is it running?"}

    # ── Reduce ─────────────────────────────────────────────────────────────────
    if len(partials) == 1:
        final = partials[0]
    else:
        final = _reduce_partials(partials, model)

    # Collect all source pages
    all_pages = sorted({
        p
        for partial in partials
        for p in partial.get("source_pages", [])
    })

    return {
        "executive_summary":     final.get("executive_summary") or final.get("summary", ""),
        "concise_summary":       final.get("concise_summary", ""),
        "key_takeaways":         final.get("key_takeaways") or final.get("key_points", []),
        "main_topics":           final.get("main_topics", []),
        "important_definitions": final.get("important_definitions") or final.get("definitions", []),
        "dates_and_figures":     final.get("dates_and_figures") or final.get("dates_figures", []),
        "action_items":          final.get("action_items", []),
        "source_pages":          all_pages,
        "chunk_count_used":      len(working_chunks),
        "total_chunks":          len(chunks),
        "error":                 None,
    }
