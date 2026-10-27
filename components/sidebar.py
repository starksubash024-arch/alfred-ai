"""
components/sidebar.py — ALFRED AI Left Sidebar Navigation
Signature Edition with Butler Crest & Black Titanium Surfaces
"""

import streamlit as st
from pathlib import Path

import database as db
from llm_service import check_ollama
from config import APP_NAME, APP_TAGLINE, APP_VERSION, OLLAMA_MODEL
from components.assets_loader import get_asset_uri


def _load_css() -> None:
    """Inject the custom CSS with stationary background texture."""
    css_path = Path(__file__).parent.parent / "styles" / "custom.css"
    if css_path.exists():
        titanium_uri = get_asset_uri("alfred_titanium_bg.jpg")
        css_text = css_path.read_text(encoding="utf-8")
        extra_vars = f"""
        :root {{
            --bg-titanium-uri: url('{titanium_uri}');
        }}
        """ if titanium_uri else ""
        st.markdown(f"<style>{extra_vars}\n{css_text}</style>", unsafe_allow_html=True)


def render_sidebar(active_page: str = "Dashboard") -> None:
    """Render the ALFRED AI signature sidebar with Butler Crest."""
    _load_css()
    crest_uri = get_asset_uri("alfred_crest.png")

    with st.sidebar:
        # ── Butler Crest & Brand Wordmark ─────────────────────────────────────
        crest_tag = (
            f'<img src="{crest_uri}" class="alfred-crest-img" alt="ALFRED Butler Crest" />'
            if crest_uri
            else '<span style="font-size:1.8rem;">🛡️</span>'
        )
        st.markdown(
            f"""
            <div class="alfred-sidebar-brand">
                {crest_tag}
                <div class="alfred-brand-text">
                    <span class="alfred-brand-title">ALFRED AI</span>
                    <span class="alfred-brand-tagline">Intelligent Workspace</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Navigation Items ─────────────────────────────────────────────────
        st.page_link("app.py",               label="Dashboard",   icon=":material/dashboard:",   disabled=(active_page == "Dashboard"))
        st.page_link("pages/1_Chat.py",      label="Chat",        icon=":material/chat:",        disabled=(active_page == "Chat"))
        st.page_link("pages/2_Documents.py", label="Documents",   icon=":material/folder:",      disabled=(active_page == "Documents"))
        st.page_link("pages/3_Summaries.py", label="Summaries",   icon=":material/article:",     disabled=(active_page == "Summaries"))
        st.page_link("pages/4_Analytics.py", label="Analytics",   icon=":material/bar_chart:",   disabled=(active_page == "Analytics"))
        st.page_link("pages/5_Evaluation.py",label="Evaluation",  icon=":material/shield:",      disabled=(active_page == "Evaluation"))
        st.page_link("pages/6_Settings.py",  label="Settings",    icon=":material/settings:",    disabled=(active_page == "Settings"))

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # ── Inference Engine Status Card ─────────────────────────────────────
        @st.cache_data(ttl=30, show_spinner=False)
        def _check():
            return check_ollama()

        ollama_status = _check()

        if ollama_status["available"]:
            model_ok = any(OLLAMA_MODEL in m for m in ollama_status["models"])
            disp_model = OLLAMA_MODEL if model_ok else (ollama_status["models"][0] if ollama_status["models"] else "offline")
            conn_pill = '<span class="sidebar-status-pill online"><span style="font-size:7px;">●</span> Connected</span>'
            model_label = f"model: {disp_model}"
        else:
            conn_pill = '<span class="sidebar-status-pill offline"><span style="font-size:7px;">●</span> Offline</span>'
            model_label = "Local RAG Mode"

        st.markdown(
            f"""
            <div class="sidebar-status-box">
                <div class="sidebar-status-header">
                    <span>Inference Engine</span>
                    {conn_pill}
                </div>
                <div class="sidebar-status-sub">{model_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── System Status Card ───────────────────────────────────────────────
        try:
            stats = db.get_stats()
        except Exception:
            stats = {"doc_count": 0, "page_total": 0, "chunk_total": 0, "query_count": 0}

        st.markdown(
            f"""
            <div class="sidebar-status-box">
                <div class="sidebar-status-header">
                    <span>System Status</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; margin-bottom:5px;">
                    <span style="color:var(--text-secondary); display:flex; align-items:center; gap:6px;">📄 Documents</span>
                    <span style="font-weight:700; color:var(--text-primary);">{stats["doc_count"]}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
                    <span style="color:var(--text-secondary); display:flex; align-items:center; gap:6px;">⚡ Index Status</span>
                    <span style="font-weight:700; color:var(--accent-emerald);">Active</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Enterprise Footer ────────────────────────────────────────────────
        st.markdown(
            f"""
            <div class="sidebar-footer-box">
                <div class="sidebar-footer-version">ALFRED AI Signature · v{APP_VERSION}</div>
                <div>Air-Gapped Local Intelligence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
