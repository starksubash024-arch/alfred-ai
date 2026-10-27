"""
components/metric_cards.py — Aurora Mint Data Metric Cards for ALFRED AI
Distinctive semantic color allocation:
  - Documents: Deep Jade & Fresh Mint (Hero Card)
  - Pages: Clear Sky Blue with Trend Wave
  - Chunks: Soft Violet with Vector Cluster
  - Questions: Fresh Emerald with Confidence Arc
"""

import streamlit as st


def render_kpi_cards(stats: dict) -> None:
    """Render the four distinctive Aurora Mint metric cards."""
    doc_count   = stats.get("doc_count", 0)
    page_total  = stats.get("page_total", 0)
    chunk_total = stats.get("chunk_total", 0)
    query_count = stats.get("query_count", 0)

    doc_sub   = "No documents yet" if doc_count == 0 else f"{doc_count} active files in corpus"
    page_sub  = "No pages processed" if page_total == 0 else f"{page_total} pages extracted"
    chunk_sub = "No chunks indexed" if chunk_total == 0 else f"{chunk_total} embedded vectors"
    query_sub = "This workspace session"

    cards_html = f"""<div class="metrics-row">
<!-- Card 1: Documents Uploaded (Vibrant Fresh Mint Hero Card) -->
<div class="metric-box card-mint-hero">
    <div class="metric-header">
        <div class="metric-header-left">
            <div class="metric-icon-circle">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
            </div>
            <span class="metric-label">Documents</span>
        </div>
        <div style="width:26px; height:26px; border-radius:50%; background:rgba(10,58,50,0.14); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; color:#0A3A32;">↗</div>
    </div>
    <div class="metric-value">{doc_count:,}</div>
    <div class="metric-footer-row">
        <span class="metric-pill-chip">Corpus Active ↗</span>
        <span class="metric-footnote">{doc_sub}</span>
    </div>
</div>

<!-- Card 2: Total Pages Processed (Clear Sky Blue Card with Sparkline) -->
<div class="metric-box card-sky-blue">
    <div class="metric-header">
        <div class="metric-header-left">
            <div class="metric-icon-circle">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                    <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                    <line x1="9" y1="12" x2="15" y2="12"></line>
                    <line x1="9" y1="16" x2="15" y2="16"></line>
                </svg>
            </div>
            <span class="metric-label">Total Pages</span>
        </div>
        <span class="metric-pill-chip blue">Extracted</span>
    </div>
    <div class="metric-value">{page_total:,}</div>
    <div class="metric-footer-row">
        <span class="metric-footnote">{page_sub}</span>
        <svg width="70" height="20" viewBox="0 0 70 20" fill="none" style="flex-shrink:0;">
            <path d="M2 16 Q 18 18, 30 10 T 52 8 T 68 3" stroke="#65B8F5" stroke-width="2" fill="none" stroke-linecap="round"/>
            <circle cx="68" cy="3" r="2.5" fill="#65B8F5"/>
        </svg>
    </div>
</div>

<!-- Card 3: Indexed Text Chunks (Soft Violet Card with Vector Cluster) -->
<div class="metric-box card-violet">
    <div class="metric-header">
        <div class="metric-header-left">
            <div class="metric-icon-circle">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
            </div>
            <span class="metric-label">Indexed Chunks</span>
        </div>
        <span class="metric-pill-chip violet">384-dim</span>
    </div>
    <div class="metric-value">{chunk_total:,}</div>
    <div class="metric-footer-row">
        <span class="metric-footnote">{chunk_sub}</span>
        <svg width="60" height="20" viewBox="0 0 60 20" fill="none" style="flex-shrink:0;">
            <rect x="4" y="10" width="8" height="8" rx="2" fill="#A99AF7" fill-opacity="0.4"/>
            <rect x="18" y="6" width="8" height="12" rx="2" fill="#A99AF7" fill-opacity="0.65"/>
            <rect x="32" y="3" width="8" height="15" rx="2" fill="#A99AF7"/>
            <rect x="46" y="8" width="8" height="10" rx="2" fill="#A99AF7" fill-opacity="0.5"/>
        </svg>
    </div>
</div>

<!-- Card 4: Questions Asked (Fresh Emerald Card with Confidence Arc) -->
<div class="metric-box card-emerald">
    <div class="metric-header">
        <div class="metric-header-left">
            <div class="metric-icon-circle">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </div>
            <span class="metric-label">Questions</span>
        </div>
        <span class="metric-pill-chip emerald">RAG Ready</span>
    </div>
    <div class="metric-value">{query_count:,}</div>
    <div class="metric-footer-row">
        <span class="metric-footnote">{query_sub}</span>
        <svg width="40" height="20" viewBox="0 0 40 20" fill="none" style="flex-shrink:0;">
            <path d="M 5 18 A 15 15 0 0 1 35 18" stroke="#D3E3D8" stroke-width="3" stroke-linecap="round"/>
            <path d="M 5 18 A 15 15 0 0 1 29 7" stroke="#32B985" stroke-width="3" stroke-linecap="round"/>
        </svg>
    </div>
</div>
</div>"""

    st.markdown(cards_html, unsafe_allow_html=True)
