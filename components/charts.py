"""
components/charts.py — Plotly chart builders for the Analytics page

All charts use real data fetched from analytics.py.
Every function returns a Plotly Figure object (or None on empty data).
"""

from typing import Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ALFRED AI enterprise colour palette
CRIMSON = "#E5485D"
RUBY    = "#C93B4E"
BLUE    = "#5798F5"
SLATE   = "#777E8B"
GREEN   = "#31B77A"
AMBER   = "#F59E0B"
RED     = "#E5485D"
BG      = "#101114"
CARD    = "#17191F"
TEXT    = "#F4F5F7"
MUTED   = "#A2A7B2"
BORDER  = "#2A2D35"

PLOTLY_THEME = dict(
    paper_bgcolor=BG,
    plot_bgcolor=CARD,
    font=dict(color=TEXT, family="Inter, -apple-system, sans-serif", size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    colorway=[CRIMSON, BLUE, GREEN, SLATE, RUBY],
)


def pages_per_doc_chart(doc_stats: list[dict]) -> Optional[go.Figure]:
    """Bar chart: pages per document."""
    if not doc_stats:
        return None
    df = pd.DataFrame(doc_stats)
    df = df[df["page_count"] > 0].sort_values("page_count", ascending=True)
    if df.empty:
        return None

    fig = go.Figure(go.Bar(
        x=df["page_count"],
        y=df["filename"],
        orientation="h",
        marker=dict(
            color=df["page_count"],
            colorscale=[[0, BLUE], [1, CRIMSON]],
            showscale=False,
        ),
        hovertemplate="<b>%{y}</b><br>Pages: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title="Pages per Document",
        xaxis_title="Page Count",
        yaxis_title="",
        **PLOTLY_THEME,
    )
    return fig


def chunks_per_doc_chart(doc_stats: list[dict]) -> Optional[go.Figure]:
    """Bar chart: extracted chunks per document."""
    if not doc_stats:
        return None
    df = pd.DataFrame(doc_stats)
    df = df[df["chunk_count"] > 0].sort_values("chunk_count", ascending=True)
    if df.empty:
        return None

    fig = go.Figure(go.Bar(
        x=df["chunk_count"],
        y=df["filename"],
        orientation="h",
        marker=dict(color=SLATE),
        hovertemplate="<b>%{y}</b><br>Chunks: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title="Chunks per Document",
        xaxis_title="Chunk Count",
        yaxis_title="",
        **PLOTLY_THEME,
    )
    return fig


def status_donut_chart(status_dist: dict[str, int]) -> Optional[go.Figure]:
    """Donut chart: document processing status distribution."""
    if not status_dist:
        return None

    color_map = {
        "indexed":  GREEN,
        "pending":  ORANGE,
        "indexing": BLUE,
        "error":    RED,
    }

    labels = list(status_dist.keys())
    values = list(status_dist.values())
    colors = [color_map.get(l, MUTED) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=BG, width=2)),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        textinfo="label+value",
        textfont=dict(color=TEXT),
    ))
    fig.update_layout(
        title="Document Status",
        showlegend=True,
        legend=dict(font=dict(color=TEXT)),
        **PLOTLY_THEME,
    )
    return fig


def query_timeline_chart(timeline: list[dict]) -> Optional[go.Figure]:
    """Bar chart: questions asked per day."""
    if not timeline:
        return None
    df = pd.DataFrame(timeline)
    if df["count"].sum() == 0:
        return None

    fig = go.Figure(go.Bar(
        x=df["date"],
        y=df["count"],
        marker=dict(color=BLUE, opacity=0.85),
        hovertemplate="<b>%{x}</b><br>Queries: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title="Queries per Day (last 30 days)",
        xaxis_title="Date",
        yaxis_title="Query Count",
        xaxis=dict(tickangle=-30),
        **PLOTLY_THEME,
    )
    return fig


def score_histogram(scores: list[float]) -> Optional[go.Figure]:
    """Histogram of retrieval similarity scores."""
    if not scores:
        return None

    fig = go.Figure(go.Histogram(
        x=scores,
        nbinsx=20,
        marker=dict(color=CRIMSON, opacity=0.85, line=dict(color=BG, width=1)),
        hovertemplate="Score: %{x:.3f}<br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title="Retrieval Score Distribution",
        xaxis_title="Cosine Similarity Score",
        yaxis_title="Frequency",
        **PLOTLY_THEME,
    )
    return fig


def evaluation_bar_chart(eval_results: list[dict]) -> Optional[go.Figure]:
    """Compare Hit Rate and MRR across evaluation runs."""
    if not eval_results:
        return None

    runs  = [f"Run {i+1}" for i in range(len(eval_results))]
    hits  = [r.get("hit_rate", 0) for r in eval_results]
    mrrs  = [r.get("mrr", 0)      for r in eval_results]

    fig = go.Figure([
        go.Bar(name="Hit Rate@k", x=runs, y=hits, marker_color=CRIMSON),
        go.Bar(name="MRR",        x=runs, y=mrrs, marker_color=BLUE),
    ])
    fig.update_layout(
        barmode="group",
        title="Evaluation Metrics",
        yaxis=dict(title="Score", range=[0, 1]),
        **PLOTLY_THEME,
    )
    return fig
