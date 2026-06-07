"""Unit tests for retrieval trace visualization.

Tests the data-building helpers and the render function with mock data.
"""

from __future__ import annotations

from uuid import uuid4

import pandas as pd
import pytest

from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import (
    FusedResult,
    KeywordResult,
    RetrievalTrace,
    VectorResult,
)
from ticketpilot.review.retrieval_viz import (
    _build_contribution_df,
    _build_results_df,
    render_retrieval_trace,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_trace(
    *,
    n_fused: int = 3,
    query: str = "如何退款",
) -> RetrievalTrace:
    """Build a RetrievalTrace with n_fused fused results."""
    fused = []
    for i in range(n_fused):
        fused.append(
            FusedResult(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                content=f"content chunk {i}",
                rrf_score=0.05 - i * 0.01,
                keyword_rank=i + 1 if i < 2 else None,
                keyword_contribution=1 / (60 + i + 1) if i < 2 else None,
                vector_rank=i + 1,
                vector_contribution=1 / (60 + i + 1),
                sources=["keyword", "vector"] if i < 2 else ["vector"],
            )
        )
    return RetrievalTrace(
        query=query,
        embedding_provider="fake",
        keyword_latency_ms=12,
        vector_latency_ms=8,
        fusion_latency_ms=3,
        total_latency_ms=23,
        fused_results=fused,
    )


def _make_empty_trace() -> RetrievalTrace:
    """Build a RetrievalTrace with no results."""
    return RetrievalTrace(query="empty query")


# ---------------------------------------------------------------------------
# _build_results_df
# ---------------------------------------------------------------------------

class TestBuildResultsDf:
    """Tests for the results DataFrame builder."""

    def test_columns_present(self) -> None:
        trace = _make_trace()
        df = _build_results_df(trace)
        expected = {"chunk_id", "doc_type", "keyword_rank", "vector_rank", "rrf_score", "sources"}
        assert set(df.columns) == expected

    def test_row_count_matches_fused(self) -> None:
        trace = _make_trace(n_fused=5)
        df = _build_results_df(trace)
        assert len(df) == 5

    def test_empty_trace_returns_empty_df(self) -> None:
        trace = _make_empty_trace()
        df = _build_results_df(trace)
        assert len(df) == 0

    def test_doc_type_is_string_value(self) -> None:
        trace = _make_trace(n_fused=1)
        df = _build_results_df(trace)
        assert df.iloc[0]["doc_type"] == "FAQ"

    def test_sources_dashed_when_empty(self) -> None:
        trace = RetrievalTrace(
            query="q",
            fused_results=[
                FusedResult(
                    chunk_id=uuid4(),
                    doc_id=uuid4(),
                    doc_type=DocType.POLICY,
                    content="c",
                    rrf_score=0.01,
                    sources=[],
                ),
            ],
        )
        df = _build_results_df(trace)
        assert df.iloc[0]["sources"] == "-"

    def test_rrf_score_rounded(self) -> None:
        trace = _make_trace(n_fused=1)
        df = _build_results_df(trace)
        score = df.iloc[0]["rrf_score"]
        # Should be rounded to 6 decimal places
        assert isinstance(score, float)
        assert len(str(score).split(".")[-1]) <= 6


# ---------------------------------------------------------------------------
# _build_contribution_df
# ---------------------------------------------------------------------------

class TestBuildContributionDf:
    """Tests for the contribution DataFrame builder."""

    def test_index_is_result_label(self) -> None:
        trace = _make_trace(n_fused=2)
        df = _build_contribution_df(trace)
        assert "keyword" in df.columns
        assert "vector" in df.columns
        assert len(df) == 2

    def test_empty_trace_returns_empty_df(self) -> None:
        trace = _make_empty_trace()
        df = _build_contribution_df(trace)
        assert len(df) == 0

    def test_missing_contribution_defaulted_to_zero(self) -> None:
        trace = RetrievalTrace(
            query="q",
            fused_results=[
                FusedResult(
                    chunk_id=uuid4(),
                    doc_id=uuid4(),
                    doc_type=DocType.CASE,
                    content="c",
                    rrf_score=0.01,
                    keyword_rank=None,
                    keyword_contribution=None,
                    vector_rank=1,
                    vector_contribution=0.016,
                    sources=["vector"],
                ),
            ],
        )
        df = _build_contribution_df(trace)
        assert df.iloc[0]["keyword"] == 0.0
        assert df.iloc[0]["vector"] == pytest.approx(0.016)

    def test_both_contributions_present(self) -> None:
        trace = _make_trace(n_fused=1)
        df = _build_contribution_df(trace)
        assert df.iloc[0]["keyword"] > 0
        assert df.iloc[0]["vector"] > 0


# ---------------------------------------------------------------------------
# render_retrieval_trace (smoke test)
# ---------------------------------------------------------------------------

class TestRenderRetrievalTrace:
    """Smoke tests — verify the render function does not raise."""

    @pytest.mark.parametrize("n_fused", [0, 1, 5])
    def test_render_does_not_raise(self, n_fused: int) -> None:
        """render_retrieval_trace should not raise for any result count."""
        import streamlit as st

        trace = _make_trace(n_fused=n_fused) if n_fused > 0 else _make_empty_trace()
        # st.delta_generator.DeltaGenerator methods are no-ops in test context
        # We just verify the function executes without error
        render_retrieval_trace(trace)

    def test_render_with_reranking(self) -> None:
        trace = RetrievalTrace(
            query="退款",
            embedding_provider="openai",
            reranking_enabled=True,
            rerank_latency_ms=15,
            fused_results=[
                FusedResult(
                    chunk_id=uuid4(),
                    doc_id=uuid4(),
                    doc_type=DocType.FAQ,
                    content="c",
                    rrf_score=0.02,
                    keyword_rank=1,
                    keyword_contribution=0.016,
                    vector_rank=2,
                    vector_contribution=0.015,
                    sources=["keyword", "vector"],
                ),
            ],
        )
        render_retrieval_trace(trace)
