"""
app.py — ALFRED AI Signature Edition · Main Intelligence Dashboard

Distinctive Black Titanium & Butler Crest Intelligence Workspace:
  - Rich, layered palette (Obsidian, Graphite, Black Titanium, Crimson, Cyan, Violet, Emerald)
  - Stationary atmospheric black titanium background texture
  - Signature Butler Crest emblem integration
  - Executive intelligence cockpit hero section (zero parallax, static)
  - Four semantic data cards (Documents, Pages, Chunks, Queries)
  - Signature document intake surface with multi-file drag-and-drop
  - Recent Documents & Activity panels with live status indicators
  - Right Rail with Quick Actions, Recent Queries, and Data Enclave security card
  - Bottom ALFRED AI Assistant with scope filtering and verified source citations
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
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS with Stationary Background Texture ───────────────────────────────
def load_css():
    css_path = Path(__file__).parent / "styles" / "custom.css"
    if css_path.exists():
        titanium_uri = get_asset_uri("alfred_titanium_bg.jpg")
        css_text = css_path.read_text(encoding="utf-8")
        extra_vars = f"""
        :root {{
            --bg-titanium-uri: url('{titanium_uri}');
        }}
        """ if titanium_uri else ""
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
crest_uri = get_asset_uri("alfred_crest.png")
now_str = datetime.now().strftime("%b %d, %Y  %H:%M")

header_html = f"""<div class="alfred-top-header">
<div class="top-search-bar">
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#6C798E" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="11" cy="11" r="8"></circle>
<line x1="21" y1="21" x2="16.65" y2="16.65"></line>
</svg>
<span>Search documents, ask questions...</span>
</div>
<div class="top-header-right">
<span class="header-datetime">{now_str}</span>
<div class="user-avatar" title="Stark">S</div>
<div class="header-badge">
<span class="header-badge-dot"></span> Local Mode
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
    # ── 1. Signature Hero Greeting & Executive Intelligence Cockpit ───────────
    hero_html = f"""<div class="alfred-hero">
<div class="hero-content">
<div class="hero-status-pill"><span class="hero-status-pulse"></span><span>ALFRED INTELLIGENCE SYSTEM</span></div>
<h1 class="hero-greeting">{greeting_prefix} <span class="hero-name">Stark</span></h1>
<p class="hero-subtext">Your knowledge, connected. Your decisions, better informed.</p>
</div>
<div class="hero-cockpit">
<div class="cockpit-title">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#C8D0DC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
<line x1="8" y1="21" x2="16" y2="21"></line>
<line x1="12" y1="17" x2="12" y2="21"></line>
</svg>
<span>Intelligence Status</span>
</div>
<div class="cockpit-row">
<span class="cockpit-label">Vector Engine</span>
<span class="cockpit-val"><span class="val-dot cyan"></span> FAISS FlatIP (384-d)</span>
</div>
<div class="cockpit-row">
<span class="cockpit-label">Inference Enclave</span>
<span class="cockpit-val"><span class="val-dot emerald"></span> Air-Gapped Local</span>
</div>
</div>
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)

    # ── 2. Four Semantic Metric Cards ─────────────────────────────────────────
    try:
        stats = db.get_stats()
    except Exception:
        stats = {"doc_count": 0, "page_total": 0, "chunk_total": 0, "query_count": 0}

    render_kpi_cards(stats)

    # ── 3. Signature Document Intake Drop Zone ────────────────────────────────
    upload_html = """<div class="alfred-upload-container">
<div class="upload-center-content">
<div class="upload-icon-box">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
<polyline points="17 8 12 3 7 8"/>
<line x1="12" y1="3" x2="12" y2="15"/>
</svg>
</div>
<div class="upload-main-title">Bring your knowledge into ALFRED</div>
<div class="upload-helper-text">Drop your documents here or browse your computer.</div>
<div class="upload-badges-row">
<span class="upload-badge-chip">📄 PDF Only</span>
<span class="upload-badge-chip">⚡ Max 50MB</span>
<span class="upload-badge-chip">🔒 100% Local Ingestion</span>
<span class="upload-badge-chip">🧠 Auto-Vectorized</span>
</div>
</div>
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
            st.markdown("**Processing documents…**")
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
            """<div class="alfred-panel">
<div class="panel-header">
<div class="panel-header-left">
<span>Recent Documents</span>
</div>
<a href="./Documents" target="_self" class="panel-header-link">View all →</a>
</div>""",
            unsafe_allow_html=True,
        )

        if not all_docs:
            st.markdown(
                """<div class="panel-empty-state">
<div class="panel-empty-icon-circle">📄</div>
<div class="panel-empty-title">No documents yet</div>
<div class="panel-empty-sub">Upload your first PDF to get started</div>
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
            table_rows_html += "</div></div>"
            st.markdown(table_rows_html, unsafe_allow_html=True)

    with col_act:
        st.markdown(
            """<div class="alfred-panel">
<div class="panel-header">
<div class="panel-header-left">
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
<div class="panel-empty-icon-circle">🕐</div>
<div class="panel-empty-title">No recent activity</div>
<div class="panel-empty-sub">Your recent queries and indexing events will appear here</div>
</div>
</div>""",
                unsafe_allow_html=True,
            )
        else:
            act_items_html = "<div>"
            for ev in activity:
                color = "#F0445E" if ev.get("event_type") == "query" else "#45D6A1"
                ts = datetime.fromtimestamp(ev.get("timestamp", 0)).strftime("%b %d, %H:%M")
                act_items_html += f"""<div style="display:flex; justify-content:space-between; align-items:center; padding:0.55rem 0; border-bottom:1px solid rgba(255,255,255,0.03); font-size:0.75rem;">
<div style="display:flex; align-items:center; gap:8px;">
<span style="color:{color}; font-size:0.75rem;">●</span>
<span style="color:var(--text-primary); font-weight:600;">{truncate_text(ev.get('description',''), 32)}</span>
</div>
<span style="color:var(--text-muted); font-size:0.7rem;">{ts}</span>
</div>"""
            act_items_html += "</div></div>"
            st.markdown(act_items_html, unsafe_allow_html=True)

    # ── 5. Bottom: ALFRED AI Assistant ────────────────────────────────────────
    st.markdown("""<div class="alfred-assistant-panel">""", unsafe_allow_html=True)
    
    crest_avatar_tag = (
        f'<img src="{crest_uri}" style="width:26px; height:32px; object-fit:contain;" alt="ALFRED Crest" />'
        if crest_uri
        else '🛡️'
    )
    col_hdr_left, col_hdr_right = st.columns([3.0, 2.4])
    with col_hdr_left:
        st.markdown(
            f"""<div class="assistant-header-left">
<div class="assistant-avatar-box">
{crest_avatar_tag}
</div>
<div class="assistant-title-group">
<span class="assistant-title">ALFRED AI Assistant</span>
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
            placeholder="Type your question or query...",
            label_visibility="collapsed",
            key="alfred_main_q",
        )
    with q_btn_col:
        send_clicked = st.button("➤", type="primary", use_container_width=True, help="Send question to ALFRED AI Assistant")

    if send_clicked and user_q.strip():
        if not all_docs:
            st.warning("Please upload a PDF document before asking questions.")
        else:
            with st.spinner("ALFRED is analyzing documents and retrieving evidence…"):
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
        st.markdown("<div style='margin-top:12px; padding:14px 18px; background:var(--bg-surface); border-radius:10px; border:1px solid var(--border-fine);'>", unsafe_allow_html=True)
        st.markdown(f"**Answer:**\n\n{ans.get('answer', 'No answer generated.')}")
        
        used_chunks = ans.get("used_chunks", [])
        if used_chunks:
            st.markdown("<div style='font-size:0.75rem; font-weight:700; color:var(--accent-crimson); margin-top:10px;'>📎 Retrieved Evidence:</div>", unsafe_allow_html=True)
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
<span>Quick Actions</span>
</div>
</div>

<a href="./Summaries" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box crimson">
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
<polyline points="14 2 14 8 20 8"></polyline>
<line x1="16" y1="13" x2="8" y2="13"></line>
<line x1="16" y1="17" x2="8" y2="17"></line>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">Summarize Documents</span>
<span class="qa-desc">Extract key insights and highlights</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>

<a href="./Chat" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box cyan">
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">Start Chat</span>
<span class="qa-desc">Ask questions across library</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>

<a href="./Documents" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box violet">
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">View Library</span>
<span class="qa-desc">Manage indexed documents</span>
</div>
</div>
<span class="qa-chevron">›</span>
</a>

<a href="./Analytics" target="_self" class="quick-action-card">
<div class="quick-action-left">
<div class="qa-icon-box emerald">
<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="18" y1="20" x2="18" y2="10"></line>
<line x1="12" y1="20" x2="12" y2="4"></line>
<line x1="6" y1="20" x2="6" y2="14"></line>
</svg>
</div>
<div class="qa-text-col">
<span class="qa-title">View Analytics</span>
<span class="qa-desc">Inspect retrieval & volume trends</span>
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
<span>Recent Queries</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    queries_list = [
        "Summarize this document",
        "What are the key findings?",
        "Find specific information in this document",
        "Show me the sources for this answer.",
        "What are the main topics?",
    ]

    for q_item in queries_list:
        if st.button(f"{q_item}  ›", key=f"rq_{q_item}", use_container_width=True):
            st.session_state.assistant_question = q_item
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Right Rail 3: Signature Enterprise Enclave Card ───────────────────────
    st.markdown(
        """<div class="alfred-security-card">
<div class="security-card-header">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F0445E" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
</svg>
<span>Enterprise Data Enclave</span>
</div>
<div class="security-card-sub">
All vector indexes, embeddings, and query syntheses execute strictly within your local environment.
</div>
<div class="security-badge-row">
<span class="security-badge-dot"></span>
<span>100% On-Premise · Air-Gapped Intelligence</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )
