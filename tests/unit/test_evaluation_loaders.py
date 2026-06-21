"""Unit tests for evaluation CSV loaders.

Tests cover:
- Valid CSV loading for both tickets and golden expectations
- Joined EvalDataset validation
- Duplicate case_id rejection
- Missing required column rejection
- Unknown issue_type rejection
- Invalid severity rejection
- Boolean parsing
- Semicolon-separated list parsing
- Golden without ticket rejection
- Ticket without golden rejection
- Loader determinism
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

from ticketpilot.evaluation.loaders import (
    load_golden_expectations,
    load_tickets_eval,
    load_eval_dataset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TICKETS_CSV_HEADER = (
    "case_id,original_text,customer_id,submitted_at,scenario_type,notes"
)
GOLDEN_CSV_HEADER = (
    "case_id,expected_issue_type,expected_risk_flags,expected_severity,"
    "expected_must_human_review,expected_evidence_doc_types,"
    "expected_fallback_required,expected_no_auto_send,notes"
)


def _write_csv(path: pathlib.Path, header: str, rows: list[str]) -> None:
    """Write a CSV file with header and rows."""
    with path.open("w", newline="", encoding="utf-8") as f:
        f.write(header + "\n")
        for row in rows:
            f.write(row + "\n")


def _make_valid_tickets(extra_rows: list[str] | None = None) -> list[str]:
    """Return a list of valid ticket CSV rows."""
    rows = [
        "case_refund_001,我要退款,CUST001,2026-05-01T10:00:00Z,refund,Standard refund",
        "case_return_001,我想退货,CUST002,2026-05-01T10:05:00Z,return_exchange,",
        "case_acct_001,账号被冻结,CUST003,2026-05-01T10:10:00Z,account_issue,",
    ]
    if extra_rows:
        rows.extend(extra_rows)
    return rows


def _make_valid_golden(extra_rows: list[str] | None = None) -> list[str]:
    """Return a list of valid golden expectation CSV rows."""
    rows = [
        "case_refund_001,refund,,LOW,false,FAQ,false,false,",
        "case_return_001,return_exchange,,LOW,false,FAQ;POLICY,false,false,",
        "case_acct_001,account_issue,account_security_risk,LOW,true,FAQ;CASE,false,true,",
    ]
    if extra_rows:
        rows.extend(extra_rows)
    return rows


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for CSV files."""
    with tempfile.TemporaryDirectory() as d:
        yield pathlib.Path(d)


@pytest.fixture
def valid_tickets_csv(tmp_dir):
    """Create a valid tickets_eval.csv and return its path."""
    path = tmp_dir / "tickets_eval.csv"
    _write_csv(path, TICKETS_CSV_HEADER, _make_valid_tickets())
    return path


@pytest.fixture
def valid_golden_csv(tmp_dir):
    """Create a valid golden_expectations.csv and return its path."""
    path = tmp_dir / "golden_expectations.csv"
    _write_csv(path, GOLDEN_CSV_HEADER, _make_valid_golden())
    return path


# ---------------------------------------------------------------------------
# Tests: load_tickets_eval
# ---------------------------------------------------------------------------


class TestLoadTicketsEval:
    """Tests for load_tickets_eval()."""

    def test_valid_tickets_loads(self, valid_tickets_csv):
        tickets = load_tickets_eval(str(valid_tickets_csv))
        assert len(tickets) == 3
        assert "case_refund_001" in tickets
        assert "case_return_001" in tickets
        assert "case_acct_001" in tickets

    def test_ticket_fields_populated(self, valid_tickets_csv):
        tickets = load_tickets_eval(str(valid_tickets_csv))
        ticket = tickets["case_refund_001"]
        assert ticket.original_text == "我要退款"
        assert ticket.customer_id == "CUST001"
        assert ticket.submitted_at == "2026-05-01T10:00:00Z"
        assert ticket.scenario_type == "refund"
        assert ticket.notes == "Standard refund"

    def test_optional_fields_default_to_none(self, valid_tickets_csv):
        tickets = load_tickets_eval(str(valid_tickets_csv))
        ticket = tickets["case_return_001"]
        assert ticket.customer_id == "CUST002"
        assert ticket.notes is None  # empty notes become None

    def test_duplicate_case_id_rejected(self, tmp_dir):
        path = tmp_dir / "tickets_eval.csv"
        rows = [
            "case_001,text one,CUST001,2026-05-01T10:00:00Z,refund,",
            "case_001,text two,CUST002,2026-05-01T10:05:00Z,refund,",
        ]
        _write_csv(path, TICKETS_CSV_HEADER, rows)
        with pytest.raises(ValueError, match="duplicate case_id"):
            load_tickets_eval(str(path))

    def test_missing_required_column_rejected(self, tmp_dir):
        path = tmp_dir / "tickets_eval.csv"
        # Missing 'original_text' column
        bad_header = "case_id,customer_id,submitted_at,scenario_type,notes"
        rows = ["case_001,CUST001,2026-05-01T10:00:00Z,refund,"]
        _write_csv(path, bad_header, rows)
        with pytest.raises(ValueError, match="missing required column"):
            load_tickets_eval(str(path))

    def test_empty_case_id_rejected(self, tmp_dir):
        path = tmp_dir / "tickets_eval.csv"
        rows = [",text,CUST001,2026-05-01T10:00:00Z,refund,"]
        _write_csv(path, TICKETS_CSV_HEADER, rows)
        with pytest.raises(ValueError, match="empty or missing"):
            load_tickets_eval(str(path))

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_tickets_eval("/nonexistent/path.csv")


# ---------------------------------------------------------------------------
# Tests: load_golden_expectations
# ---------------------------------------------------------------------------


class TestLoadGoldenExpectations:
    """Tests for load_golden_expectations()."""

    def test_valid_golden_loads(self, valid_golden_csv):
        golden = load_golden_expectations(str(valid_golden_csv))
        assert len(golden) == 3
        assert "case_refund_001" in golden
        assert "case_return_001" in golden
        assert "case_acct_001" in golden

    def test_golden_fields_populated(self, valid_golden_csv):
        golden = load_golden_expectations(str(valid_golden_csv))
        g = golden["case_refund_001"]
        assert g.expected_issue_type == "refund"
        assert g.expected_severity == "LOW"
        assert g.expected_must_human_review is False
        assert g.expected_fallback_required is False
        assert g.expected_no_auto_send is False

    def test_duplicate_case_id_rejected(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        rows = [
            "case_001,refund,,LOW,false,FAQ,false,false,",
            "case_001,complaint,,MEDIUM,true,FAQ,false,true,",
        ]
        _write_csv(path, GOLDEN_CSV_HEADER, rows)
        with pytest.raises(ValueError, match="duplicate case_id"):
            load_golden_expectations(str(path))

    def test_missing_required_column_rejected(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        bad_header = "case_id,expected_issue_type,expected_severity"
        rows = ["case_001,refund,LOW"]
        _write_csv(path, bad_header, rows)
        with pytest.raises(ValueError, match="missing required column"):
            load_golden_expectations(str(path))

    def test_unknown_issue_type_rejected(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        rows = ["case_001,bad_intent,,LOW,false,FAQ,false,false,"]
        _write_csv(path, GOLDEN_CSV_HEADER, rows)
        with pytest.raises(ValueError, match="Unknown issue type"):
            load_golden_expectations(str(path))

    def test_invalid_severity_rejected(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        rows = ["case_001,refund,,CRITICAL,false,FAQ,false,false,"]
        _write_csv(path, GOLDEN_CSV_HEADER, rows)
        with pytest.raises(ValueError, match="Unknown severity"):
            load_golden_expectations(str(path))

    def test_boolean_parsing_from_string(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        rows = [
            "case_001,complaint,,MEDIUM,true,FAQ,false,true,",
            "case_002,refund,,LOW,false,POLICY,false,false,",
        ]
        _write_csv(path, GOLDEN_CSV_HEADER, rows)
        golden = load_golden_expectations(str(path))
        assert golden["case_001"].expected_must_human_review is True
        assert golden["case_001"].expected_no_auto_send is True
        assert golden["case_002"].expected_must_human_review is False
        assert golden["case_002"].expected_no_auto_send is False

    def test_semicolon_risk_flags_parsing(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        rows = [
            "case_001,complaint,complaint_risk;compensation_risk,MEDIUM,true,FAQ,false,true,",
            "case_002,account_issue,account_security_risk,LOW,true,FAQ,false,true,",
        ]
        _write_csv(path, GOLDEN_CSV_HEADER, rows)
        golden = load_golden_expectations(str(path))
        assert golden["case_001"].expected_risk_flags == frozenset(
            {"complaint_risk", "compensation_risk"}
        )
        assert golden["case_002"].expected_risk_flags == frozenset(
            {"account_security_risk"}
        )

    def test_semicolon_evidence_doc_types_parsing(self, tmp_dir):
        path = tmp_dir / "golden.csv"
        rows = [
            "case_001,complaint,,MEDIUM,true,FAQ;POLICY;CASE,false,true,",
        ]
        _write_csv(path, GOLDEN_CSV_HEADER, rows)
        golden = load_golden_expectations(str(path))
        assert golden["case_001"].expected_evidence_doc_types == frozenset(
            {"FAQ", "POLICY", "CASE"}
        )

    def test_empty_list_fields_default_to_frozenset(self, valid_golden_csv):
        golden = load_golden_expectations(str(valid_golden_csv))
        g = golden["case_refund_001"]
        assert g.expected_risk_flags == frozenset()
        assert g.expected_evidence_doc_types == frozenset({"FAQ"})

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_golden_expectations("/nonexistent/path.csv")


# ---------------------------------------------------------------------------
# Tests: load_eval_dataset (joined validation)
# ---------------------------------------------------------------------------


class TestLoadEvalDataset:
    """Tests for load_eval_dataset()."""

    def test_joined_dataset_has_matching_ids(self, valid_tickets_csv, valid_golden_csv):
        result = load_eval_dataset(str(valid_tickets_csv), str(valid_golden_csv))
        assert result.is_valid
        assert result.dataset.ticket_count == 3
        assert result.dataset.golden_count == 3

    def test_ticket_without_golden_rejected(self, tmp_dir):
        tickets_path = tmp_dir / "tickets.csv"
        golden_path = tmp_dir / "golden.csv"
        _write_csv(
            tickets_path,
            TICKETS_CSV_HEADER,
            _make_valid_tickets(
                extra_rows=[
                    "case_extra,extra text,CUST009,2026-05-01T10:00:00Z,refund,",
                ]
            ),
        )
        _write_csv(golden_path, GOLDEN_CSV_HEADER, _make_valid_golden())
        result = load_eval_dataset(str(tickets_path), str(golden_path))
        assert not result.is_valid
        assert "case_extra" in result.missing_golden_for_ticket

    def test_golden_without_ticket_rejected(self, tmp_dir):
        tickets_path = tmp_dir / "tickets.csv"
        golden_path = tmp_dir / "golden.csv"
        _write_csv(tickets_path, TICKETS_CSV_HEADER, _make_valid_tickets())
        _write_csv(
            golden_path,
            GOLDEN_CSV_HEADER,
            _make_valid_golden(
                extra_rows=[
                    "case_orphan,refund,,LOW,false,FAQ,false,false,",
                ]
            ),
        )
        result = load_eval_dataset(str(tickets_path), str(golden_path))
        assert not result.is_valid
        assert "case_orphan" in result.missing_ticket_for_golden

    def test_loaders_are_deterministic(self, tmp_dir):
        """Two consecutive loads produce identical results."""
        tickets_path = tmp_dir / "tickets.csv"
        golden_path = tmp_dir / "golden.csv"
        _write_csv(tickets_path, TICKETS_CSV_HEADER, _make_valid_tickets())
        _write_csv(golden_path, GOLDEN_CSV_HEADER, _make_valid_golden())

        result1 = load_eval_dataset(str(tickets_path), str(golden_path))
        result2 = load_eval_dataset(str(tickets_path), str(golden_path))

        assert result1.is_valid == result2.is_valid
        assert result1.dataset.ticket_count == result2.dataset.ticket_count
        assert result1.dataset.golden_count == result2.dataset.golden_count
        assert result1.missing_golden_for_ticket == result2.missing_golden_for_ticket
        assert result1.missing_ticket_for_golden == result2.missing_ticket_for_golden
        assert result1.errors == result2.errors

    def test_nonexistent_tickets_file(self, tmp_dir):
        golden_path = tmp_dir / "golden.csv"
        _write_csv(golden_path, GOLDEN_CSV_HEADER, _make_valid_golden())
        result = load_eval_dataset("/nonexistent/tickets.csv", str(golden_path))
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_nonexistent_golden_file(self, valid_tickets_csv, tmp_dir):
        result = load_eval_dataset(str(valid_tickets_csv), "/nonexistent/golden.csv")
        assert not result.is_valid
        assert len(result.errors) > 0
