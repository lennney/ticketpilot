"""Pydantic schemas for evaluation data structures.

This module defines the data contracts for the evaluation pipeline:
- EvalTicket: a single evaluation ticket loaded from tickets_eval.csv
- GoldenExpectation: expected pipeline output for a ticket
- EvalDataset: the joined view of tickets and their golden expectations
- LoadResult: the result of loading and validating both CSVs
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator

from ticketpilot.schema.ticket import IntentClass, RiskSeverity

# The 8 valid issue types derived from the IntentClass enum
VALID_ISSUE_TYPES: set[str] = {m.value for m in IntentClass}

# Valid severity values (uppercase canonical form per _validate_severity)
VALID_SEVERITIES: set[str] = {m.value.upper() for m in RiskSeverity}


class EvalTicket(BaseModel):
    """A single evaluation ticket loaded from tickets_eval.csv."""

    case_id: str = Field(..., min_length=1)
    original_text: str
    customer_id: str | None = None
    submitted_at: str
    scenario_type: str
    notes: str | None = None


class GoldenExpectation(BaseModel):
    """Expected pipeline output for a single evaluation ticket.

    List-like fields (expected_risk_flags, expected_evidence_doc_types) are
    stored as semicolon-separated strings in the CSV and parsed into frozensets
    for deterministic comparison.
    """

    case_id: str = Field(..., min_length=1)
    expected_issue_type: str
    expected_risk_flags: frozenset[str] = Field(default_factory=frozenset)
    expected_severity: str
    expected_must_human_review: bool
    expected_evidence_doc_types: frozenset[str] = Field(default_factory=frozenset)
    expected_fallback_required: bool
    expected_no_auto_send: bool
    notes: str | None = None

    @field_validator("expected_issue_type")
    @classmethod
    def _validate_issue_type(cls, v: str) -> str:
        if v not in VALID_ISSUE_TYPES:
            msg = (
                f"Unknown issue type '{v}'. "
                f"Must be one of: {', '.join(sorted(VALID_ISSUE_TYPES))}"
            )
            raise ValueError(msg)
        return v

    @field_validator("expected_severity")
    @classmethod
    def _validate_severity(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_SEVERITIES:
            msg = (
                f"Unknown severity '{v}'. "
                f"Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
            )
            raise ValueError(msg)
        return v_upper

    @field_validator("expected_must_human_review", mode="before")
    @classmethod
    def _coerce_bool(cls, v: bool | str) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
            msg = f"Cannot parse boolean from '{v}'"
            raise ValueError(msg)
        return bool(v)

    @field_validator("expected_fallback_required", mode="before")
    @classmethod
    def _coerce_bool_fallback(cls, v: bool | str) -> bool:
        return GoldenExpectation._coerce_bool(v)

    @field_validator("expected_no_auto_send", mode="before")
    @classmethod
    def _coerce_bool_no_auto_send(cls, v: bool | str) -> bool:
        return GoldenExpectation._coerce_bool(v)


@dataclass
class EvalDataset:
    """The joined view of tickets and their golden expectations.

    Both fields are dicts keyed by case_id for O(1) lookup.
    """

    tickets: dict[str, EvalTicket] = field(default_factory=dict)
    golden: dict[str, GoldenExpectation] = field(default_factory=dict)

    @property
    def case_ids(self) -> set[str]:
        return set(self.tickets.keys()) | set(self.golden.keys())

    @property
    def ticket_count(self) -> int:
        return len(self.tickets)

    @property
    def golden_count(self) -> int:
        return len(self.golden)

    def get_ticket(self, case_id: str) -> EvalTicket | None:
        return self.tickets.get(case_id)

    def get_golden(self, case_id: str) -> GoldenExpectation | None:
        return self.golden.get(case_id)


@dataclass
class LoadResult:
    """The result of loading and validating both CSV files."""

    dataset: EvalDataset
    missing_golden_for_ticket: list[str] = field(default_factory=list)
    missing_ticket_for_golden: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return (
            len(self.missing_golden_for_ticket) == 0
            and len(self.missing_ticket_for_golden) == 0
            and len(self.errors) == 0
        )


# ---------------------------------------------------------------------------
# Prediction & metric schemas (Batch 2)
# ---------------------------------------------------------------------------


class EvalPrediction(BaseModel):
    """Predicted pipeline output for a single evaluation ticket.

    Mirrors the shape of GoldenExpectation but with predicted_* fields
    instead of expected_* fields.
    """

    case_id: str = Field(..., min_length=1)
    predicted_issue_type: str
    predicted_risk_flags: frozenset[str] = Field(default_factory=frozenset)
    predicted_severity: str
    predicted_must_human_review: bool
    predicted_evidence_doc_types: frozenset[str] = Field(default_factory=frozenset)
    predicted_fallback_required: bool
    predicted_no_auto_send: bool


class RiskFlagMetrics(BaseModel):
    """Per-case risk flag prediction metrics.

    All float values are in [0.0, 1.0].
    """

    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1: float = Field(..., ge=0.0, le=1.0)
    exact_match: bool


class EvaluationMetrics(BaseModel):
    """All computed metrics for a single evaluation case.

    Boolean metrics are per-case (True = correct, False = mismatch).
    """

    intent_accuracy: bool
    severity_accuracy: bool
    must_human_review_accuracy: bool
    risk_flag_metrics: RiskFlagMetrics
    evidence_doc_type_recall: float = Field(..., ge=0.0, le=1.0)
    fallback_correctness: bool
    no_auto_send_compliance: bool


class MismatchEntry(BaseModel):
    """A single mismatch between prediction and golden expectation."""

    case_id: str
    metric: str
    expected: str
    predicted: str


class CaseResult(BaseModel):
    """Full evaluation result for a single case."""

    case_id: str
    golden: GoldenExpectation
    prediction: EvalPrediction
    metrics: EvaluationMetrics
    mismatches: list[MismatchEntry] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    """Aggregate evaluation summary across all cases.

    Aggregate metrics are rate-based (float in [0.0, 1.0]).
    Risk flag metrics use micro-averaging across all cases.
    """

    total_cases: int = Field(..., ge=0)
    results: dict[str, CaseResult] = Field(default_factory=dict)
    aggregate_intent_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_severity_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_must_human_review_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_risk_flag_precision: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_risk_flag_recall: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_risk_flag_f1: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_evidence_doc_type_recall: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_fallback_correctness: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_no_auto_send_compliance: float = Field(default=0.0, ge=0.0, le=1.0)
    failed_cases: list[MismatchEntry] = Field(default_factory=list)
