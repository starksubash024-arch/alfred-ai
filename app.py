"""
app.py — RAG Document Assistant · Main Dashboard

This is the entry point for the Streamlit multipage app.
Page: Dashboard (home)

What this page shows:
  - Welcome heading and product tagline
  - Four KPI cards (real data from SQLite)
  - PDF upload dropzone with progress
  - Recent documents list
  - Quick action area (chat / summarise)
  - Recent activity feed
  - Helpful empty state when no documents uploaded
"""

import sys
import os

# Make sure the project root is on the Python path so every page can import modules
sys.path.insert(0, os.path.dirname(__file__))

import time
from datetime import datetime
from pathlib import Path

import streamlit as st

# Initialise DB on first run
import database as db
db.init_db()

import rag_engine
from components.sidebar import render_sidebar
from components.metric_cards import render_kpi_cards
from config import APP_NAME, APP_TAGLINE, MAX_UPLOAD_SIZE_MB
from utils import human_readable_size

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
def load_css():
    css_path = Path(__file__).parent / "styles" / "custom.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>",
                    unsafe_allow_html=True)

load_css()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar()

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="margin-bottom: 0.2rem;">
        <div class="page-title">RAG Document Assistant</div>
        <div class="page-subtitle">Your documents. One intelligent workspace.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPI cards ──────────────────────────────────────────────────────────────────
try:
    stats = db.get_stats()
except Exception:
    stats = {"doc_count": 0, "page_total": 0, "chunk_total": 0, "query_count": 0}

render_kpi_cards(stats)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Two-column layout: Upload (left) | Recent docs (right) ────────────────────
col_upload, col_docs = st.columns([1.1, 0.9], gap="large")

# ════════════════════════════════════════════════════════════════════════════════
# LEFT — Upload zone
# ════════════════════════════════════════════════════════════════════════════════
with col_upload:
    st.markdown(
        """
        <div class="section-header">
            <span class="section-icon">📤</span>
            <h3>Upload Documents</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="upload-zone">
            <span class="upload-icon">📄</span>
            <div class="upload-title">Drop your PDFs here</div>
            <div class="upload-subtitle">
                Supports multiple files · Max {MAX_UPLOAD_SIZE_MB} MB per file
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # Track processed files in session state to prevent infinite rerun loops
    if "processed_upload_ids" not in st.session_state:
        st.session_state.processed_upload_ids = set()
    if "upload_results" not in st.session_state:
        st.session_state.upload_results = []

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

                with st.spinner(f"Indexing {ufile.name}…"):
                    result = rag_engine.ingest_pdf(
                        file_bytes=file_bytes,
                        filename=ufile.name,
                        progress_callback=make_cb(progress_bar),
                    )

                progress_bar.empty()
                st.session_state.processed_upload_ids.add(get_file_key(ufile))
                st.session_state.upload_results.append((ufile.name, result))

            st.rerun()

        # Display results from the upload
        if st.session_state.upload_results:
            for fname, result in st.session_state.upload_results:
                if result.get("duplicate"):
                    st.info(
                        f"⚡ **{fname}** is already indexed "
                        f"({result['page_count']} pages, {result['chunk_count']} chunks). "
                        "Skipping duplicate."
                    )
                elif result["success"]:
                    st.success(
                        f"✅ **{fname}** indexed successfully — "
                        f"{result['page_count']} pages, {result['chunk_count']} chunks "
                        f"in {result['processing_ms']} ms."
                    )
                    for w in result.get("warnings", []):
                        st.warning(f"⚠️ {w}")
                else:
                    st.error(f"❌ **{fname}** — {result.get('error', 'Unknown error')}")
    else:
        # Clear tracking when uploader is emptied
        st.session_state.processed_upload_ids.clear()
        st.session_state.upload_results.clear()

# ════════════════════════════════════════════════════════════════════════════════
# RIGHT — Recent documents
# ════════════════════════════════════════════════════════════════════════════════
with col_docs:
    st.markdown(
        """
        <div class="section-header">
            <span class="section-icon">📚</span>
            <h3>Recent Documents</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    docs = db.list_documents()
    recent = docs[:8]   # show at most 8

    if not recent:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📂</div>
                <div class="empty-state-title">No documents yet</div>
                <div class="empty-state-text">
                    Upload a PDF on the left to get started.
                    Your documents will appear here once indexed.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for doc in recent:
            status = doc.get("status", "pending")
            pill_class = {
                "indexed":  "indexed",
                "pending":  "pending",
                "indexing": "indexing",
                "error":    "error",
            }.get(status, "pending")

            upload_dt = datetime.fromtimestamp(doc.get("upload_time", 0))
            time_str  = upload_dt.strftime("%d %b %Y, %H:%M")
            size_str  = human_readable_size(doc.get("file_size", 0))

            st.markdown(
                f"""
                <div class="doc-row">
                    <span class="doc-icon">📄</span>
                    <div class="doc-info">
                        <div class="doc-name" title="{doc['filename']}">{doc['filename']}</div>
                        <div class="doc-meta">
                            {doc.get('page_count', 0)} pages · {doc.get('chunk_count', 0)} chunks
                            · {size_str} · {time_str}
                        </div>
                    </div>
                    <span class="pill {pill_class}">{status}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<hr>", unsafe_allow_html=True)

# ── Quick actions ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="section-header">
        <span class="section-icon">⚡</span>
        <h3>Quick Actions</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

qa1, qa2, qa3 = st.columns(3)

with qa1:
    if st.button("💬 Chat with Documents", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Chat.py")

with qa2:
    if st.button("📝 Generate Summary", use_container_width=True):
        st.switch_page("pages/3_Summaries.py")

with qa3:
    if st.button("📊 View Analytics", use_container_width=True):
        st.switch_page("pages/4_Analytics.py")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Activity feed ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="section-header">
        <span class="section-icon">🕐</span>
        <h3>Recent Activity</h3>
    </div>
    """,
    unsafe_allow_html=True,
)

activity = db.list_activity(limit=10)

if not activity:
    st.markdown(
        """
        <div class="empty-state" style="padding: 1.5rem;">
            <div class="empty-state-icon" style="font-size:1.8rem;">🕐</div>
            <div class="empty-state-title">No activity yet</div>
            <div class="empty-state-text">
                Upload a document or ask a question to see activity here.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    dot_color = {"upload": "blue", "index": "green", "query": "purple",
                 "delete": "orange", "error": "orange"}

    items_html = ""
    for event in activity:
        color = dot_color.get(event.get("event_type", ""), "blue")
        ts    = datetime.fromtimestamp(event.get("timestamp", 0))
        ts_str = ts.strftime("%d %b, %H:%M")
        desc   = event.get("description", "")
        items_html += f"""
        <div class="activity-item">
            <span class="activity-dot {color}"></span>
            <div>
                <div class="activity-text">{desc}</div>
                <div class="activity-time">{ts_str}</div>
            </div>
        </div>
        """

    st.markdown(
        f'<div class="glass-panel">{items_html}</div>',
        unsafe_allow_html=True,
    )
