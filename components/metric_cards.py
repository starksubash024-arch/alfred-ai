"""
components/metric_cards.py — KPI card rendering helpers
"""

import streamlit as st


def render_kpi_cards(stats: dict) -> None:
    """Render the four KPI cards at the top of the dashboard."""
    c1, c2, c3, c4 = st.columns(4)

    cards = [
        (c1, "📄", stats.get("doc_count",   0), "Documents Indexed",   None),
        (c2, "📃", stats.get("page_total",  0), "Pages Processed",     None),
        (c3, "🧩", stats.get("chunk_total", 0), "Text Chunks",         None),
        (c4, "❓", stats.get("query_count", 0), "Questions This Session", None),
    ]

    for col, icon, value, label, delta in cards:
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <span class="kpi-icon">{icon}</span>
                    <div class="kpi-value">{value:,}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
