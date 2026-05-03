"""Tests for the prediction loader (predictions.py)."""

from __future__ import annotations
import pathlib as pl
import tempfile

import pytest

from ticketpilot.evaluation.predictions import load_predictions
from ticketpilot.evaluation.schemas import EvalPrediction, GoldenExpectation
from ticketpilot.evaluation.metrics import validate_predictions


@pytest.fixture
def valid_csv() -> str:
    rows = [
        "case_id,predicted_issue_type,predicted_risk_flags,predicted_severity,predicted_must_human_review,predicted_evidence_doc_types,predicted_fallback_required,predicted_no_auto_send",
        "case_001,refund,,LOW,false,FAQ,false,false",
        "case_002,complaint,legal_risk;compensation_risk,HIGH,true,POLICY;CASE,false,true",
        "case_003,account_issue,privacy_risk,MEDIUM,true,POLICY,false,true",
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(chr(10).join(rows))
        tmppath = f.name
    yield tmppath
    pl.Path(tmppath).unlink(missing_ok=True)


def test_prediction_csv_loads_correctly(valid_csv: str) -> None:
    """Prediction CSV loads into dict of EvalPrediction keyed by case_id."""
    result = load_predictions(valid_csv)
    assert len(result) == 3
    assert "case_001" in result
    assert isinstance(result["case_001"], EvalPrediction)
    assert result["case_001"].predicted_issue_type == "refund"
    assert result["case_001"].predicted_severity == "LOW"
    assert result["case_001"].predicted_must_human_review is False


def test_semicolon_fields_parse_correctly() -> None:
    """Semicolon-separated fields are parsed into frozensets."""
    rows = [
        "case_id,predicted_issue_type,predicted_risk_flags,predicted_severity,predicted_must_human_review,predicted_evidence_doc_types,predicted_fallback_required,predicted_no_auto_send",
        "case_001,refund,flag_a;flag_b;flag_c,LOW,false,FAQ;POLICY;MANUAL,false,false",
        "case_002,logistics,,LOW,false,FAQ,false,false",
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(chr(10).join(rows))
        tmppath = f.name
    try:
        result = load_predictions(tmppath)
        case1 = result["case_001"]
        assert case1.predicted_risk_flags == frozenset({"flag_a", "flag_b", "flag_c"})
        assert case1.predicted_evidence_doc_types == frozenset({"FAQ", "POLICY", "MANUAL"})
        case2 = result["case_002"]
        assert case2.predicted_risk_flags == frozenset()
    finally:
        pl.Path(tmppath).unlink(missing_ok=True)


def test_invalid_issue_type_fails() -> None:
    """Invalid predicted_issue_type raises ValueError."""
    rows = [
        "case_id,predicted_issue_type,predicted_risk_flags,predicted_severity,predicted_must_human_review,predicted_evidence_doc_types,predicted_fallback_required,predicted_no_auto_send",
        "case_001,invalid_type,,LOW,false,FAQ,false,false",
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(chr(10).join(rows))
        tmppath = f.name
    try:
        with pytest.raises(ValueError, match="Unknown issue type"):
            load_predictions(tmppath)
    finally:
        pl.Path(tmppath).unlink(missing_ok=True)


def test_duplicate_case_id_fails() -> None:
    """Duplicate case_id raises ValueError."""
    rows = [
        "case_id,predicted_issue_type,predicted_risk_flags,predicted_severity,predicted_must_human_review,predicted_evidence_doc_types,predicted_fallback_required,predicted_no_auto_send",
        "case_001,refund,,LOW,false,FAQ,false,false",
        "case_001,complaint,,HIGH,true,POLICY,false,true",
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(chr(10).join(rows))
        tmppath = f.name
    try:
        with pytest.raises(ValueError, match="duplicate case_id"):
            load_predictions(tmppath)
    finally:
        pl.Path(tmppath).unlink(missing_ok=True)


def test_missing_case_id_fails() -> None:
    """Missing case_id in prediction is caught by validate_predictions."""
    errors = validate_predictions({}, {
        "case_001": GoldenExpectation(
            case_id="case_001",
            expected_issue_type="refund",
            expected_severity="LOW",
            expected_must_human_review=False,
            expected_fallback_required=False,
            expected_no_auto_send=False,
        ),
    })
    assert len(errors) == 1
    assert "Missing prediction" in errors[0]


def test_extra_case_id_fails() -> None:
    """Extra prediction case_id is caught by validate_predictions."""
    errors = validate_predictions({
        "case_999": EvalPrediction(
            case_id="case_999",
            predicted_issue_type="refund",
            predicted_severity="LOW",
            predicted_must_human_review=False,
            predicted_fallback_required=False,
            predicted_no_auto_send=False,
        ),
    }, {})
    assert len(errors) == 1
    assert "Prediction without golden" in errors[0]
