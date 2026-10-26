"""
app.py — NEMESIS AI Document Assistant · Main Dashboard

Redesigned in full accordance with the NEMESIS reference screenshot:
  - Futuristic dark black & charcoal palette with crimson / ruby / magenta lighting
  - Detailed dragon emblem and hero dragon background artwork
  - Slim top header with search field, time, user avatar, and Local Mode badge
  - Hero greeting with "Good afternoon, Stark", tagline, and ANALYZE | UNDERSTAND | ACHIEVE
  - Four multicolored metric cards (Crimson, Electric Blue, Violet, Teal)
  - Central PDF upload zone with drag-and-drop ingestion
  - Side-by-side Recent Documents & Recent Activity panels
  - Right Rail with Quick Actions, Recent Queries, and NEMESIS dragon brand card
  - Bottom NEMESIS AI Assistant with document selector, top-k slider, and real RAG querying
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

import database as db
db.init_db()

import rag_engine
from components.sidebar import render_sidebar
from components.metric_cards import render_kpi_cards
from components.assets_loader import get_asset_uri
from config import APP_NAME, APP_TAGLINE, MAX_UPLOAD_SIZE_MB, DEFAULT_TOP_K
from utils import human_readable_size, truncate_text

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} — Intelligent Workspace",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ──────────────────────────────────────────────────────────────────
def load_css():
    css_path = Path(__file__).parent / "styles" / "custom.css"
    if css_path.exists():
        scales_uri = get_asset_uri("dragon_scales_bg.jpg")
        css_text = css_path.read_text(encoding="utf-8")
        extra_vars = f"""
        :root {{
            --bg-scales-uri: url('{scales_uri}');
        }}
        """ if scales_uri else ""
        st.markdown(f"<style>{extra_vars}\n{css_text}</style>", unsafe_allow_html=True)

load_css()

# ── Render Left Sidebar ───────────────────────────────────────────────────────
render_sidebar(active_page="Dashboard")

# ── Session State Initialisation ──────────────────────────────────────────────
if "processed_upload_ids" not in st.session_state:
    st.session_state.processed_upload_ids = set()
if "upload_results" not in st.session_state:
    st.session_state.upload_results = []
if "assistant_question" not in st.session_state:
    st.session_state.assistant_question = ""
if "assistant_answer" not in st.session_state:
    st.session_state.assistant_answer = None

# ── Top Header Navigation Bar ─────────────────────────────────────────────────
hero_dragon_uri = get_asset_uri("hero_dragon_head.webp") or get_asset_uri("hero_dragon_head.png") or get_asset_uri("hero_dragon.png")
bottom_card_dragon_uri = get_asset_uri("bottom_dragon_card.png")
upload_dragon_uri = get_asset_uri("upload_dragon.png")
upload_pdf_uri = get_asset_uri("upload_pdf_icon.png")

now_str = datetime.now().strftime("%b %d, %Y  %H:%M")

header_html = f"""<div class="nemesis-top-header">
<div class="top-search-bar">
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#AAB0BC" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
<circle cx="11" cy="11" r="8"></circle>
<line x1="21" y1="21" x2="16.65" y2="16.65"></line>
</svg>
<span>Search documents, ask questions...</span>
</div>
<div class="top-header-right">
<span class="header-theme-icon" title="Toggle theme">☼</span>
<span class="header-datetime">{now_str}</span>
<div class="user-avatar" title="Stark">S</div>
<div class="header-badge">
<span style="font-size:7px; color:#00D8B5;">●</span> Local Mode <span style="font-size:9px; opacity:0.7;">▾</span>
</div>
</div>
</div>"""
st.markdown(header_html, unsafe_allow_html=True)

# ── Greeting calculation ──────────────────────────────────────────────────────
cur_hour = datetime.now().hour
if cur_hour < 12:
    greeting_prefix = "Good morning,"
elif cur_hour < 17:
    greeting_prefix = "Good afternoon,"
else:
    greeting_prefix = "Good evening,"

# ── Main Layout: Center Workspace (col_main) & Right Rail (col_rail) ──────────
col_main, col_rail = st.columns([2.4, 0.95], gap="large")

with col_main:
    # ── 1. Expansive Hero Greeting with Atmospheric Dragon Artwork ────────────
    hero_dragon_tag = f'<img src="{hero_dragon_uri}" class="hero-dragon-backdrop" alt="NEMESIS Dragon" />' if hero_dragon_uri else ''
    hero_html = f"""<div class="nemesis-hero-scene">
<div class="hero-content-left">
<div class="hero-hud-badge"><span class="hud-pulse-dot"></span><span>NEMESIS DOCUMENT COMMAND</span></div>
<h1 class="hero-greeting">{greeting_prefix} <span class="hero-name">Stark</span></h1>
<div class="hero-subtext">Upload your documents, ask questions, get summaries and gain insights — all from your local files.</div>
<div class="hero-motto-strip">
<span class="motto-item">ANALYZE</span>
<span class="motto-divider">/</span>
<span class="motto-item">UNDERSTAND</span>
<span class="motto-divider">/</span>
<span class="motto-item">ACHIEVE</span>
</div>
</div>
{hero_dragon_tag}
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)

    # ── 2. Four Multicolored Metric Cards ─────────────────────────────────────
    try:
        stats = db.get_stats()
    except Exception:
        stats = {"doc_count": 0, "page_total": 0, "chunk_total": 0, "query_count": 0}

    render_kpi_cards(stats)

    # ── 3. Central PDF Upload Drop Zone (Dragon Command Center) ────────────────
    pdf_decor_tag = f'<img src="{upload_pdf_uri}" class="upload-decor-pdf-img" alt="PDF" />' if upload_pdf_uri else ''
    dragon_decor_tag = f'<img src="{upload_dragon_uri}" class="upload-decor-dragon-img" alt="Dragon" />' if upload_dragon_uri else ''

    upload_html = f"""<div class="nemesis-upload-container">
{pdf_decor_tag}
<div class="upload-center-content">
<div class="upload-cloud-icon">
<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#FF174F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
<path d="M12 12v9"/>
<path d="m8 16 4-4 4 4"/>
</svg>
</div>
<div class="upload-main-title">Upload PDF Documents</div>
<div class="upload-helper-text">Drag and drop your PDF files here, or click to browse</div>
<div class="upload-footer-text">Supports multiple files • PDF only • Max 50MB each</div>
</div>
{dragon_decor_tag}
</div>"""
    st.markdown(upload_html, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        def get_file_key(f):
            return f"{f.name}_{f.size}"

        new_files = [f for f in uploaded_files if get_file_key(f) not in st.session_state.processed_upload_ids]

        if new_files:
            st.markdown("**Processing uploads…**")
            for ufile in new_files:
                file_bytes = ufile.read()
                progress_bar = st.progress(0.0, text=f"Processing {ufile.name}…")

                def make_cb(bar):
                    def cb(pct, msg):
                        bar.progress(min(pct, 1.0), text=msg)
                    return cb

                try:
                    with st.spinner(f"Indexing {ufile.name}…"):
                        result = rag_engine.ingest_pdf(
                            file_bytes=file_bytes,
                            filename=ufile.name,
                            progress_callback=make_cb(progress_bar),
                        )
                except Exception as exc:
                    result = {
                        "success": False,
                        "error": str(exc),
                        "duplicate": False,
                        "doc_id": None,
                    }
                finally:
                    progress_bar.empty()
                    st.session_state.processed_upload_ids.add(get_file_key(ufile))
                    st.session_state.upload_results.append((ufile.name, result))

            st.rerun()

        if st.session_state.upload_results:
            for fname, result in st.session_state.upload_results:
                if result.get("duplicate"):
                    st.info(f"⚡ **{fname}** is already indexed ({result['page_count']} pages, {result['chunk_count']} chunks). Skipping duplicate.")
                elif result["success"]:
                    st.success(f"✅ **{fname}** indexed successfully — {result['page_count']} pages, {result['chunk_count']} chunks in {result['processing_ms']} ms.")
                    for w in result.get("warnings", []):
                        st.warning(f"⚠️ {w}")
                else:
                    st.error(f"❌ **{fname}** — {result.get('error', 'Unknown error')}")
    else:
        st.session_state.processed_upload_ids.clear()
        st.session_state.upload_results.clear()

    # ── 4. Middle Row: Side-by-Side Recent Documents & Recent Activity ────────
    col_docs, col_act = st.columns(2, gap="medium")

    all_docs = db.list_documents()
    with col_docs:
        st.markdown(
            """<div class="nemesis-panel">
<div class="panel-header">
<div class="panel-header-left">
<span class="panel-header-icon">📄</span>
<span>Recent Documents</span>
</div>
<a href="./Documents" target="_self" class="panel-header-link">View all →</a>
</div>""",
            unsafe_allow_html=True,
        )

        if not all_docs:
            st.markdown(
                """<div class="panel-empty-state">
<div class="panel-empty-icon-circle">
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#555D71" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
<polyline points="14 2 14 8 20 8"></polyline>
</svg>
</div>
<div class="panel-empty-title">No documents yet</div>
<div class="panel-empty-sub">Upload your first PDF to get started</div>
<button class="empty-upload-btn">📄  Upload Document</button>
</div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            table_rows_html = """<div class="doc-table-header">
<span>Name</span>
<span>Pages</span>
<span>Size</span>
<span>Status</span>
<span>Uploaded</span>
</div>"""
            for d in all_docs[:4]:
                st_pill = "indexed" if d.get("status") == "indexed" else "pending"
                dt_str = datetime.fromtimestamp(d.get("upload_time", 0)).strftime("%b %d")
                sz_str = human_readable_size(d.get("file_size", 0))
                table_rows_html += f"""<div class="doc-table-row">
<span class="doc-name-cell" title="{d['filename']}">{d['filename']}</span>
<span>{d.get('page_count', 0)}</span>
<span>{sz_str}</span>
<span><span class="pill {st_pill}">{d.get('status','indexed')}</span></span>
<span>{dt_str}</span>
</div>"""
            table_rows_html += "</div>"
            st.markdown(table_rows_html, unsafe_allow_html=True)

    with col_act:
        st.markdown(
            """<div class="nemesis-panel">
<div class="panel-header">
<div class="panel-header-left">
<span class="panel-header-icon">🕐</span>
<span>Recent Activity</span>
</div>
<span class="panel-header-link">View all →</span>
</div>""",
            unsafe_allow_html=True,
        )

        activity = db.list_activity(limit=4)
        if not activity:
            st.markdown(
                """<div class="panel-empty-state">
<div class="panel-empty-icon-circle">
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#159CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
</svg>
</div>
<div class="panel-empty-title">No recent activity</div>
<div class="panel-empty-sub">Your recent actions will appear here</div>
</div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            act_items_html = "<div>"
            for ev in activity:
                color = "crimson" if ev.get("event_type") == "query" else "teal"
                ts = datetime.fromtimestamp(ev.get("timestamp", 0)).strftime("%b %d, %H:%M")
                act_items_html += f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:0.55rem 0; border-bottom:1px solid rgba(255,255,255,0.03); font-size:0.75rem;">
<div style="display:flex; align-items:center; gap:8px;">
<span style="color:#FF174F; font-size:0.8rem;">●</span>
<span style="color:#F4F5FA; font-weight:600;">{truncate_text(ev.get('description',''), 32)}</span>
</div>
<span style="color:var(--text-dim); font-size:0.68rem;">{ts}</span>
</div>"""
            act_items_html += "</div></div>"
            st.markdown(act_items_html, unsafe_allow_html=True)

    # ── 5. Bottom: NEMESIS AI Assistant ───────────────────────────────────────
    st.markdown("""<div class="nemesis-assistant-panel">""", unsafe_allow_html=True)
    
    col_hdr_left, col_hdr_right = st.columns([3.0, 2.4])
    with col_hdr_left:
        st.markdown(
            """<div class="assistant-header-left">
<div class="assistant-avatar-circle">🐉</div>
<div class="assistant-title-group">
<span class="assistant-title">NEMESIS AI Assistant</span>
<span class="assistant-sub">Ask anything about your documents — get accurate, source-backed answers.</span>
</div>
</div>""",
            unsafe_allow_html=True,
        )
    with col_hdr_right:
        c_scope, c_k, c_mic = st.columns([1.6, 1.2, 0.6])
        with c_scope:
            doc_opts = {"All Documents": None}
            for d in all_docs:
                if d.get("status") == "indexed":
                    doc_opts[d["filename"]] = d["id"]
            chosen_scope_label = st.selectbox("Scope", list(doc_opts.keys()), label_visibility="collapsed")
            chosen_doc_id = doc_opts.get(chosen_scope_label)
        with c_k:
            chosen_k = st.selectbox("Top K", [3, 5, 8, 10], index=1, format_func=lambda x: f"Top K: {x}", label_visibility="collapsed")
        with c_mic:
            st.button("🎙️", key="btn_mic", help="Voice Input (Local mode)")

    # Question Input
    default_q = st.session_state.assistant_question or ""
    q_input_col, q_btn_col = st.columns([5.5, 0.7], gap="small")
    with q_input_col:
        user_q = st.text_input(
            "Ask anything about your documents...",
            value=default_q,
            placeholder="Type your question here...",
            label_visibility="collapsed",
            key="nemesis_main_q",
        )
    with q_btn_col:
        send_clicked = st.button("➤", type="primary", use_container_width=True, help="Send question to NEMESIS AI Assistant")

    if send_clicked and user_q.strip():
        if not all_docs:
            st.warning("Please upload a PDF document before asking questions.")
        else:
            with st.spinner("NEMESIS is analyzing documents and retrieving evidence…"):
                q_res = rag_engine.query(
                    question=user_q.strip(),
                    top_k=chosen_k,
                    doc_id_filter=chosen_doc_id,
                )
                st.session_state.assistant_answer = q_res
                st.session_state.assistant_question = user_q.strip()

    # Display Answer & Source Cards if available
    if st.session_state.assistant_answer:
        ans = st.session_state.assistant_answer
        st.markdown("<div style='margin-top:12px; padding:12px 16px; background:#0F1220; border-radius:10px; border:1px solid rgba(255,23,79,0.3);'>", unsafe_allow_html=True)
        st.markdown(f"**Answer:**\n\n{ans.get('answer', 'No answer generated.')}")
        
        used_chunks = ans.get("used_chunks", [])
        if used_chunks:
            st.markdown("<div style='font-size:0.75rem; font-weight:700; color:var(--accent-crimson); margin-top:8px;'>📎 Retrieved Evidence:</div>", unsafe_allow_html=True)
            for i, chk in enumerate(used_chunks, 1):
                p_num = chk.get("page_number", "?")
                fname = chk.get("filename", "Document")
                score = chk.get("score", 0.0)
                snip = truncate_text(chk.get("text", ""), 220)
                with st.expander(f"[S{i}] {fname} · Page {p_num} (Score: {score:.3f})"):
                    st.caption(snip)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


with col_rail:
    # ── Right Rail 1: Quick Actions Panel ─────────────────────────────────────
    quick_actions_html = """<div class="right-rail-box">
<div class="panel-header" style="margin-bottom:0.75rem;">
<div class="panel-header-left">
<span style="color:#FF174F; font-size:1rem;">⚡</span>
<span>Quick Actions</span>
</div>
</div>

<a href="./Summaries" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box crimson">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FF174F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
<polyline points="14 2 14 8 20 8"></polyline>
<line x1="16" y1="13" x2="8" y2="13"></line>
<line x1="16" y1="17" x2="8" y2="17"></line>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">Summarize Documents</span>
<span class="qa-desc">Get key insights and highlights</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>

<a href="./Chat" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box violet">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#963DFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">Start Chat</span>
<span class="qa-desc">Ask questions about your documents</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>

<a href="./Documents" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box blue">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#159CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">View Library</span>
<span class="qa-desc">Manage your uploaded documents</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>

<a href="./Analytics" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box teal">
<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#00D8B5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="18" y1="20" x2="18" y2="10"></line>
<line x1="12" y1="20" x2="12" y2="4"></line>
<line x1="6" y1="20" x2="6" y2="14"></line>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">View Analytics</span>
<span class="qa-desc">See detailed charts and insights</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>
</div>"""
    st.markdown(quick_actions_html, unsafe_allow_html=True)

    # ── Right Rail 2: Recent Queries Panel ────────────────────────────────────
    st.markdown(
        """<div class="right-rail-box">
<div class="panel-header" style="margin-bottom:0.75rem;">
<div class="panel-header-left">
<span style="color:#FF174F; font-size:1rem;">💬</span>
<span>Recent Queries</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    queries_list = [
        ("📌", "Summarize this document"),
        ("🎯", "What are the key findings?"),
        ("🔍", "Find specific information in this document"),
        ("📎", "Show me the sources for this answer."),
        ("📄", "What are the main topics?"),
    ]

    for icon, q_item in queries_list:
        if st.button(f"{icon}  {q_item}  ›", key=f"rq_{q_item}", use_container_width=True):
            st.session_state.assistant_question = q_item
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Right Rail 3: NEMESIS Brand Promotional Card ──────────────────────────
    if bottom_card_dragon_uri:
        st.markdown(
            f"""<div class="nemesis-brand-card-wrapper">
<img src="{bottom_card_dragon_uri}" class="nemesis-brand-card-img" alt="NEMESIS - Your documents. One intelligent workspace." />
</div>""",
            unsafe_allow_html=True,
        )
