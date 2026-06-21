"""Deterministic prediction loader for the evaluation pipeline."""

from __future__ import annotations

import csv
import pathlib

from ticketpilot.evaluation.schemas import EvalPrediction

REQUIRED_PREDICTION_COLUMNS: list[str] = [
    "case_id",
    "predicted_issue_type",
    "predicted_risk_flags",
    "predicted_severity",
    "predicted_must_human_review",
    "predicted_evidence_doc_types",
    "predicted_fallback_required",
    "predicted_no_auto_send",
]


def _check_required_columns(header, required, source_label):
    header_set = set(header)
    missing = [c for c in required if c not in header_set]
    if missing:
        msg = f"{source_label}: missing required column(s): {chr(44).join(missing)}. Found columns: {header}"
        raise ValueError(msg)


def _parse_semicolon_list(value):
    if not value or not value.strip():
        return frozenset()
    return frozenset(token.strip() for token in value.split(chr(59)) if token.strip())


def load_predictions(path):
    filepath = pathlib.Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Predictions file not found: {filepath}")

    predictions = {}

    with filepath.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        _check_required_columns(
            reader.fieldnames or [], REQUIRED_PREDICTION_COLUMNS, filepath.name
        )

        for row_idx, row in enumerate(reader, start=2):
            case_id_raw = row.get("case_id", "").strip()
            if not case_id_raw:
                raise ValueError(
                    f"{filepath.name}: row {row_idx}: 'case_id' is empty or missing"
                )
            if case_id_raw in predictions:
                raise ValueError(
                    f"{filepath.name}: row {row_idx}: duplicate case_id '{case_id_raw}'"
                )

            try:
                prediction = EvalPrediction(
                    case_id=case_id_raw,
                    predicted_issue_type=row.get("predicted_issue_type", "").strip(),
                    predicted_risk_flags=_parse_semicolon_list(
                        row.get("predicted_risk_flags", "")
                    ),
                    predicted_severity=row.get("predicted_severity", "").strip(),
                    predicted_must_human_review=row.get(
                        "predicted_must_human_review", ""
                    ).strip(),
                    predicted_evidence_doc_types=_parse_semicolon_list(
                        row.get("predicted_evidence_doc_types", "")
                    ),
                    predicted_fallback_required=row.get(
                        "predicted_fallback_required", ""
                    ).strip(),
                    predicted_no_auto_send=row.get(
                        "predicted_no_auto_send", ""
                    ).strip(),
                )
            except Exception as exc:
                raise ValueError(
                    f"{filepath.name}: row {row_idx}: failed to create EvalPrediction: {exc}"
                ) from exc

            predictions[case_id_raw] = prediction

    return predictions
