"""
pages/2_Documents.py — Document Library

Searchable, sortable table of all uploaded documents.
Supports reindex (rebuild FAISS index) and delete actions.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from datetime import datetime
from pathlib import Path

import streamlit as st

import database as db
from components.sidebar import render_sidebar
from config import APP_NAME
from rag_engine import delete_document
from utils import human_readable_size

st.set_page_config(
    page_title=f"Documents — {APP_NAME}",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css()
render_sidebar(active_page="Documents")

st.markdown(
    """
    <div class="page-title">📚 Document Library</div>
    <div class="page-subtitle">Manage your indexed PDFs.</div>
    """,
    unsafe_allow_html=True,
)

# ── Load documents ─────────────────────────────────────────────────────────────
docs = db.list_documents()

if not docs:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <div class="empty-state-title">No documents uploaded yet</div>
            <div class="empty-state-text">
                Go to the Dashboard and upload a PDF to build your document library.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Search / filter ────────────────────────────────────────────────────────────
search_col, filter_col = st.columns([3, 1])
with search_col:
    query = st.text_input("🔍 Search by filename", placeholder="Type to filter…",
                          label_visibility="collapsed")
with filter_col:
    status_filter = st.selectbox("Status", ["All", "indexed", "error", "pending"],
                                  label_visibility="collapsed")

filtered = docs
if query:
    filtered = [d for d in filtered if query.lower() in d["filename"].lower()]
if status_filter != "All":
    filtered = [d for d in filtered if d["status"] == status_filter]

st.caption(f"Showing {len(filtered)} of {len(docs)} documents")
st.markdown("<hr>", unsafe_allow_html=True)

# ── Document table ─────────────────────────────────────────────────────────────
for doc in filtered:
    status     = doc.get("status", "pending")
    pill_class = {"indexed": "indexed", "pending": "pending",
                  "indexing": "indexing", "error": "error"}.get(status, "pending")
    upload_dt  = datetime.fromtimestamp(doc.get("upload_time", 0))
    time_str   = upload_dt.strftime("%d %b %Y, %H:%M")
    size_str   = human_readable_size(doc.get("file_size", 0))
    proc_ms    = doc.get("processing_ms") or 0
    proc_str   = f"{proc_ms} ms" if proc_ms else "—"

    with st.container():
        row_left, row_right = st.columns([5, 2])

        with row_left:
            st.markdown(
                f"""
                <div class="doc-row" style="margin-bottom:0;">
                    <span class="doc-icon">📄</span>
                    <div class="doc-info">
                        <div class="doc-name">{doc['filename']}</div>
                        <div class="doc-meta">
                            {doc.get('page_count', 0)} pages ·
                            {doc.get('chunk_count', 0)} chunks ·
                            {size_str} ·
                            Indexed {time_str} ·
                            Processing: {proc_str}
                        </div>
                        {f'<div class="doc-meta" style="color:#EF4444;">⚠ {doc.get("error_msg","")}</div>'
                         if doc.get("error_msg") else ""}
                    </div>
                    <span class="pill {pill_class}">{status}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with row_right:
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🗑 Delete", key=f"del_{doc['id']}", use_container_width=True):
                    st.session_state[f"confirm_delete_{doc['id']}"] = True

            with btn_col2:
                if st.button("🔄 Reindex", key=f"reindex_{doc['id']}", use_container_width=True):
                    # Reindex: rebuild FAISS index from stored chunks
                    with st.spinner(f"Reindexing {doc['filename']}…"):
                        from vector_store import build_index, rebuild_combined_index
                        chunks = db.get_chunks_for_doc(doc["id"])
                        if chunks:
                            try:
                                build_index(chunks, doc["id"])
                                all_chunks = db.get_all_chunks()
                                rebuild_combined_index(all_chunks)
                                db.update_document_status(
                                    doc["id"], "indexed",
                                    chunk_count=len(chunks),
                                )
                                st.success(f"✅ Reindexed {doc['filename']}")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Reindex failed: {exc}")
                        else:
                            st.warning("No chunks found. Re-upload the document.")

        # Delete confirmation
        if st.session_state.get(f"confirm_delete_{doc['id']}"):
            st.warning(
                f"⚠️ Delete **{doc['filename']}**? This removes the document, "
                "all its chunks, and its index entry. This cannot be undone."
            )
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("✅ Yes, delete", key=f"confirm_yes_{doc['id']}", type="primary"):
                    result = delete_document(doc["id"])
                    if result["success"]:
                        st.success(f"Deleted {doc['filename']}.")
                    else:
                        st.error(f"Delete failed: {result['error']}")
                    del st.session_state[f"confirm_delete_{doc['id']}"]
                    st.cache_data.clear()
                    st.rerun()
            with confirm_col2:
                if st.button("❌ Cancel", key=f"confirm_no_{doc['id']}"):
                    del st.session_state[f"confirm_delete_{doc['id']}"]
                    st.rerun()

    st.markdown("<hr style='margin:0.3rem 0;'>", unsafe_allow_html=True)
