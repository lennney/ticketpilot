"""Streamlit visualization for RetrievalTrace.

Renders query info, fused results table, and keyword-vs-vector
contribution chart from a RetrievalTrace object.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ticketpilot.retrieval.traces import RetrievalTrace


def _build_results_df(trace: RetrievalTrace) -> pd.DataFrame:
    """Build a DataFrame from fused results for display."""
    rows = []
    for r in trace.fused_results:
        rows.append(
            {
                "chunk_id": str(r.chunk_id)[:8],
                "doc_type": r.doc_type.value,
                "keyword_rank": r.keyword_rank,
                "vector_rank": r.vector_rank,
                "rrf_score": round(r.rrf_score, 6),
                "sources": ", ".join(r.sources) if r.sources else "-",
            }
        )
    return pd.DataFrame(rows)


def _build_contribution_df(trace: RetrievalTrace) -> pd.DataFrame:
    """Build a DataFrame of keyword vs vector contributions per result."""
    rows = []
    for r in trace.fused_results:
        label = f"{str(r.chunk_id)[:8]} ({r.doc_type.value})"
        rows.append(
            {
                "result": label,
                "keyword": r.keyword_contribution or 0.0,
                "vector": r.vector_contribution or 0.0,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.set_index("result")
    return df


def render_retrieval_trace(trace: RetrievalTrace) -> None:
    """Render a RetrievalTrace as a Streamlit component.

    Shows three sections:
    1. Query Info — query text, embedding provider, latency breakdown
    2. Results Table — fused results with ranks, RRF scores, sources
    3. Contribution Chart — horizontal bar chart of keyword vs vector
       contribution per result

    Args:
        trace: A RetrievalTrace from the retrieval pipeline.
    """
    # --- Section 1: Query Info ---
    st.markdown("#### Query Info")
    col_q, col_p = st.columns([3, 1])
    with col_q:
        st.write(f"**Query:** {trace.query}")
    with col_p:
        st.write(f"**Embedding:** {trace.embedding_provider}")

    col_kw, col_vec, col_fuse, col_total = st.columns(4)
    col_kw.metric("Keyword (ms)", trace.keyword_latency_ms)
    col_vec.metric("Vector (ms)", trace.vector_latency_ms)
    col_fuse.metric("Fusion (ms)", trace.fusion_latency_ms)
    col_total.metric("Total (ms)", trace.total_latency_ms)

    if trace.reranking_enabled:
        st.write(f"**Rerank latency:** {trace.rerank_latency_ms} ms")

    # --- Section 2: Results Table ---
    st.markdown("#### Fused Results")
    if not trace.fused_results:
        st.info("No fused results.")
    else:
        df = _build_results_df(trace)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Section 3: Contribution Chart ---
    st.markdown("#### Keyword vs Vector Contribution")
    if not trace.fused_results:
        st.info("No results to chart.")
    else:
        contrib_df = _build_contribution_df(trace)
        st.bar_chart(contrib_df, horizontal=True)
