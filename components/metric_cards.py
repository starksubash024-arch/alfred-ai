"""
components/metric_cards.py — Signature Edition Data Metric Cards for ALFRED AI
Distinctive semantic color allocation: Crimson, Cyan, Violet, Emerald
"""

import streamlit as st


def render_kpi_cards(stats: dict) -> None:
    """Render the four signature metric cards with distinctive semantic coloring."""
    doc_count   = stats.get("doc_count", 0)
    page_total  = stats.get("page_total", 0)
    chunk_total = stats.get("chunk_total", 0)
    query_count = stats.get("query_count", 0)

    doc_sub   = "No documents yet" if doc_count == 0 else f"{doc_count} active files in corpus"
    page_sub  = "No pages processed" if page_total == 0 else f"{page_total} pages extracted"
    chunk_sub = "No chunks indexed" if chunk_total == 0 else f"{chunk_total} embedded vectors"
    query_sub = "This session"

    cards_html = f"""<div class="metrics-row">
<div class="metric-box card-crimson">
<div class="metric-header">
<div class="metric-icon-circle">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
<polyline points="14 2 14 8 20 8"></polyline>
<line x1="16" y1="13" x2="8" y2="13"></line>
<line x1="16" y1="17" x2="8" y2="17"></line>
</svg>
</div>
<span class="metric-label">Documents Uploaded</span>
</div>
<div class="metric-value">{doc_count:,}</div>
<div class="metric-footnote">{doc_sub}</div>
</div>

<div class="metric-box card-cyan">
<div class="metric-header">
<div class="metric-icon-circle">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
<rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
<line x1="9" y1="12" x2="15" y2="12"></line>
<line x1="9" y1="16" x2="15" y2="16"></line>
</svg>
</div>
<span class="metric-label">Total Pages Processed</span>
</div>
<div class="metric-value">{page_total:,}</div>
<div class="metric-footnote">{page_sub}</div>
</div>

<div class="metric-box card-violet">
<div class="metric-header">
<div class="metric-icon-circle">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
<polyline points="2 17 12 22 22 17"></polyline>
<polyline points="2 12 12 17 22 12"></polyline>
</svg>
</div>
<span class="metric-label">Indexed Text Chunks</span>
</div>
<div class="metric-value">{chunk_total:,}</div>
<div class="metric-footnote">{chunk_sub}</div>
</div>

<div class="metric-box card-emerald">
<div class="metric-header">
<div class="metric-icon-circle">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
</svg>
</div>
<span class="metric-label">Questions Asked</span>
</div>
<div class="metric-value">{query_count:,}</div>
<div class="metric-footnote">{query_sub}</div>
</div>
</div>"""

    st.markdown(cards_html, unsafe_allow_html=True)
