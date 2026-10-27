"""
pages/4_Analytics.py — Analytics Dashboard
Aurora Mint Edition with Colorful, Real-Time Business Intelligence

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
from components.assets_loader import get_asset_uri
from config import APP_NAME

st.set_page_config(
    page_title=f"Analytics — {APP_NAME}",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        aurora_uri = get_asset_uri("alfred_aurora_bg.jpg")
        css_text = p.read_text(encoding="utf-8")
        extra_vars = f":root {{ --bg-aurora-uri: url('{aurora_uri}'); }}" if aurora_uri else ""
        st.markdown(f"<style>{extra_vars}\n{css_text}</style>", unsafe_allow_html=True)

load_css()
render_sidebar(active_page="Analytics")

st.markdown(
    """
    <div class="page-title">Workspace Analytics</div>
    <div class="page-subtitle">Real-time retrieval metrics, ingestion distributions, and model performance.</div>
    """,
    unsafe_allow_html=True,
)

# ── Load data ──────────────────────────────────────────────────────────────────
doc_stats    = analytics.get_document_stats()
status_dist  = analytics.get_status_distribution()
query_tl     = analytics.get_query_timeline(days=30)
insights     = analytics.get_insights()
eval_history = analytics.get_evaluation_history()

# ── Colorful Semantic Insight cards ───────────────────────────────────────────
ic1, ic2, ic3, ic4 = st.columns(4)
cards = [
    (ic1, insights["total_indexed_pages"],  "Indexed Pages",   "card-sky-blue", "#65B8F5"),
    (ic2, insights["total_indexed_chunks"], "Indexed Chunks",  "card-violet",   "#A99AF7"),
    (ic3, insights["total_queries"],         "Total Queries",   "card-emerald",  "#32B985"),
    (ic4, insights.get("most_recent_doc") or "—", "Latest Document", "card-mint-hero", "#155E52"),
]
for col, val, label, card_cls, accent_col in cards:
    with col:
        display_val = f"{val:,}" if isinstance(val, int) else str(val)
        if card_cls == "card-mint-hero":
            st.markdown(
                f"""
                <div class="metric-box card-mint-hero" style="padding:1.1rem 1.25rem;">
                    <div class="metric-label" style="margin-bottom:0.3rem;">{label}</div>
                    <div class="metric-value" style="font-size:1.4rem; margin-bottom:0.2rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{display_val}</div>
                    <div class="metric-footnote">Most recent intake</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="metric-box {card_cls}" style="padding:1.1rem 1.25rem;">
                    <div class="metric-label" style="margin-bottom:0.3rem;">{label}</div>
                    <div class="metric-value" style="font-size:1.8rem; margin-bottom:0.2rem;">{display_val}</div>
                    <div class="metric-footnote">Verified real data</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

if not doc_stats:
    st.markdown(
        """
        <div class="panel-empty-state" style="background:#FFFFFF; border:1px solid var(--border-delicate); border-radius:14px; padding:3rem 1rem;">
            <div class="panel-empty-icon-circle">📊</div>
            <div class="panel-empty-title">No analytics data yet</div>
            <div class="panel-empty-sub">
                Upload and index documents on the Dashboard, then ask questions in Chat.
                Charts will automatically populate using your verified corporate data.
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
st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
st.markdown("<h3 style='color:var(--text-deep-forest); font-size:1.15rem; font-weight:800;'>Document Ingestion Ledger</h3>", unsafe_allow_html=True)

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
