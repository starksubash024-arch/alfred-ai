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
        "format": "json",
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
    if not text:
        return {}
    import re
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Try finding outer-most braces { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass
    return {}


# ── Extractive Fallback Summarizer ──────────────────────────────────────────────

def generate_extractive_summary(chunks: list[dict], filename: str = "") -> dict:
    """
    Extract structured summaries directly from text chunks using NLP heuristics.
    Used when Ollama is offline or as a fast, instant summarisation mode.
    Guaranteed to succeed and never fail with connection timeouts.
    """
    import re

    if not chunks:
        return {"error": "No text chunks available for summarisation."}

    all_pages = sorted({c.get("page_number", 1) for c in chunks})
    
    # Collect sentences with page provenance
    sentences_with_page = []
    for c in chunks:
        p_num = c.get("page_number", 1)
        raw_sentences = re.split(r'(?<=[.!?])\s+', c.get("text", ""))
        for s in raw_sentences:
            cleaned_s = s.strip()
            if len(cleaned_s) > 30:  # meaningful sentence
                sentences_with_page.append((cleaned_s, p_num))

    # 1. Executive Summary: First few substantial sentences from early pages
    early_sentences = [s for s, p in sentences_with_page if p <= min(all_pages) + 2]
    if early_sentences:
        exec_summary = " ".join(early_sentences[:4])
    else:
        exec_summary = " ".join([s for s, _ in sentences_with_page[:3]])

    # 2. Key Takeaways
    key_takeaways = []
    seen_takeaways = set()
    for s, p in sentences_with_page:
        lower = s.lower()
        if any(marker in lower for marker in ["significant", "conclude", "result", "important", "major", "objective", "purpose", "shows that"]):
            if s not in seen_takeaways and len(key_takeaways) < 8:
                key_takeaways.append(f"{s} (Page {p})")
                seen_takeaways.add(s)

    if len(key_takeaways) < 3:
        # Sample well-spaced sentences across the document
        step = max(1, len(sentences_with_page) // 6)
        for i in range(0, len(sentences_with_page), step):
            s, p = sentences_with_page[i]
            if s not in seen_takeaways and len(key_takeaways) < 6:
                key_takeaways.append(f"{s} (Page {p})")
                seen_takeaways.add(s)

    # 3. Main Topics (from headers or frequent nouns)
    topics = []
    seen_topics = set()
    for c in chunks:
        lines = c.get("text", "").split("\n")
        for line in lines:
            line_s = line.strip()
            # Likely header: short, capitalized, no period
            if 4 < len(line_s) < 60 and not line_s.endswith(".") and not line_s.startswith("http"):
                clean_top = re.sub(r'^[0-9.\-\s]+', '', line_s)
                if clean_top and clean_top not in seen_topics and len(clean_top.split()) <= 6:
                    topics.append(clean_top)
                    seen_topics.add(clean_top)
                    if len(topics) >= 6:
                        break
        if len(topics) >= 6:
            break

    if not topics:
        topics = ["Document Content", "Core Principles", "Analysis & Findings"]

    # 4. Important Definitions
    definitions = []
    def_patterns = [
        r'([A-Z][a-zA-Z\s]{2,30})\s+(?:is defined as|refers to|means|is described as)\s+([^.]+)',
        r'([A-Z][a-zA-Z\s]{2,30})\s*:\s*([A-Z][^.]+)',
    ]
    for s, p in sentences_with_page:
        for pat in def_patterns:
            m = re.search(pat, s)
            if m:
                term = m.group(1).strip()
                defi = m.group(2).strip()
                if len(term) < 40 and len(defi) > 15:
                    definitions.append({"term": term, "definition": f"{defi}. (Page {p})"})
                    if len(definitions) >= 5:
                        break
        if len(definitions) >= 5:
            break

    # 5. Dates & Figures
    dates_and_figures = []
    seen_df = set()
    num_pattern = re.compile(r'\b(?:\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:\.\d+)?|\b(?:19|20)\d{2}\b|\bQ[1-4]\b|\b\d+\s*(?:crore|lakh|million|billion|units|marks|hours)\b)', re.IGNORECASE)
    for s, p in sentences_with_page:
        matches = num_pattern.findall(s)
        if matches:
            for match in matches:
                item_str = f"'{match}' — {truncate_text(s, 140)} (Page {p})"
                if item_str not in seen_df:
                    dates_and_figures.append(item_str)
                    seen_df.add(item_str)
                    if len(dates_and_figures) >= 6:
                        break
        if len(dates_and_figures) >= 6:
            break

    # 6. Action Items / Recommendations
    action_items = []
    for s, p in sentences_with_page:
        lower = s.lower()
        if any(w in lower for w in ["recommend", "should", "must", "action item", "ensure", "advised to"]):
            action_items.append(f"{s} (Page {p})")
            if len(action_items) >= 5:
                break

    # 7. Concise Summary
    first_sentence = sentences_with_page[0][0] if sentences_with_page else "Document overview."
    concise = f"{filename or 'This document'} covers {len(all_pages)} pages addressing {', '.join(topics[:3])}."

    return {
        "executive_summary":     exec_summary,
        "concise_summary":       concise,
        "key_takeaways":         key_takeaways,
        "main_topics":           topics,
        "important_definitions": definitions,
        "dates_and_figures":     dates_and_figures,
        "action_items":          action_items,
        "source_pages":          all_pages,
        "chunk_count_used":      len(chunks),
        "total_chunks":          len(chunks),
        "mode":                  "extractive",
        "error":                 None,
    }


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
        logger.info("Ollama returned no partials; falling back to extractive summary.")
        fallback = generate_extractive_summary(chunks)
        fallback["mode"] = "extractive_fallback"
        return fallback

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
