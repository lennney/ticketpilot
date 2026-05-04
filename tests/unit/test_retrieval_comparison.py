"""Unit tests for the retrieval comparison report builder (retrieval_comparison.py).

Tests cover:
- comparison_summary_to_dict serialization
- comparison_summary_to_markdown content
- JSON report file writing
- Markdown report file writing
- Edge cases: empty summary, no wrong cases, doc_id metrics present
"""

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from ticketpilot.evaluation.retrieval_comparison import (
    comparison_summary_to_dict,
    comparison_summary_to_markdown,
    write_json_report,
    write_markdown_report,
)
from ticketpilot.evaluation.retrieval_metrics import (
    RetrievedDoc,
    RetrievalComparisonCase,
    RetrievalComparisonSummary,
    compute_retrieval_comparison_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_retrieved(entries: list[tuple[str, str, int]]) -> list[RetrievedDoc]:
    """Build RetrievedDoc list from (doc_id, doc_type, rank) tuples."""
    return [RetrievedDoc(doc_id=did, doc_type=dt, rank=r, score=1.0 / r) for did, dt, r in entries]


def _make_cases() -> list[RetrievalComparisonCase]:
    """Build a mini set of 3 comparison cases with 1 failure."""
    return [
        RetrievalComparisonCase(
            case_id="case_001",
            query="refund status",
            retrieved_docs=_make_retrieved([
                ("doc_faq_001", "FAQ", 1),
                ("doc_pol_001", "Policy", 2),
            ]),
            expected_doc_types=frozenset(["FAQ"]),
        ),
        RetrievalComparisonCase(
            case_id="case_002",
            query="return policy",
            retrieved_docs=_make_retrieved([
                ("doc_faq_002", "FAQ", 1),
                ("doc_pol_002", "Policy", 3),
            ]),
            expected_doc_types=frozenset(["Policy", "Case"]),
        ),
        RetrievalComparisonCase(
            case_id="case_003",
            query="complaint",
            retrieved_docs=_make_retrieved([
                ("doc_faq_003", "FAQ", 1),
                ("doc_faq_004", "FAQ", 2),
            ]),
            expected_doc_types=frozenset(["Case"]),
        ),
    ]


def _make_cases_with_doc_ids() -> list[RetrievalComparisonCase]:
    """Same cases but with doc_id golden expectations."""
    return [
        RetrievalComparisonCase(
            case_id="case_001",
            query="refund status",
            retrieved_docs=_make_retrieved([
                ("doc_faq_001", "FAQ", 1),
                ("doc_pol_001", "Policy", 2),
            ]),
            expected_doc_types=frozenset(["FAQ"]),
            expected_doc_ids=frozenset(["doc_faq_001"]),
        ),
        RetrievalComparisonCase(
            case_id="case_003",
            query="complaint",
            retrieved_docs=_make_retrieved([
                ("doc_faq_003", "FAQ", 1),
                ("doc_faq_004", "FAQ", 2),
            ]),
            expected_doc_types=frozenset(["Case"]),
            expected_doc_ids=frozenset(["doc_case_001"]),
        ),
    ]


@pytest.fixture
def sample_summary() -> RetrievalComparisonSummary:
    return compute_retrieval_comparison_summary(_make_cases())


@pytest.fixture
def summary_with_doc_ids() -> RetrievalComparisonSummary:
    return compute_retrieval_comparison_summary(_make_cases_with_doc_ids())


@pytest.fixture
def summary_no_cases() -> RetrievalComparisonSummary:
    return compute_retrieval_comparison_summary([])


# ---------------------------------------------------------------------------
# Test comparison_summary_to_dict
# ---------------------------------------------------------------------------


class TestComparisonSummaryToDict:
    def test_expected_keys_present(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        assert "generated_at" in data
        assert "metadata" in data
        assert "config" in data
        assert "total_cases" in data
        assert "aggregate_metrics" in data
        assert "per_case_results" in data
        assert "wrong_cases" in data
        assert "wrong_case_count" in data

    def test_total_cases(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        assert data["total_cases"] == 3

    def test_aggregate_metrics(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        metrics = data["aggregate_metrics"]
        assert "hit_rate_doc_type" in metrics
        assert "mrr_doc_type" in metrics

    def test_wrong_case_count(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        # case_003 has no Case doc_type -> wrong
        assert data["wrong_case_count"] >= 1

    def test_per_case_results(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        assert "case_001" in data["per_case_results"]
        assert "case_002" in data["per_case_results"]
        assert "case_003" in data["per_case_results"]

    def test_no_doc_id_metrics(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        assert "hit_rate_doc_id" not in data["aggregate_metrics"]
        assert "mrr_doc_id" not in data["aggregate_metrics"]

    def test_with_doc_id_metrics(self, summary_with_doc_ids: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(summary_with_doc_ids)
        assert data["aggregate_metrics"]["hit_rate_doc_id"] is not None
        assert data["aggregate_metrics"]["mrr_doc_id"] is not None

    def test_wrong_cases_have_required_fields(self, sample_summary: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(sample_summary)
        for wc in data["wrong_cases"]:
            assert "case_id" in wc
            assert "failure_mode" in wc
            assert "details" in wc
            assert "top_k_doc_type_hit" in wc
            assert "reciprocal_rank_doc_type" in wc

    def test_empty_summary(self, summary_no_cases: RetrievalComparisonSummary) -> None:
        data = comparison_summary_to_dict(summary_no_cases)
        assert data["total_cases"] == 0
        assert data["wrong_case_count"] == 0
        assert data["per_case_results"] == {}


# ---------------------------------------------------------------------------
# Test comparison_summary_to_markdown
# ---------------------------------------------------------------------------


class TestComparisonSummaryToMarkdown:
    def test_contains_section_headers(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(sample_summary)
        assert "# Retrieval Comparison Report" in md
        assert "## Dataset" in md
        assert "## Aggregate Metrics" in md
        assert "## Wrong Cases" in md

    def test_contains_total_cases(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(sample_summary)
        assert "3" in md

    def test_tickets_path_included(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(
            sample_summary, tickets_path="data/eval/tickets_eval.csv"
        )
        assert "tickets_eval.csv" in md

    def test_golden_path_included(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(
            sample_summary, golden_path="data/eval/golden_expectations.csv"
        )
        assert "golden_expectations.csv" in md

    def test_config_rendered(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(
            sample_summary, config={"retrieval_mode": "mock", "key": "value"}
        )
        assert "retrieval_mode" in md
        assert "## Configuration" in md

    def test_hit_rate_table_present(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(sample_summary)
        assert "### Top-K Doc Type Hit Rate" in md
        assert "| k | Hit Rate |" in md

    def test_mrr_section_present(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(sample_summary)
        assert "MRR (doc_type)" in md

    def test_wrong_case_details(self, sample_summary: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(sample_summary)
        # case_003 should be listed as a wrong case
        assert "case_003" in md
        assert "missing_doc_type" in md

    def test_no_wrong_cases_message(self) -> None:
        """When there are no wrong cases, show a message instead of details."""
        case = RetrievalComparisonCase(
            case_id="case_001",
            query="test",
            retrieved_docs=_make_retrieved([("doc_faq_001", "FAQ", 1)]),
            expected_doc_types=frozenset(["FAQ"]),
        )
        summary = compute_retrieval_comparison_summary([case])
        md = comparison_summary_to_markdown(summary)
        assert "No retrieval failures detected." in md

    def test_doc_id_mrr_shown(self, summary_with_doc_ids: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(summary_with_doc_ids)
        assert "MRR (doc_id)" in md

    def test_doc_id_hit_rate_shown(self, summary_with_doc_ids: RetrievalComparisonSummary) -> None:
        md = comparison_summary_to_markdown(summary_with_doc_ids)
        assert "Top-K Doc ID Hit Rate" in md


# ---------------------------------------------------------------------------
# Test write_json_report
# ---------------------------------------------------------------------------


class TestWriteJsonReport:
    def test_creates_file(self, sample_summary: RetrievalComparisonSummary) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name

        try:
            write_json_report(sample_summary, out_path)
            assert pathlib.Path(out_path).exists()
            data = json.loads(pathlib.Path(out_path).read_text(encoding="utf-8"))
            assert data["total_cases"] == 3
        finally:
            pathlib.Path(out_path).unlink(missing_ok=True)

    def test_creates_parent_dir(self, sample_summary: RetrievalComparisonSummary) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = pathlib.Path(tmpdir) / "sub" / "report.json"
            write_json_report(sample_summary, out_path)
            assert out_path.exists()


# ---------------------------------------------------------------------------
# Test write_markdown_report
# ---------------------------------------------------------------------------


class TestWriteMarkdownReport:
    def test_creates_file(self, sample_summary: RetrievalComparisonSummary) -> None:
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            out_path = f.name

        try:
            result = write_markdown_report(sample_summary, out_path)
            assert pathlib.Path(out_path).exists()
            content = pathlib.Path(out_path).read_text(encoding="utf-8")
            assert result == content
            assert "# Retrieval Comparison Report" in content
        finally:
            pathlib.Path(out_path).unlink(missing_ok=True)

    def test_creates_parent_dir(self, sample_summary: RetrievalComparisonSummary) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = pathlib.Path(tmpdir) / "sub" / "report.md"
            write_markdown_report(sample_summary, out_path)
            assert out_path.exists()
