"""Unit tests for retrieval metric computation (retrieval_metrics.py).

Tests cover:
- compute_hit_rate_at_k and compute_mrr helpers
- compute_case_retrieval_metrics (with and without doc_id expectations)
- compute_retrieval_comparison_summary (aggregation)
- summarize_wrong_cases (failure classification)
- Edge cases: empty lists, no matches, all matches, missing doc_ids
"""

from __future__ import annotations

import pytest

from ticketpilot.evaluation.retrieval_metrics import (
    DEFAULT_KS,
    RetrievedDoc,
    RetrievalComparisonCase,
    compute_case_retrieval_metrics,
    compute_hit_rate_at_k,
    compute_mrr,
    compute_retrieval_comparison_summary,
    summarize_wrong_cases,
)


# ---------------------------------------------------------------------------
# Helper: build RetrievedDoc lists
# ---------------------------------------------------------------------------


def _doc(
    doc_id: str,
    doc_type: str = "FAQ",
    rank: int = 1,
    score: float = 1.0,
) -> RetrievedDoc:
    return RetrievedDoc(doc_id=doc_id, doc_type=doc_type, rank=rank, score=score)


def _make_retrieved(entries: list[tuple[str, str, int]]) -> list[RetrievedDoc]:
    """Build RetrievedDoc list from (doc_id, doc_type, rank) tuples."""
    return [RetrievedDoc(doc_id=did, doc_type=dt, rank=r, score=1.0 / r) for did, dt, r in entries]


def _case(
    case_id: str = "test_001",
    retrieved: list[RetrievedDoc] | None = None,
    expected_doc_types: frozenset[str] | None = None,
    expected_doc_ids: frozenset[str] | None = None,
) -> RetrievalComparisonCase:
    return RetrievalComparisonCase(
        case_id=case_id,
        query="test query",
        retrieved_docs=retrieved or [],
        expected_doc_types=expected_doc_types or frozenset(),
        expected_doc_ids=expected_doc_ids,
    )


# ---------------------------------------------------------------------------
# Test compute_hit_rate_at_k
# ---------------------------------------------------------------------------


class TestComputeHitRateAtK:
    def test_all_hits(self) -> None:
        assert compute_hit_rate_at_k([True, True, True]) == 1.0

    def test_no_hits(self) -> None:
        assert compute_hit_rate_at_k([False, False]) == 0.0

    def test_mixed(self) -> None:
        assert compute_hit_rate_at_k([True, False, True]) == pytest.approx(2.0 / 3.0)

    def test_single_true(self) -> None:
        assert compute_hit_rate_at_k([True]) == 1.0

    def test_single_false(self) -> None:
        assert compute_hit_rate_at_k([False]) == 0.0

    def test_empty_list(self) -> None:
        assert compute_hit_rate_at_k([]) == 0.0


# ---------------------------------------------------------------------------
# Test compute_mrr
# ---------------------------------------------------------------------------


class TestComputeMRR:
    def test_all_perfect(self) -> None:
        assert compute_mrr([1.0, 1.0, 1.0]) == 1.0

    def test_mixed(self) -> None:
        assert compute_mrr([1.0, 0.5, 0.0]) == pytest.approx(0.5)

    def test_all_zero(self) -> None:
        assert compute_mrr([0.0, 0.0]) == 0.0

    def test_single_value(self) -> None:
        assert compute_mrr([0.5]) == 0.5

    def test_empty_list(self) -> None:
        assert compute_mrr([]) == 0.0


# ---------------------------------------------------------------------------
# Test compute_case_retrieval_metrics
# ---------------------------------------------------------------------------


class TestComputeCaseRetrievalMetrics:
    def test_perfect_doc_type_hit(self) -> None:
        """Expected doc_type appears at rank 1."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
            ("doc_pol_001", "Policy", 2),
            ("doc_case_001", "Case", 3),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset(["FAQ"]))
        metrics = compute_case_retrieval_metrics(case)

        assert metrics.top_k_doc_type_hit[1] is True
        assert metrics.top_k_doc_type_hit[3] is True
        assert metrics.reciprocal_rank_doc_type == 1.0

    def test_doc_type_at_rank_3(self) -> None:
        """Expected doc_type appears at rank 3 — misses top-1, hits top-3."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
            ("doc_faq_002", "FAQ", 2),
            ("doc_pol_001", "Policy", 3),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset(["Policy"]))
        metrics = compute_case_retrieval_metrics(case)

        assert metrics.top_k_doc_type_hit[1] is False
        assert metrics.top_k_doc_type_hit[3] is True
        assert metrics.reciprocal_rank_doc_type == pytest.approx(1.0 / 3.0)

    def test_no_match(self) -> None:
        """No expected doc_type in results."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
            ("doc_pol_001", "Policy", 2),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset(["Case"]))
        metrics = compute_case_retrieval_metrics(case)

        assert all(not metrics.top_k_doc_type_hit[k] for k in DEFAULT_KS)
        assert metrics.reciprocal_rank_doc_type == 0.0

    def test_empty_retrieved(self) -> None:
        """No retrieved docs at all."""
        case = _case(retrieved=[], expected_doc_types=frozenset(["FAQ"]))
        metrics = compute_case_retrieval_metrics(case)

        assert all(not metrics.top_k_doc_type_hit[k] for k in DEFAULT_KS)
        assert metrics.reciprocal_rank_doc_type == 0.0

    def test_empty_expected_types(self) -> None:
        """No expected doc types — all hits vacuously true."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset())
        metrics = compute_case_retrieval_metrics(case)

        # None of the retrieved docs match an empty expected set
        assert all(not metrics.top_k_doc_type_hit[k] for k in DEFAULT_KS)
        assert metrics.reciprocal_rank_doc_type == 0.0

    def test_doc_id_hit(self) -> None:
        """Expected doc_id appears at rank 2."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
            ("doc_faq_002", "FAQ", 2),
            ("doc_pol_001", "Policy", 3),
        ])
        case = _case(
            retrieved=retrieved,
            expected_doc_types=frozenset(["FAQ"]),
            expected_doc_ids=frozenset(["doc_faq_002"]),
        )
        metrics = compute_case_retrieval_metrics(case)

        assert metrics.top_k_doc_id_hit is not None
        assert metrics.top_k_doc_id_hit[1] is False
        assert metrics.top_k_doc_id_hit[3] is True
        assert metrics.reciprocal_rank_doc_id == pytest.approx(1.0 / 2.0)

    def test_doc_id_not_provided(self) -> None:
        """When expected_doc_ids is None, doc_id metrics should be None."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset(["FAQ"]))
        metrics = compute_case_retrieval_metrics(case)

        assert metrics.top_k_doc_id_hit is None
        assert metrics.reciprocal_rank_doc_id is None

    def test_empty_doc_id_set_is_skipped(self) -> None:
        """When expected_doc_ids is empty frozenset, doc_id metrics are None."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
        ])
        case = _case(
            retrieved=retrieved,
            expected_doc_types=frozenset(["FAQ"]),
            expected_doc_ids=frozenset(),
        )
        metrics = compute_case_retrieval_metrics(case)

        assert metrics.top_k_doc_id_hit is None
        assert metrics.reciprocal_rank_doc_id is None

    def test_multiple_expected_doc_types(self) -> None:
        """Multiple expected doc types — hit if any appears."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
            ("doc_pol_001", "Policy", 2),
            ("doc_case_001", "Case", 3),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset(["Policy", "Case"]))
        metrics = compute_case_retrieval_metrics(case)

        assert metrics.top_k_doc_type_hit[1] is False  # FAQ not expected
        assert metrics.top_k_doc_type_hit[3] is True  # Policy at rank 2
        assert metrics.reciprocal_rank_doc_type == pytest.approx(1.0 / 2.0)

    def test_custom_ks(self) -> None:
        """Custom k values produce correct hit dict."""
        retrieved = _make_retrieved([
            ("doc_faq_001", "FAQ", 1),
            ("doc_faq_002", "FAQ", 2),
            ("doc_faq_003", "FAQ", 3),
            ("doc_faq_004", "FAQ", 4),
            ("doc_pol_001", "Policy", 5),
        ])
        case = _case(retrieved=retrieved, expected_doc_types=frozenset(["Policy"]))
        metrics = compute_case_retrieval_metrics(case, ks=[1, 3, 5])

        assert metrics.top_k_doc_type_hit == {1: False, 3: False, 5: True}


# ---------------------------------------------------------------------------
# Test compute_retrieval_comparison_summary
# ---------------------------------------------------------------------------


class TestComputeRetrievalComparisonSummary:
    def test_empty_cases(self) -> None:
        summary = compute_retrieval_comparison_summary([])
        assert summary.total_cases == 0
        assert all(v == 0.0 for v in summary.hit_rate_doc_type.values())

    def test_all_perfect(self) -> None:
        cases = [
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
            ),
            _case(
                case_id="case_002",
                retrieved=_make_retrieved([("doc_pol_001", "Policy", 1)]),
                expected_doc_types=frozenset(["Policy"]),
            ),
        ]
        summary = compute_retrieval_comparison_summary(cases)

        assert summary.total_cases == 2
        assert summary.hit_rate_doc_type[1] == 1.0
        assert summary.mrr_doc_type == 1.0
        assert len(summary.wrong_cases) == 0

    def test_mixed_results(self) -> None:
        cases = [
            # case_001: FAQ at rank 1, expected FAQ -> hit at all k
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
            ),
            # case_002: all FAQ results, expected Policy -> never hits
            _case(
                case_id="case_002",
                retrieved=_make_retrieved([
                    ("doc_faq_002", "FAQ", 1),
                    ("doc_faq_003", "FAQ", 2),
                ]),
                expected_doc_types=frozenset(["Policy"]),
            ),
            # case_003: Policy at rank 3 -> miss at k=1, hit at k>=3
            _case(
                case_id="case_003",
                retrieved=_make_retrieved([
                    ("doc_faq_004", "FAQ", 1),
                    ("doc_faq_005", "FAQ", 2),
                    ("doc_pol_001", "Policy", 3),
                ]),
                expected_doc_types=frozenset(["Policy"]),
            ),
        ]
        summary = compute_retrieval_comparison_summary(cases)

        assert summary.total_cases == 3
        # case_001 hits, case_002 misses, case_003 misses (Policy at rank 3)
        assert summary.hit_rate_doc_type[1] == pytest.approx(1.0 / 3.0)
        # case_001 hits, case_002 misses, case_003 hits
        assert summary.hit_rate_doc_type[3] == pytest.approx(2.0 / 3.0)
        assert summary.mrr_doc_type == pytest.approx((1.0 + 0.0 + 1.0 / 3.0) / 3.0)

    def test_with_doc_ids(self) -> None:
        """Doc-id metrics computed when all cases provide expected_doc_ids."""
        cases = [
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
                expected_doc_ids=frozenset(["doc_faq_001"]),
            ),
            _case(
                case_id="case_002",
                retrieved=_make_retrieved([
                    ("doc_faq_002", "FAQ", 1),
                    ("doc_pol_001", "Policy", 2),
                ]),
                expected_doc_types=frozenset(["Policy"]),
                expected_doc_ids=frozenset(["doc_pol_001"]),
            ),
        ]
        summary = compute_retrieval_comparison_summary(cases)

        assert summary.hit_rate_doc_id is not None
        assert summary.hit_rate_doc_id[1] == 0.5  # case_001 hits, case_002 misses
        assert summary.hit_rate_doc_id[3] == 1.0
        assert summary.mrr_doc_id is not None
        assert summary.mrr_doc_id == pytest.approx((1.0 + 0.5) / 2.0)

    def test_mixed_doc_id_availability(self) -> None:
        """When only some cases have doc_ids, doc_id metrics still computed."""
        cases = [
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
                expected_doc_ids=frozenset(["doc_faq_001"]),
            ),
            _case(
                case_id="case_002",
                retrieved=_make_retrieved([("doc_faq_002", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
                # No doc_ids for this case
            ),
        ]
        summary = compute_retrieval_comparison_summary(cases)

        # Doc-id metrics only computed over cases that have doc_ids
        assert summary.hit_rate_doc_id is not None
        assert summary.hit_rate_doc_id[1] == 1.0  # only case_001 counted

    def test_no_doc_ids_anywhere(self) -> None:
        """When no cases have doc_ids, doc_id metrics are None."""
        cases = [
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
            ),
        ]
        summary = compute_retrieval_comparison_summary(cases)

        assert summary.hit_rate_doc_id is None
        assert summary.mrr_doc_id is None

    def test_per_case_results_preserved(self) -> None:
        """All case_ids are present in the per_case dict with correct metrics."""
        cases = [
            _case(
                case_id="case_a",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
            ),
            _case(
                case_id="case_b",
                retrieved=_make_retrieved([("doc_pol_001", "Policy", 2)]),
                expected_doc_types=frozenset(["Policy"]),
            ),
        ]
        summary = compute_retrieval_comparison_summary(cases)

        assert set(summary.per_case.keys()) == {"case_a", "case_b"}
        assert summary.per_case["case_a"].reciprocal_rank_doc_type == 1.0
        assert summary.per_case["case_b"].reciprocal_rank_doc_type == 0.5


# ---------------------------------------------------------------------------
# Test summarize_wrong_cases
# ---------------------------------------------------------------------------


class TestSummarizeWrongCases:
    def test_no_wrong_cases(self) -> None:
        """All cases have expected doc_type in top-10."""
        cases = [
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
            ),
        ]
        wrong = summarize_wrong_cases(cases)
        assert len(wrong) == 0

    def test_missing_doc_type(self) -> None:
        """Expected doc_type never appears in results."""
        cases = [
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([
                    ("doc_faq_001", "FAQ", 1),
                    ("doc_faq_002", "FAQ", 2),
                ]),
                expected_doc_types=frozenset(["Policy"]),
            ),
        ]
        wrong = summarize_wrong_cases(cases)

        assert len(wrong) == 1
        assert wrong[0].case_id == "case_001"
        assert wrong[0].failure_mode == "missing_doc_type"

    def test_below_top_10(self) -> None:
        """Expected doc_type exists but not in top-10."""
        retrieved = _make_retrieved([("doc_faq_001", "FAQ", 1)])
        # Only 1 retrieved doc and it's not the expected type
        case = _case(
            case_id="case_001",
            retrieved=retrieved,
            expected_doc_types=frozenset(["Policy"]),
        )
        wrong = summarize_wrong_cases([case])

        assert len(wrong) == 1
        assert wrong[0].case_id == "case_001"

    def test_classification_counts(self) -> None:
        """Multiple wrong cases are correctly counted by failure mode."""
        cases = [
            # missing_doc_type
            _case(
                case_id="case_001",
                retrieved=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
                expected_doc_types=frozenset(["Policy"]),
            ),
            # missing_doc_type
            _case(
                case_id="case_002",
                retrieved=_make_retrieved([("doc_faq_002", "FAQ", 1)]),
                expected_doc_types=frozenset(["Case"]),
            ),
            # Success case
            _case(
                case_id="case_003",
                retrieved=_make_retrieved([("doc_faq_003", "FAQ", 1)]),
                expected_doc_types=frozenset(["FAQ"]),
            ),
        ]
        wrong = summarize_wrong_cases(cases)

        assert len(wrong) == 2
        assert all(w.failure_mode == "missing_doc_type" for w in wrong)
