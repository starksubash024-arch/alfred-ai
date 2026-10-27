"""
pages/6_Settings.py — Application Settings

Explains configuration options and allows runtime overrides stored in session state.
Does NOT write to .env (that would require a restart).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
import streamlit as st

from components.sidebar import render_sidebar
from config import (
    APP_NAME, APP_VERSION, OLLAMA_HOST, OLLAMA_MODEL,
    DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, DEFAULT_TOP_K,
    MAX_UPLOAD_SIZE_MB, EMBEDDING_MODEL, DB_PATH, UPLOAD_DIR, INDEX_DIR,
)
from llm_service import check_ollama

st.set_page_config(
    page_title=f"Settings — {APP_NAME}",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css()
render_sidebar(active_page="Settings")

st.markdown(
    """
    <div class="page-title">Settings & Configuration</div>
    <div class="page-subtitle">Inspect system parameters, inference endpoints, and storage metrics.</div>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs(["Inference Engine", "Chunking", "Retrieval", "Storage", "About"])

# ── Tab: Ollama ────────────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown("### Ollama Connection")
    st.markdown(
        f"""
        | Setting | Value |
        |---------|-------|
        | Host    | `{OLLAMA_HOST}` |
        | Model   | `{OLLAMA_MODEL}` |

        To change these values, edit your `.env` file and restart the app.
        """
    )

    if st.button("🔄 Test Connection"):
        with st.spinner("Checking Ollama…"):
            status = check_ollama()
        if status["available"]:
            st.success(
                f"✅ Ollama is reachable. "
                f"Available models: {', '.join(status['models']) or 'none pulled yet'}"
            )
            if not any(OLLAMA_MODEL in m for m in status["models"]):
                st.warning(
                    f"Model `{OLLAMA_MODEL}` is not pulled yet. "
                    f"Run: `ollama pull {OLLAMA_MODEL}`"
                )
        else:
            st.error(f"❌ {status['error']}")

    st.markdown("---")
    st.markdown("#### Quick Setup Guide")
    st.markdown(
        f"""
        1. **Install Ollama** — [ollama.com/download](https://ollama.com/download)
        2. **Start the server** — `ollama serve` (or it starts automatically on Windows)
        3. **Pull the model** — `ollama pull {OLLAMA_MODEL}`
        4. **Verify** — click "Test Connection" above

        After the model is downloaded (~2 GB for llama3.2:3b), all AI features
        work **fully offline**. Your documents never leave your machine.
        """
    )

# ── Tab: Chunking ──────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### Text Chunking")
    st.info(
        "Chunking settings affect how PDFs are split before embedding. "
        "Changes here apply to newly indexed documents only. "
        "To apply to existing documents, reindex them from the Document Library."
    )

    st.markdown(
        f"""
        | Setting | Current value | Description |
        |---------|--------------|-------------|
        | Chunk size | **{DEFAULT_CHUNK_SIZE} chars** | Maximum characters per chunk. Larger = more context per retrieval; smaller = more precise matching. |
        | Overlap | **{DEFAULT_CHUNK_OVERLAP} chars** | Characters shared between adjacent chunks. Prevents context from being cut at boundaries. |

        To change defaults, set `DEFAULT_CHUNK_SIZE` and `DEFAULT_CHUNK_OVERLAP` in `.env`.
        """
    )

    st.markdown("#### Effect of chunk size")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            **Smaller chunks (300–500 chars)**
            - More precise matches
            - Less surrounding context
            - More vectors in index
            """
        )
    with col2:
        st.markdown(
            """
            **Larger chunks (1000–2000 chars)**
            - Richer context per result
            - May dilute relevance signal
            - Fewer vectors in index
            """
        )

# ── Tab: Retrieval ─────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown("### Retrieval Settings")
    st.markdown(
        f"""
        | Setting | Current value | Description |
        |---------|--------------|-------------|
        | Embedding model | `{EMBEDDING_MODEL}` | Sentence-Transformers model used for all embeddings. |
        | Default top-k | **{DEFAULT_TOP_K}** | Number of chunks retrieved per query. Increase for broader coverage; decrease for speed. |

        **About retrieval scores:**  
        Scores are cosine similarities between the query embedding and chunk embeddings.
        A score near 1.0 means the passage is semantically very close to the query.
        High retrieval score ≠ factual correctness — always review cited sources.
        """
    )

# ── Tab: Storage ───────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown("### Storage Paths")
    st.markdown(
        f"""
        | Path | Location |
        |------|----------|
        | Uploaded PDFs | `{UPLOAD_DIR}` |
        | FAISS indexes | `{INDEX_DIR}` |
        | SQLite database | `{DB_PATH}` |

        These paths are gitignored and stay on your local machine.
        """
    )

    st.markdown("#### Database maintenance")
    if st.button("🔍 Show DB file info"):
        import os
        db_file = Path(DB_PATH)
        if db_file.exists():
            size_kb = db_file.stat().st_size / 1024
            st.success(f"Database exists · {size_kb:.1f} KB")
        else:
            st.warning("Database file not found.")

# ── Tab: About ─────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown(
        f"""
        ### {APP_NAME} · v{APP_VERSION}

        A local-first RAG Document Assistant built with:

        | Component | Technology |
        |-----------|-----------|
        | Frontend  | Streamlit + custom CSS |
        | PDF processing | PyMuPDF |
        | Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
        | Vector search | FAISS CPU |
        | Local LLM | Ollama ({OLLAMA_MODEL}) |
        | Database | SQLite |
        | Charts | Plotly |
        | Testing | pytest |

        **Privacy:** All documents and queries are processed on your local machine.
        No data is sent to external servers (beyond the initial model download from HuggingFace / Ollama).

        **Limitations:**
        - Scanned PDFs (image-only) require OCR — not currently supported.
        - Large PDFs are sampled for summarisation (first 20 chunks).
        - Answer quality depends on the local model's capabilities.
        - The local Ollama endpoint is not automatically available for cloud deployments.
        """
    )
