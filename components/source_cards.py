"""
components/source_cards.py — Source citation rendering for chat answers
"""

import streamlit as st
from utils import truncate_text


def render_source_cards(chunks: list[dict]) -> None:
    """
    Render expandable source cards below a chat answer.

    Each card shows:
      - Citation label [S1], [S2], …
      - Filename and page number
      - Cosine similarity retrieval score (labelled clearly — not a probability)
      - Truncated text snippet
    """
    if not chunks:
        return

    st.markdown("**📎 Sources used:**")

    for i, chunk in enumerate(chunks, 1):
        score   = chunk.get("score", 0.0)
        page    = chunk.get("page_number", "?")
        fname   = chunk.get("filename", "Unknown")
        snippet = truncate_text(chunk.get("text", ""), max_chars=300)

        with st.expander(
            f"[S{i}] {fname} — Page {page}  ·  retrieval score {score:.3f}",
            expanded=False,
        ):
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-card-header">
                        <span class="source-label">[S{i}]</span>
                        <span class="source-score">retrieval score: {score:.3f}</span>
                    </div>
                    <div class="source-filename">📄 {fname}</div>
                    <div class="source-page">Page {page}</div>
                    <div class="source-snippet">{snippet}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(
                "ℹ️ The retrieval score measures how closely this passage matched "
                "your query embedding. It is not a measure of factual correctness."
            )
