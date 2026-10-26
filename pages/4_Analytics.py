"""
pages/4_Analytics.py — Analytics Dashboard

All charts use real data from SQLite / analytics.py.
No fake statistics are ever shown.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
import streamlit as st

import analytics
from components.sidebar import render_sidebar
from components.charts import (
    pages_per_doc_chart,
    chunks_per_doc_chart,
    status_donut_chart,
    query_timeline_chart,
    score_histogram,
    evaluation_bar_chart,
)
from config import APP_NAME

st.set_page_config(
    page_title=f"Analytics — {APP_NAME}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css()
render_sidebar(active_page="Analytics")

st.markdown(
    """
    <div class="page-title">📊 Analytics</div>
    <div class="page-subtitle">Real-time insights from your document workspace.</div>
    """,
    unsafe_allow_html=True,
)

# ── Load data ──────────────────────────────────────────────────────────────────
doc_stats    = analytics.get_document_stats()
status_dist  = analytics.get_status_distribution()
query_tl     = analytics.get_query_timeline(days=30)
insights     = analytics.get_insights()
eval_history = analytics.get_evaluation_history()

# ── Insight cards ──────────────────────────────────────────────────────────────
ic1, ic2, ic3, ic4 = st.columns(4)
cards = [
    (ic1, "📃", insights["total_indexed_pages"],  "Indexed Pages"),
    (ic2, "🧩", insights["total_indexed_chunks"], "Indexed Chunks"),
    (ic3, "❓", insights["total_queries"],         "Total Queries"),
    (ic4, "📄", insights.get("most_recent_doc") or "—", "Latest Document"),
]
for col, icon, val, label in cards:
    with col:
        display_val = f"{val:,}" if isinstance(val, int) else str(val)
        st.markdown(
            f"""
            <div class="kpi-card">
                <span class="kpi-icon">{icon}</span>
                <div class="kpi-value" style="font-size:1.4rem;">{display_val}</div>
                <div class="kpi-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<hr>", unsafe_allow_html=True)

if not doc_stats:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <div class="empty-state-title">No data to display yet</div>
            <div class="empty-state-text">
                Upload and index documents, then ask some questions.
                Charts will appear here using your real data.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Charts row 1 ───────────────────────────────────────────────────────────────
ch1, ch2 = st.columns(2)

with ch1:
    fig = pages_per_doc_chart(doc_stats)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No page data available yet.")

with ch2:
    fig = chunks_per_doc_chart(doc_stats)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No chunk data available yet.")

# ── Charts row 2 ───────────────────────────────────────────────────────────────
ch3, ch4 = st.columns(2)

with ch3:
    fig = status_donut_chart(status_dist)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No status data available yet.")

with ch4:
    fig = query_timeline_chart(query_tl)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No query history yet. Ask some questions in the Chat page.")

# ── Evaluation chart (if data exists) ─────────────────────────────────────────
if eval_history:
    st.markdown("<hr>", unsafe_allow_html=True)
    fig = evaluation_bar_chart(eval_history)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# ── Document details table ─────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("### Document Detail Table")

import pandas as pd
from utils import human_readable_size
import database as db

docs_raw = db.list_documents()
if docs_raw:
    from datetime import datetime
    table_data = []
    for d in docs_raw:
        table_data.append({
            "Filename":   d["filename"],
            "Pages":      d["page_count"],
            "Chunks":     d["chunk_count"],
            "Status":     d["status"],
            "Uploaded":   datetime.fromtimestamp(d["upload_time"]).strftime("%Y-%m-%d %H:%M"),
            "Size":       human_readable_size(d["file_size"]),
        })
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
