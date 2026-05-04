"""Deterministic CSV loaders for the evaluation dataset.

All loaders are pure I/O functions that:
- Depend only on the csv module from the standard library
- Do NOT import or call pipeline, database, LLM, embedding provider, network,
  or external services
- Fail loudly on malformed input
- Produce deterministic output for the same input
"""

from __future__ import annotations

import csv
import pathlib

from ticketpilot.evaluation.schemas import (
    EvalDataset,
    EvalTicket,
    GoldenExpectation,
    LoadResult,
)

# Required columns for each CSV
REQUIRED_TICKET_COLUMNS: list[str] = [
    "case_id",
    "original_text",
    "customer_id",
    "submitted_at",
    "scenario_type",
    "notes",
]

REQUIRED_GOLDEN_COLUMNS: list[str] = [
    "case_id",
    "expected_issue_type",
    "expected_risk_flags",
    "expected_severity",
    "expected_must_human_review",
    "expected_evidence_doc_types",
    "expected_fallback_required",
    "expected_no_auto_send",
    "notes",
]


def _check_required_columns(
    header: list[str],
    required: list[str],
    source_label: str,
) -> None:
    """Check that all required columns are present in the header.

    Raises ValueError with a descriptive message if any are missing.
    """
    header_set = set(header)
    missing = [c for c in required if c not in header_set]
    if missing:
        msg = (
            f"{source_label}: missing required column(s): {', '.join(missing)}. "
            f"Found columns: {header}"
        )
        raise ValueError(msg)


def _parse_semicolon_list(value: str | None) -> frozenset[str]:
    """Parse a semicolon-separated string into a frozenset of stripped tokens.

    Returns an empty frozenset for None, empty, or whitespace-only strings.
    """
    if not value or not value.strip():
        return frozenset()
    return frozenset(
        token.strip() for token in value.split(";") if token.strip()
    )


def load_tickets_eval(path: str | pathlib.Path) -> dict[str, EvalTicket]:
    """Load evaluation tickets from a CSV file.

    Args:
        path: Path to tickets_eval.csv

    Returns:
        Dict mapping case_id -> EvalTicket

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the CSV is missing required columns or contains
                    duplicate case_ids or malformed rows
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tickets file not found: {path}")

    tickets: dict[str, EvalTicket] = {}

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _check_required_columns(
            reader.fieldnames or [], REQUIRED_TICKET_COLUMNS, path.name
        )

        for row_idx, row in enumerate(reader, start=2):
            case_id_raw = row.get("case_id", "").strip()
            if not case_id_raw:
                msg = (
                    f"{path.name}: row {row_idx}: 'case_id' is empty or missing"
                )
                raise ValueError(msg)

            if case_id_raw in tickets:
                msg = (
                    f"{path.name}: row {row_idx}: duplicate case_id "
                    f"'{case_id_raw}'"
                )
                raise ValueError(msg)

            try:
                ticket = EvalTicket(
                    case_id=case_id_raw,
                    original_text=row.get("original_text", ""),
                    customer_id=row.get("customer_id", "").strip() or None,
                    submitted_at=row.get("submitted_at", "").strip(),
                    scenario_type=row.get("scenario_type", "").strip(),
                    notes=row.get("notes", "").strip() or None,
                )
            except Exception as exc:
                msg = (
                    f"{path.name}: row {row_idx}: failed to create "
                    f"EvalTicket: {exc}"
                )
                raise ValueError(msg) from exc

            tickets[case_id_raw] = ticket

    return tickets


def load_golden_expectations(
    path: str | pathlib.Path,
) -> dict[str, GoldenExpectation]:
    """Load golden expectations from a CSV file.

    Args:
        path: Path to golden_expectations.csv

    Returns:
        Dict mapping case_id -> GoldenExpectation

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the CSV is missing required columns or contains
                    duplicate case_ids or malformed rows
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Golden expectations file not found: {path}")

    golden: dict[str, GoldenExpectation] = {}

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _check_required_columns(
            reader.fieldnames or [], REQUIRED_GOLDEN_COLUMNS, path.name
        )

        for row_idx, row in enumerate(reader, start=2):
            case_id_raw = row.get("case_id", "").strip()
            if not case_id_raw:
                msg = (
                    f"{path.name}: row {row_idx}: 'case_id' is empty or missing"
                )
                raise ValueError(msg)

            if case_id_raw in golden:
                msg = (
                    f"{path.name}: row {row_idx}: duplicate case_id "
                    f"'{case_id_raw}'"
                )
                raise ValueError(msg)

            try:
                expectation = GoldenExpectation(
                    case_id=case_id_raw,
                    expected_issue_type=row.get(
                        "expected_issue_type", ""
                    ).strip(),
                    expected_risk_flags=_parse_semicolon_list(
                        row.get("expected_risk_flags", "")
                    ),
                    expected_severity=row.get("expected_severity", "").strip(),
                    expected_must_human_review=row.get(
                        "expected_must_human_review", ""
                    ).strip(),
                    expected_evidence_doc_types=_parse_semicolon_list(
                        row.get("expected_evidence_doc_types", "")
                    ),
                    expected_relevant_doc_ids=_parse_semicolon_list(
                        row.get("expected_relevant_doc_ids", "")
                    ),
                    expected_fallback_required=row.get(
                        "expected_fallback_required", ""
                    ).strip(),
                    expected_no_auto_send=row.get(
                        "expected_no_auto_send", ""
                    ).strip(),
                    notes=row.get("notes", "").strip() or None,
                )
            except Exception as exc:
                msg = (
                    f"{path.name}: row {row_idx}: failed to create "
                    f"GoldenExpectation: {exc}"
                )
                raise ValueError(msg) from exc

            golden[case_id_raw] = expectation

    return golden


def load_eval_dataset(
    tickets_path: str | pathlib.Path,
    golden_path: str | pathlib.Path,
) -> LoadResult:
    """Load and validate a complete evaluation dataset.

    Loads both CSV files, validates that:
    - All required columns are present
    - case_ids are unique within each file
    - Every ticket has a matching golden expectation
    - Every golden expectation references an existing ticket

    Args:
        tickets_path: Path to tickets_eval.csv
        golden_path: Path to golden_expectations.csv

    Returns:
        LoadResult containing the validated dataset and any issues found
    """
    errors: list[str] = []

    try:
        tickets = load_tickets_eval(tickets_path)
    except (FileNotFoundError, ValueError) as exc:
        errors.append(str(exc))
        return LoadResult(
            dataset=EvalDataset(),
            errors=errors,
        )

    try:
        golden = load_golden_expectations(golden_path)
    except (FileNotFoundError, ValueError) as exc:
        errors.append(str(exc))
        return LoadResult(
            dataset=EvalDataset(tickets=tickets),
            errors=errors,
        )

    ticket_ids = set(tickets.keys())
    golden_ids = set(golden.keys())

    missing_golden = sorted(ticket_ids - golden_ids)
    missing_ticket = sorted(golden_ids - ticket_ids)

    dataset = EvalDataset(tickets=tickets, golden=golden)

    return LoadResult(
        dataset=dataset,
        missing_golden_for_ticket=missing_golden,
        missing_ticket_for_golden=missing_ticket,
    )
