"""Tests for retrieve_evidence wrapper — uses mocked hybrid_retrieval."""

import uuid
from unittest.mock import patch

from ticketpilot.retrieval.evidence_mapper import map_fused_to_evidence
from ticketpilot.retrieval.retrieve_evidence import retrieve_evidence
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import FusedResult, RetrievalTrace
from ticketpilot.schema.ticket import IntentClass, RiskFlag


def _make_trace(query, fused_results):
    return RetrievalTrace(
        query=query,
        query_embedding=[0.0] * 384,
        fused_results=fused_results,
        final_evidence_ids=[r.chunk_id for r in fused_results],
        top_k=10,
    )


def _make_fused(rrf_score=0.9):
    return FusedResult(
        chunk_id=uuid.uuid4(),
        doc_id=uuid.uuid4(),
        doc_type=DocType.FAQ,
        content="退款政策说明",
        rrf_score=rrf_score,
        keyword_rank=1,
        keyword_contribution=1.0 / 61,
        vector_rank=2,
        vector_contribution=1.0 / 62,
        sources=["keyword", "vector"],
    )


class TestRetrieveEvidence:
    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_calls_hybrid_retrieval_with_constructed_query(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("退款 退货", [])

        retrieve_evidence("退款申请", IntentClass.REFUND, set(), top_k=10)

        call_args = mock_hybrid.call_args
        assert call_args.kwargs["query"] == "退款申请 退款 退货 退款政策"

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_top_k_passed_through(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("query", [])

        retrieve_evidence("测试", IntentClass.OTHER, set(), top_k=5)

        assert mock_hybrid.call_args.kwargs["top_k"] == 5

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_doc_types_passed_through(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("query", [])
        doc_types = [DocType.FAQ, DocType.POLICY]

        retrieve_evidence("测试", IntentClass.OTHER, set(), doc_types=doc_types)

        assert mock_hybrid.call_args.kwargs["doc_types"] == doc_types

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_returns_evidence_candidates_and_trace_tuple(self, mock_hybrid):
        fused = _make_fused(0.95)
        mock_hybrid.return_value = _make_trace("query", [fused])

        candidates, trace = retrieve_evidence("退款", IntentClass.REFUND, set())

        assert isinstance(candidates, list)
        assert len(candidates) == 1
        assert candidates[0].score == 0.95
        assert isinstance(trace, RetrievalTrace)
        assert trace.fused_results == [fused]

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_empty_retrieval_returns_empty_list_and_trace(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("查询无结果", [])

        candidates, trace = retrieve_evidence("查询无结果", IntentClass.OTHER, set())

        assert candidates == []
        assert isinstance(trace, RetrievalTrace)
        assert trace.fused_results == []
        assert trace.final_evidence_ids == []

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_map_fused_to_evidence_called_on_fused_results(self, mock_hybrid):
        fused = _make_fused(0.88)
        mock_hybrid.return_value = _make_trace("query", [fused])

        expected = map_fused_to_evidence([fused])
        candidates, _ = retrieve_evidence("测试", IntentClass.OTHER, set())

        assert len(candidates) == len(expected)
        assert candidates[0].chunk_id == expected[0].chunk_id
        assert candidates[0].score == expected[0].score

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_no_risk_flag_mutation(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("query", [])
        original_flags = {RiskFlag.COMPENSATION_RISK}
        flags_snapshot = set(original_flags)

        retrieve_evidence("测试", IntentClass.OTHER, flags_snapshot)

        assert flags_snapshot == original_flags
        assert RiskFlag.INSUFFICIENT_EVIDENCE not in flags_snapshot

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_doc_types_default_to_none(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("query", [])

        retrieve_evidence("测试", IntentClass.OTHER, set())

        assert mock_hybrid.call_args.kwargs["doc_types"] is None

    @patch("ticketpilot.retrieval.retrieve_evidence.hybrid_retrieval")
    def test_default_top_k_is_10(self, mock_hybrid):
        mock_hybrid.return_value = _make_trace("query", [])

        retrieve_evidence("测试", IntentClass.OTHER, set())

        assert mock_hybrid.call_args.kwargs["top_k"] == 10
