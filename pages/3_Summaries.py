"""
pages/3_Summaries.py — Document Summary Workspace

Select an indexed document and generate a structured summary using
the map-reduce summariser. Includes export to Markdown / TXT.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
import streamlit as st
import importlib

import database as db
from components.sidebar import render_sidebar
from config import APP_NAME, OLLAMA_MODEL
from llm_service import check_ollama

import summarizer
importlib.reload(summarizer)
from summarizer import summarise_document, generate_extractive_summary

st.set_page_config(
    page_title=f"Summaries — {APP_NAME}",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    from components.assets_loader import get_asset_uri
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        aurora_uri = get_asset_uri("alfred_aurora_bg.jpg")
        css_text = p.read_text(encoding="utf-8")
        extra_vars = f":root {{ --bg-aurora-uri: url('{aurora_uri}'); }}" if aurora_uri else ""
        st.markdown(f"<style>{extra_vars}\n{css_text}</style>", unsafe_allow_html=True)

load_css()
render_sidebar(active_page="Summaries")

st.markdown(
    """<div class="page-title">Document Summaries</div>
<div class="page-subtitle">AI-generated structured syntheses and executive briefs grounded in your documents.</div>""",
    unsafe_allow_html=True,
)

# ── Ollama check ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _check():
    return check_ollama()

ollama = _check()
if not ollama["available"]:
    st.info(
        "ℹ️ **Ollama is currently offline.** "
        "You can still generate instant document summaries using the **⚡ Instant Extraction** mode below. "
        f"To enable generative AI synthesis, start Ollama and run `ollama pull {OLLAMA_MODEL}`."
    )

# ── Document selector ──────────────────────────────────────────────────────────
indexed_docs = [d for d in db.list_documents() if d["status"] == "indexed"]

if not indexed_docs:
    st.markdown(
        """<div class="empty-state">
<div class="empty-state-icon">📂</div>
<div class="empty-state-title">No indexed documents</div>
<div class="empty-state-text">Upload and index a PDF on the Dashboard first.</div>
</div>""",
        unsafe_allow_html=True,
    )
    st.stop()

col1, col2 = st.columns([1.6, 1], gap="medium")
with col1:
    doc_map = {d["filename"]: d for d in indexed_docs}
    chosen_name = st.selectbox("Select document to summarise",
                               list(doc_map.keys()),
                               label_visibility="visible")

with col2:
    summary_mode = st.radio(
        "Summarisation Mode",
        ["⚡ Instant Extraction (Fast & Offline)", "🤖 AI Map-Reduce (Local LLM)"],
        horizontal=False,
    )

chosen_doc = doc_map[chosen_name]

st.markdown(
    f'<div class="glass-panel" style="padding:0.8rem 1.2rem; margin:0.8rem 0;">'
    f'<b>📄 {chosen_doc["filename"]}</b> &nbsp;·&nbsp; '
    f'{chosen_doc.get("page_count", 0)} pages &nbsp;·&nbsp; '
    f'{chosen_doc.get("chunk_count", 0)} chunks'
    f'</div>',
    unsafe_allow_html=True,
)

# Prominent primary button across the full section width
run_btn = st.button("✨ Generate Summary", type="primary", use_container_width=True, key="btn_generate_summary")

# ── Summary generation ─────────────────────────────────────────────────────────
if run_btn:
    chunks = db.get_chunks_for_doc(chosen_doc["id"])
    if not chunks:
        st.error("No text chunks found for this document. Try reindexing it from the Document Library.")
        st.stop()

    if "Instant Extraction" in summary_mode:
        with st.spinner("Extracting executive overview, key topics, and dates/figures…"):
            result = generate_extractive_summary(chunks, filename=chosen_doc["filename"])
    else:
        # LLM mode
        if not ollama["available"]:
            st.warning("Ollama is not running. Automatically using Instant Extraction mode instead.")
            with st.spinner("Extracting executive overview, key topics, and dates/figures…"):
                result = generate_extractive_summary(chunks, filename=chosen_doc["filename"])
                result["mode_notice"] = "Generated via instant extraction because Ollama is currently offline."
        else:
            with st.spinner(f"Generating summary via Ollama ({min(len(chunks), 20)} chunks)…"):
                result = summarise_document(chunks)

    st.session_state["last_summary"] = result
    st.session_state["last_summary_doc"] = chosen_name
    st.rerun()

# ── Display summary ────────────────────────────────────────────────────────────
summary = st.session_state.get("last_summary")
summary_doc = st.session_state.get("last_summary_doc", "")

if summary:
    if summary.get("error"):
        st.error(f"Summarisation failed: {summary['error']}")
    else:
        if summary_doc != chosen_name:
            st.info(
                f"Showing summary for **{summary_doc}**. "
                "Click 'Generate Summary' to summarise the currently selected document."
            )

        tabs = st.tabs(["📋 Overview", "🔑 Key Points", "📖 Details", "📤 Export"])

        # ── Tab 1: Overview ────────────────────────────────────────────────────
        with tabs[0]:
            if summary.get("concise_summary"):
                st.markdown("### One-liner")
                st.info(f"💡 {summary['concise_summary']}")

            if summary.get("executive_summary"):
                st.markdown("### Executive Summary")
                st.markdown(
                    f'<div class="glass-panel">{summary["executive_summary"]}</div>',
                    unsafe_allow_html=True,
                )

            if summary.get("main_topics"):
                st.markdown("### Main Topics")
                cols = st.columns(min(len(summary["main_topics"]), 3))
                for i, topic in enumerate(summary["main_topics"]):
                    with cols[i % len(cols)]:
                        st.markdown(
                            f'<div class="glass-panel" style="text-align:center;"><b>{topic}</b></div>',
                            unsafe_allow_html=True,
                        )

        # ── Tab 2: Key Points ──────────────────────────────────────────────────
        with tabs[1]:
            if summary.get("key_takeaways"):
                st.markdown("### Key Takeaways")
                for pt in summary["key_takeaways"]:
                    st.markdown(f"- {pt}")

            if summary.get("dates_and_figures"):
                st.markdown("### Important Dates & Figures")
                for item in summary["dates_and_figures"]:
                    st.markdown(f"- {item}")

            if summary.get("action_items"):
                st.markdown("### Action Items / Recommendations")
                st.caption("*Only listed when explicitly supported by the document.*")
                for item in summary["action_items"]:
                    st.markdown(f"- {item}")

            if summary.get("source_pages"):
                pages_str = ", ".join(str(p) for p in summary["source_pages"])
                st.caption(f"📄 Source pages referenced: {pages_str}")

        # ── Tab 3: Details ─────────────────────────────────────────────────────
        with tabs[2]:
            if summary.get("important_definitions"):
                st.markdown("### Key Definitions")
                for defn in summary["important_definitions"]:
                    if isinstance(defn, dict):
                        term = defn.get("term", "")
                        defi = defn.get("definition", "")
                        if term:
                            st.markdown(f"**{term}** — {defi}")
                    else:
                        st.markdown(f"- {defn}")
            else:
                st.info("No definitions were identified in this document.")

            chunks_used = summary.get("chunk_count_used", 0)
            total_chunks = summary.get("total_chunks", 0)
            if total_chunks:
                st.caption(
                    f"Summary used {chunks_used} of {total_chunks} chunks. "
                    "For very long documents, a representative sample is used."
                )

        # ── Tab 4: Export ──────────────────────────────────────────────────────
        with tabs[3]:
            st.markdown("### Export Summary")

            # Build Markdown text
            md_lines = [
                f"# Summary: {summary_doc}\n",
                f"## Executive Summary\n{summary.get('executive_summary','')}\n",
            ]
            if summary.get("key_takeaways"):
                md_lines.append("## Key Takeaways\n" +
                                 "\n".join(f"- {t}" for t in summary["key_takeaways"]) + "\n")
            if summary.get("main_topics"):
                md_lines.append("## Main Topics\n" +
                                 "\n".join(f"- {t}" for t in summary["main_topics"]) + "\n")
            if summary.get("important_definitions"):
                md_lines.append("## Definitions\n")
                for d in summary["important_definitions"]:
                    if isinstance(d, dict):
                        md_lines.append(f"- **{d.get('term','')}**: {d.get('definition','')}\n")
                    else:
                        md_lines.append(f"- {d}\n")
            if summary.get("dates_and_figures"):
                md_lines.append("## Dates & Figures\n" +
                                 "\n".join(f"- {t}" for t in summary["dates_and_figures"]) + "\n")
            if summary.get("action_items"):
                md_lines.append("## Action Items\n" +
                                 "\n".join(f"- {t}" for t in summary["action_items"]) + "\n")

            md_text = "\n".join(md_lines)

            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "📥 Download as Markdown",
                    data=md_text,
                    file_name=f"summary_{summary_doc.replace(' ','_')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with c2:
                st.download_button(
                    "📥 Download as TXT",
                    data=md_text.replace("#", "").replace("**", "").replace("*", ""),
                    file_name=f"summary_{summary_doc.replace(' ','_')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            st.text_area("Preview (Markdown)", md_text, height=300)

elif not run_btn:
    st.markdown(
        """
        <div class="empty-state" style="padding:2rem;">
            <div class="empty-state-icon">📝</div>
            <div class="empty-state-title">No summary generated yet</div>
            <div class="empty-state-text">
                Select a document above and click "Generate Summary".
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
