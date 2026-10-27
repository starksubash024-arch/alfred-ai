"""
pages/1_Chat.py — Chat with Documents

Premium AI chat interface with:
  - Document selector (all docs or specific doc)
  - Configurable top-k retrieval
  - Grounded answers with [S1][S2] citations
  - Expandable source cards per answer
  - Conversation history in session state
  - Clear conversation button
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from datetime import datetime

import streamlit as st

import database as db
from components.sidebar import render_sidebar
from components.source_cards import render_source_cards
from config import APP_NAME, DEFAULT_TOP_K, OLLAMA_MODEL
from llm_service import check_ollama, model_is_available
from rag_engine import query as rag_query

st.set_page_config(
    page_title=f"Chat — {APP_NAME}",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    from pathlib import Path
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css()
render_sidebar(active_page="Chat")

# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_query_count" not in st.session_state:
    st.session_state.session_query_count = 0

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-title">Chat with Documents</div>
    <div class="page-subtitle">Ask questions grounded in your indexed documents with verified citations.</div>
    """,
    unsafe_allow_html=True,
)

# ── Ollama availability check ──────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _ollama_status():
    return check_ollama()

ollama = _ollama_status()

if not ollama["available"]:
    st.error(
        "**Ollama is not running.** "
        "Please install and start Ollama to use the chat feature.\n\n"
        "1. Download from [ollama.com/download](https://ollama.com/download)\n"
        f"2. Run: `ollama pull {OLLAMA_MODEL}`\n"
        "3. Refresh this page."
    )

# ── Controls ───────────────────────────────────────────────────────────────────
docs = db.list_documents()
indexed_docs = [d for d in docs if d["status"] == "indexed"]

ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 1, 1, 1])

with ctrl_col1:
    doc_options = {"All indexed documents": None}
    for d in indexed_docs:
        doc_options[d["filename"]] = d["id"]
    selected_label = st.selectbox("Search scope", list(doc_options.keys()),
                                  label_visibility="visible")
    selected_doc_id = doc_options[selected_label]

with ctrl_col2:
    top_k = st.slider("Top-k chunks", min_value=1, max_value=15,
                       value=DEFAULT_TOP_K, step=1)

with ctrl_col3:
    available_models = ollama.get("models", [OLLAMA_MODEL])
    if not available_models:
        available_models = [OLLAMA_MODEL]
    model_choice = st.selectbox("Model", available_models)

with ctrl_col4:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑 Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ── No documents warning ───────────────────────────────────────────────────────
if not indexed_docs:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <div class="empty-state-title">No documents indexed yet</div>
            <div class="empty-state-text">
                Go to the Dashboard and upload a PDF to start chatting.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Conversation display ───────────────────────────────────────────────────────
chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown(
            """
            <div class="empty-state" style="padding:2rem;">
                <div class="empty-state-icon">💬</div>
                <div class="empty-state-title">Start a conversation</div>
                <div class="empty-state-text">
                    Type a question below. Answers will be grounded in your documents,
                    with source citations so you can verify every claim.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.messages:
            role   = msg["role"]
            avatar = "👤" if role == "user" else "🛡️"
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg["content"])
                if role == "assistant" and msg.get("chunks"):
                    render_source_cards(msg["chunks"])
                    if msg.get("duration_ms"):
                        st.caption(f"⏱ {msg['duration_ms']} ms · model: {msg.get('model','')}")

# ── Input area ─────────────────────────────────────────────────────────────────
question = st.chat_input(
    "Ask a question about your documents…",
    disabled=not ollama["available"],
)

if question:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    # Generate answer
    with st.chat_message("assistant", avatar="🛡️"):
        with st.spinner("Searching documents and generating answer…"):
            result = rag_query(
                question=question,
                top_k=top_k,
                doc_id_filter=selected_doc_id,
                model=model_choice,
            )

        if result.get("error"):
            st.error(f"**Error:** {result['error']}")
            answer_text = result.get("answer", "")
        else:
            answer_text = result.get("answer", "No answer generated.")
            st.markdown(answer_text)
            render_source_cards(result.get("used_chunks", []))
            st.caption(
                f"⏱ {result.get('duration_ms', 0)} ms · "
                f"model: {result.get('model','')} · "
                f"{len(result.get('used_chunks', []))} sources used"
            )

        st.session_state.session_query_count += 1
        st.session_state.messages.append({
            "role":    "assistant",
            "content": answer_text,
            "chunks":  result.get("used_chunks", []),
            "duration_ms": result.get("duration_ms"),
            "model":   result.get("model"),
        })
