"""
components/charts.py — Plotly chart builders for the Analytics page
Aurora Mint Edition with Fresh Mint, Deep Jade, Sky Blue, Violet, Emerald, and Lemon palette.

All charts use real data fetched from analytics.py.
Every function returns a Plotly Figure object (or None on empty data).
"""

from typing import Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ALFRED AI Aurora Mint Color Palette
JADE     = "#155E52"
MINT     = "#65C9A7"
SKY_BLUE = "#65B8F5"
VIOLET   = "#A99AF7"
EMERALD  = "#32B985"
LEMON    = "#E5D95B"
CORAL    = "#F87171"
TEXT     = "#20372F"
MUTED    = "#62786D"
BORDER   = "#D3E3D8"
GRID     = "#E5F0E8"
CARD_BG  = "#FFFFFF"

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=CARD_BG,
    font=dict(color=TEXT, family="Inter, -apple-system, sans-serif", size=12),
    margin=dict(l=40, r=20, t=45, b=40),
    colorway=[JADE, MINT, SKY_BLUE, VIOLET, EMERALD, LEMON],
)


def pages_per_doc_chart(doc_stats: list[dict]) -> Optional[go.Figure]:
    """Horizontal bar chart: pages per document with Jade-Mint gradient."""
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
            colorscale=[[0, MINT], [1, JADE]],
            showscale=False,
            line=dict(color=BORDER, width=1),
        ),
        hovertemplate="<b>%{y}</b><br>Pages: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Pages per Document</b>", font=dict(color=TEXT, size=14)),
        xaxis=dict(title="Page Count", gridcolor=GRID, zerolinecolor=GRID),
        yaxis=dict(title="", gridcolor=GRID),
        **PLOTLY_THEME,
    )
    return fig


def chunks_per_doc_chart(doc_stats: list[dict]) -> Optional[go.Figure]:
    """Horizontal bar chart: extracted chunks per document in Soft Violet."""
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
        marker=dict(
            color=VIOLET,
            line=dict(color=BORDER, width=1),
        ),
        hovertemplate="<b>%{y}</b><br>Chunks: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Chunks per Document</b>", font=dict(color=TEXT, size=14)),
        xaxis=dict(title="Chunk Count", gridcolor=GRID, zerolinecolor=GRID),
        yaxis=dict(title="", gridcolor=GRID),
        **PLOTLY_THEME,
    )
    return fig


def status_donut_chart(status_dist: dict[str, int]) -> Optional[go.Figure]:
    """Donut chart: document processing status distribution."""
    if not status_dist:
        return None

    color_map = {
        "indexed":  EMERALD,
        "pending":  LEMON,
        "indexing": SKY_BLUE,
        "error":    CORAL,
    }

    labels = list(status_dist.keys())
    values = list(status_dist.values())
    colors = [color_map.get(l, MUTED) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=3)),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        textinfo="label+value",
        textfont=dict(color=TEXT, size=12),
    ))
    fig.update_layout(
        title=dict(text="<b>Document Ingestion Status</b>", font=dict(color=TEXT, size=14)),
        showlegend=True,
        legend=dict(font=dict(color=TEXT), orientation="h", yanchor="bottom", y=-0.2),
        **PLOTLY_THEME,
    )
    return fig


def query_timeline_chart(timeline: list[dict]) -> Optional[go.Figure]:
    """Bar chart: questions asked per day in Fresh Mint with Deep Jade outline."""
    if not timeline:
        return None
    df = pd.DataFrame(timeline)
    if df["count"].sum() == 0:
        return None

    fig = go.Figure(go.Bar(
        x=df["date"],
        y=df["count"],
        marker=dict(color=MINT, line=dict(color=JADE, width=1.5)),
        hovertemplate="<b>%{x}</b><br>Queries: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Queries per Day (last 30 days)</b>", font=dict(color=TEXT, size=14)),
        xaxis=dict(title="Date", tickangle=-30, gridcolor=GRID),
        yaxis=dict(title="Query Count", gridcolor=GRID, zerolinecolor=GRID),
        **PLOTLY_THEME,
    )
    return fig


def score_histogram(scores: list[float]) -> Optional[go.Figure]:
    """Histogram of retrieval similarity scores in Clear Sky Blue."""
    if not scores:
        return None

    fig = go.Figure(go.Histogram(
        x=scores,
        nbinsx=20,
        marker=dict(color=SKY_BLUE, opacity=0.9, line=dict(color="#FFFFFF", width=1.5)),
        hovertemplate="Score: %{x:.3f}<br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Retrieval Similarity Score Distribution</b>", font=dict(color=TEXT, size=14)),
        xaxis=dict(title="Cosine Similarity Score", gridcolor=GRID),
        yaxis=dict(title="Frequency", gridcolor=GRID),
        **PLOTLY_THEME,
    )
    return fig


def evaluation_bar_chart(eval_results: list[dict]) -> Optional[go.Figure]:
    """Compare Hit Rate and MRR across evaluation runs in Deep Jade & Fresh Mint."""
    if not eval_results:
        return None

    runs  = [f"Run {i+1}" for i in range(len(eval_results))]
    hits  = [r.get("hit_rate", 0) for r in eval_results]
    mrrs  = [r.get("mrr", 0)      for r in eval_results]

    fig = go.Figure([
        go.Bar(name="Hit Rate@k", x=runs, y=hits, marker=dict(color=JADE, line=dict(color=BORDER, width=1))),
        go.Bar(name="MRR",        x=runs, y=mrrs, marker=dict(color=MINT, line=dict(color=BORDER, width=1))),
    ])
    fig.update_layout(
        barmode="group",
        title=dict(text="<b>Evaluation Benchmark Metrics</b>", font=dict(color=TEXT, size=14)),
        yaxis=dict(title="Score", range=[0, 1], gridcolor=GRID),
        xaxis=dict(gridcolor=GRID),
        legend=dict(font=dict(color=TEXT)),
        **PLOTLY_THEME,
    )
    return fig
