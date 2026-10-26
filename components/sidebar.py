"""
components/sidebar.py — NEMESIS Left Sidebar Navigation

Recreates the reference screenshot left sidebar:
  - Dragon Emblem + NEMESIS brand title & tagline
  - Navigation links:
      1. Dashboard
      2. Chat with Documents
      3. Document Library
      4. Summaries
      5. Analytics
      6. Evaluation
      7. Settings
  - Status Card 1: Ollama Connection (live status & model)
  - Status Card 2: System Status (documents count & indexing state)
  - Bottom quote: "Knowledge is not just power, it is freedom." — NEMESIS
  - Decorative dragon flame/smoke watermark
"""

import streamlit as st
from datetime import datetime
from pathlib import Path

import database as db
from llm_service import check_ollama
from config import APP_NAME, APP_TAGLINE, OLLAMA_MODEL
from components.assets_loader import get_asset_uri


def _load_css() -> None:
    """Inject the custom CSS with background texture assets."""
    css_path = Path(__file__).parent.parent / "styles" / "custom.css"
    if css_path.exists():
        scales_uri = get_asset_uri("dragon_scales_bg.jpg")
        css_text = css_path.read_text(encoding="utf-8")
        extra_vars = f"""
        :root {{
            --bg-scales-uri: url('{scales_uri}');
        }}
        """ if scales_uri else ""
        st.markdown(f"<style>{extra_vars}\n{css_text}</style>", unsafe_allow_html=True)


def render_sidebar(active_page: str = "Dashboard") -> None:
    """Render the NEMESIS left sidebar."""
    _load_css()
    logo_uri = get_asset_uri("nemesis_logo.png")
    smoke_uri = get_asset_uri("sidebar_smoke.png")

    with st.sidebar:
        # ── Dragon Emblem & NEMESIS Wordmark ─────────────────────────────────
        logo_img_tag = f'<img src="{logo_uri}" class="nemesis-brand-logo" alt="NEMESIS" />' if logo_uri else '<span style="font-size:2rem;">🐉</span>'
        st.markdown(
            f'<div class="nemesis-sidebar-brand">'
            f'{logo_img_tag}'
            f'<div class="nemesis-brand-text">'
            f'<span class="nemesis-brand-title">NEMESIS</span>'
            f'<span class="nemesis-brand-tagline">Your documents. One intelligent workspace.</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Navigation Items ─────────────────────────────────────────────────
        st.page_link("app.py",               label="Dashboard",            icon=":material/home:",          disabled=(active_page == "Dashboard"))
        st.page_link("pages/1_Chat.py",      label="Chat with Documents",   icon=":material/chat:",          disabled=(active_page == "Chat"))
        st.page_link("pages/2_Documents.py", label="Document Library",      icon=":material/folder:",        disabled=(active_page == "Documents"))
        st.page_link("pages/3_Summaries.py", label="Summaries",             icon=":material/article:",       disabled=(active_page == "Summaries"))
        st.page_link("pages/4_Analytics.py", label="Analytics",             icon=":material/bar_chart:",     disabled=(active_page == "Analytics"))
        st.page_link("pages/5_Evaluation.py",label="Evaluation",            icon=":material/shield:",        disabled=(active_page == "Evaluation"))
        st.page_link("pages/6_Settings.py",  label="Settings",              icon=":material/settings:",      disabled=(active_page == "Settings"))

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # ── Ollama Connection Card ───────────────────────────────────────────
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
            conn_pill = '<span class="sidebar-status-pill offline"><span style="font-size:7px;">●</span> Disconnected</span>'
            model_label = "Service Offline"

        st.markdown(
            f'<div class="sidebar-status-box">'
            f'<div class="sidebar-status-header">'
            f'<span>Ollama Connection</span>'
            f'{conn_pill}'
            f'</div>'
            f'<div class="sidebar-status-sub">{model_label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── System Status Card ───────────────────────────────────────────────
        try:
            stats = db.get_stats()
        except Exception:
            stats = {"doc_count": 0, "page_total": 0, "chunk_total": 0, "query_count": 0}

        st.markdown(
            f'<div class="sidebar-status-box">'
            f'<div class="sidebar-status-header">'
            f'<span>System Status</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; margin-bottom:4px;">'
            f'<span style="color:var(--text-muted); display:flex; align-items:center; gap:6px;">📄 Documents</span>'
            f'<span style="font-weight:700; color:#FFFFFF;">{stats["doc_count"]}</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem; margin-bottom:8px;">'
            f'<span style="color:var(--text-muted); display:flex; align-items:center; gap:6px;">⏱️ Indexing</span>'
            f'<span style="font-weight:700; color:#159CFF;">Idle</span>'
            f'</div>'
            f'<div style="height:3px; background:rgba(255,255,255,0.06); border-radius:3px; overflow:hidden;">'
            f'<div style="width:70%; height:100%; background:#159CFF; box-shadow:0 0 6px rgba(21,156,255,0.6);"></div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Bottom Quotation & Smoke Watermark ───────────────────────────────
        st.markdown(
            f'<div class="sidebar-quote">'
            f'“Knowledge is not just power, it is freedom.”'
            f'<div class="sidebar-quote-author">— NEMESIS</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if smoke_uri:
            st.markdown(
                f'<div class="sidebar-smoke-container">'
                f'<img src="{smoke_uri}" class="sidebar-smoke-img" alt="Dragon Scales" />'
                f'</div>',
                unsafe_allow_html=True,
            )
