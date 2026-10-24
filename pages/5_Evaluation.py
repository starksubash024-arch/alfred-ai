"""
pages/5_Evaluation.py — Retrieval Evaluation

Runs automated Hit Rate@k and MRR evaluation against test cases.
Explains exactly what is and isn't measured automatically.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from pathlib import Path
import streamlit as st

from components.sidebar import render_sidebar
from config import APP_NAME, DEFAULT_TOP_K
from evaluation import run_evaluation, load_eval_cases, EVAL_CASES_PATH

st.set_page_config(
    page_title=f"Evaluation — {APP_NAME}",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

def load_css():
    p = Path(__file__).parent.parent / "styles" / "custom.css"
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_css()
render_sidebar()

st.markdown(
    """
    <div class="page-title">🧪 Evaluation</div>
    <div class="page-subtitle">Measure retrieval quality with real test cases.</div>
    """,
    unsafe_allow_html=True,
)

# ── Explanation ────────────────────────────────────────────────────────────────
with st.expander("ℹ️ What is measured here — and what isn't?", expanded=False):
    st.markdown(
        """
        **Automated metrics (computed here):**
        - **Hit Rate @ k** — fraction of test questions where the correct source page
          appears somewhere in the top-k retrieved chunks.
        - **MRR (Mean Reciprocal Rank)** — average of 1/rank; higher when the correct
          page ranks first.

        **Not automatically measured here:**
        - *Answer faithfulness* — whether the generated text accurately reflects the sources.
          This requires human review of each answer.
        - *Factual correctness* — a high retrieval score does not guarantee the answer is correct.

        **How to add test cases:**  
        Edit `evaluation_cases.json` in the project root. Each case needs:
        ```json
        {
          "question": "What is the revenue in 2023?",
          "expected_page": 5,
          "doc_id": "optional-doc-id"
        }
        ```
        """
    )

# ── Load / display test cases ──────────────────────────────────────────────────
cases = load_eval_cases()
st.markdown(f"**Test cases loaded:** {len(cases)}")

if not cases:
    st.info(
        f"No test cases found at `{EVAL_CASES_PATH}`. "
        "Add cases and re-run evaluation."
    )

    st.markdown("### Sample `evaluation_cases.json`")
    sample = [
        {"question": "What is the main conclusion?", "expected_page": 1},
        {"question": "What methodology was used?",   "expected_page": 3},
    ]
    st.code(json.dumps(sample, indent=2), language="json")

    if st.button("📝 Create sample evaluation_cases.json"):
        EVAL_CASES_PATH.write_text(json.dumps(sample, indent=2), encoding="utf-8")
        st.success("Created evaluation_cases.json with sample cases. Edit it with your real questions.")
        st.rerun()
    st.stop()

# ── Run evaluation ─────────────────────────────────────────────────────────────
top_k = st.slider("Top-k for evaluation", 1, 15, DEFAULT_TOP_K, step=1)

if st.button("▶ Run Evaluation", type="primary"):
    with st.spinner(f"Running {len(cases)} test cases…"):
        result = run_evaluation(top_k=top_k)
    st.session_state["eval_result"] = result

result = st.session_state.get("eval_result")

if result:
    if result.get("error"):
        st.error(result["error"])
    else:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Hit Rate @ k", f"{result['hit_rate']:.1%}")
        with m2:
            st.metric("MRR", f"{result['mrr']:.3f}")
        with m3:
            st.metric("Cases run", result["n_cases"])

        st.caption(
            f"Evaluated with top_k={result['top_k']}. "
            "These are retrieval metrics only — not answer quality metrics."
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Per-question Results")

        import pandas as pd
        details = result.get("details", [])
        if details:
            df_data = []
            for d in details:
                df_data.append({
                    "Question":       d["question"][:80],
                    "Expected page":  d["expected_page"],
                    "Hit":            "✅" if d["hit"] else "❌",
                    "RR":             f"{d['rr']:.3f}",
                    "Top pages":      str(d["top_pages"]),
                })
            st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
