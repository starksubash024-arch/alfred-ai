"""
components/sidebar.py — Persistent sidebar rendered on every page

Displays:
  - Logo and product name
  - Navigation links (handled by Streamlit's multipage routing)
  - Ollama connection status (live check)
  - Indexed document count and chunk count
  - Recent activity summary
"""

import streamlit as st
from datetime import datetime

import database as db
from llm_service import check_ollama
from config import APP_NAME, APP_TAGLINE, OLLAMA_MODEL


def _load_css() -> None:
    """Inject the custom CSS once per session."""
    css_path = "styles/custom.css"
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass  # gracefully skip if missing during first run


def render_sidebar() -> None:
    """Render the sidebar. Call at the top of every page."""
    _load_css()

    with st.sidebar:
        # ── Logo ───────────────────────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-logo">'
            '<span class="sidebar-logo-icon">🧠</span>'
            '<div class="sidebar-logo-text">'
            '<span class="sidebar-logo-name">RAG Document Assistant</span>'
            '<span class="sidebar-logo-tagline">Your documents. One intelligent workspace.</span>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Navigation ─────────────────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-section-header">Navigation</div>',
            unsafe_allow_html=True,
        )
        st.page_link("app.py",              label="🏠  Dashboard",         )
        st.page_link("pages/1_Chat.py",     label="💬  Chat with Documents")
        st.page_link("pages/2_Documents.py",label="📚  Document Library"   )
        st.page_link("pages/3_Summaries.py",label="📝  Summaries"          )
        st.page_link("pages/4_Analytics.py",label="📊  Analytics"          )
        st.page_link("pages/5_Evaluation.py",label="🧪  Evaluation"        )
        st.page_link("pages/6_Settings.py", label="⚙️  Settings"           )

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Ollama status ──────────────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-section-header">AI Engine</div>',
            unsafe_allow_html=True,
        )

        # Cache the Ollama check for 30 s to avoid hammering the server
        @st.cache_data(ttl=30, show_spinner=False)
        def _check():
            return check_ollama()

        ollama_status = _check()

        if ollama_status["available"]:
            model_ok = any(OLLAMA_MODEL in m for m in ollama_status["models"])
            if model_ok:
                badge_class, dot, label = "online",  "●", f"Ollama · {OLLAMA_MODEL}"
            else:
                badge_class, dot, label = "checking", "●", "Ollama · model not pulled"
        else:
            badge_class, dot, label = "offline", "●", "Ollama · offline"

        st.markdown(
            f'<div style="padding: 0 0.4rem 0.8rem;">'
            f'<span class="status-badge {badge_class}">'
            f'<span class="status-dot"></span>{label}'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not ollama_status["available"]:
            st.caption(
                "📥 Install Ollama from [ollama.com](https://ollama.com/download), "
                f"then run: `ollama pull {OLLAMA_MODEL}`"
            )

        # ── Stats ──────────────────────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-section-header">Index Status</div>',
            unsafe_allow_html=True,
        )

        try:
            stats = db.get_stats()
        except Exception:
            stats = {"doc_count": 0, "page_total": 0, "chunk_total": 0, "query_count": 0}

        st.markdown(
            f'<div>'
            f'<div class="sidebar-stat"><span class="sidebar-stat-label">📄 Indexed docs</span><span class="sidebar-stat-value">{stats["doc_count"]}</span></div>'
            f'<div class="sidebar-stat"><span class="sidebar-stat-label">📃 Total pages</span><span class="sidebar-stat-value">{stats["page_total"]}</span></div>'
            f'<div class="sidebar-stat"><span class="sidebar-stat-label">🧩 Chunks</span><span class="sidebar-stat-value">{stats["chunk_total"]}</span></div>'
            f'<div class="sidebar-stat"><span class="sidebar-stat-label">❓ Queries</span><span class="sidebar-stat-value">{stats["query_count"]}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
