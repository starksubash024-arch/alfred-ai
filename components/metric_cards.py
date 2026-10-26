"""
components/metric_cards.py — Renders the four multicolored metric cards matching NEMESIS reference design
"""

import streamlit as st


def render_kpi_cards(stats: dict) -> None:
    """Render the four multicolored metric cards."""
    doc_count   = stats.get("doc_count", 0)
    page_total  = stats.get("page_total", 0)
    chunk_total = stats.get("chunk_total", 0)
    query_count = stats.get("query_count", 0)

    doc_sub   = "No documents yet" if doc_count == 0 else f"{doc_count} active files"
    page_sub  = "No pages processed" if page_total == 0 else f"{page_total} pages indexed"
    chunk_sub = "No chunks indexed" if chunk_total == 0 else f"{chunk_total} text chunks"
    query_sub = "This session"

    cards_html = f"""<div class="metrics-row">
<div class="metric-box card-crimson">
<div class="metric-header">
<div class="metric-icon-circle">📄</div>
<span class="metric-label">Documents Uploaded</span>
</div>
<div class="metric-value">{doc_count:,}</div>
<div class="metric-footnote">{doc_sub}</div>
</div>

<div class="metric-box card-blue">
<div class="metric-header">
<div class="metric-icon-circle">📃</div>
<span class="metric-label">Total Pages Processed</span>
</div>
<div class="metric-value">{page_total:,}</div>
<div class="metric-footnote">{page_sub}</div>
</div>

<div class="metric-box card-violet">
<div class="metric-header">
<div class="metric-icon-circle">🧩</div>
<span class="metric-label">Indexed Text Chunks</span>
</div>
<div class="metric-value">{chunk_total:,}</div>
<div class="metric-footnote">{chunk_sub}</div>
</div>

<div class="metric-box card-teal">
<div class="metric-header">
<div class="metric-icon-circle">💬</div>
<span class="metric-label">Questions Asked</span>
</div>
<div class="metric-value">{query_count:,}</div>
<div class="metric-footnote">{query_sub}</div>
</div>
</div>"""

    st.markdown(cards_html, unsafe_allow_html=True)
