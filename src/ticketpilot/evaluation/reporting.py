"""JSON and Markdown report writers for the evaluation pipeline.

Provides write_json_report() and write_markdown_report() for generating
offline evaluation reports from an EvaluationSummary.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any

from ticketpilot.evaluation.schemas import EvaluationSummary


def _serialize_for_json(obj: Any) -> Any:
    if isinstance(obj, frozenset):
        return sorted(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    if isinstance(obj, tuple):
        return [_serialize_for_json(v) for v in obj]
    return obj


def _case_result_to_dict(case_result: Any) -> dict[str, Any]:
    return {
        "case_id": case_result.case_id,        "prediction": {
            "predicted_issue_type": case_result.prediction.predicted_issue_type,
            "predicted_risk_flags": sorted(case_result.prediction.predicted_risk_flags),
            "predicted_severity": case_result.prediction.predicted_severity,
            "predicted_must_human_review": case_result.prediction.predicted_must_human_review,
            "predicted_evidence_doc_types": sorted(case_result.prediction.predicted_evidence_doc_types),
            "predicted_fallback_required": case_result.prediction.predicted_fallback_required,
            "predicted_no_auto_send": case_result.prediction.predicted_no_auto_send,
        },
        "metrics": {
            "intent_accuracy": case_result.metrics.intent_accuracy,
            "severity_accuracy": case_result.metrics.severity_accuracy,
            "must_human_review_accuracy": case_result.metrics.must_human_review_accuracy,
            "risk_flag_metrics": {
                "precision": case_result.metrics.risk_flag_metrics.precision,
                "recall": case_result.metrics.risk_flag_metrics.recall,
                "f1": case_result.metrics.risk_flag_metrics.f1,
                "exact_match": case_result.metrics.risk_flag_metrics.exact_match,
            },
            "evidence_doc_type_recall": case_result.metrics.evidence_doc_type_recall,
            "fallback_correctness": case_result.metrics.fallback_correctness,
            "no_auto_send_compliance": case_result.metrics.no_auto_send_compliance,
        },
        "mismatches": [
            {"metric": m.metric, "expected": m.expected, "predicted": m.predicted}
            for m in case_result.mismatches
        ],
    }


def _mismatch_entry_to_dict(mismatch: Any) -> dict[str, str]:
    return {
        "case_id": mismatch.case_id,
        "metric": mismatch.metric,
        "expected": mismatch.expected,
        "predicted": mismatch.predicted,
    }


def write_json_report(
    summary: EvaluationSummary,
    output_path: str | pathlib.Path,
    *,
    tickets_path: str = "",
    golden_path: str = "",
    predictions_path: str = "",
    prediction_mode: str = "csv",
) -> str:
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    per_case = [
        _case_result_to_dict(r)
        for r in sorted(summary.results.values(), key=lambda x: x.case_id)
    ]

    mismatch_list = [
        _mismatch_entry_to_dict(m) for m in sorted(
            summary.failed_cases, key=lambda x: (x.case_id, x.metric)
        )
    ]

    report = {
        "generated_at": generated_at,
        "metadata": {
            "prediction_mode": prediction_mode,
            "tickets_path": tickets_path,
            "golden_path": golden_path,
            "predictions_path": predictions_path,
        },
        "total_cases": summary.total_cases,
        "aggregate_metrics": {
            "intent_accuracy": summary.aggregate_intent_accuracy,
            "severity_accuracy": summary.aggregate_severity_accuracy,
            "must_human_review_accuracy": summary.aggregate_must_human_review_accuracy,
            "evidence_doc_type_recall": summary.aggregate_evidence_doc_type_recall,
            "fallback_correctness": summary.aggregate_fallback_correctness,
            "no_auto_send_compliance": summary.aggregate_no_auto_send_compliance,
        },
        "risk_flag_metrics": {
            "precision": summary.aggregate_risk_flag_precision,
            "recall": summary.aggregate_risk_flag_recall,
            "f1": summary.aggregate_risk_flag_f1,
        },
        "per_case_results": per_case,
        "mismatches": mismatch_list,
    }

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return json.dumps(report, indent=2, ensure_ascii=False)


def _pct(value: float) -> str:
    return "{:.1f}%".format(value * 100)


def write_markdown_report(
    summary: EvaluationSummary,
    output_path: str | pathlib.Path,
    *,
    tickets_path: str = "",
    golden_path: str = "",
    predictions_path: str = "",
    prediction_mode: str = "csv",
) -> str:
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    mode_label = "pipeline (local)" if prediction_mode == "pipeline" else "CSV"
    md = ["# Evaluation Report",
          "",
          "**Generated at:** " + generated_at,
          "",
          "## Dataset Summary",
          "",
          "| Field | Value |",
          "|---|---|",
          "| Total cases | " + str(summary.total_cases) + " |",
          "| Tickets file | `" + tickets_path + "` |",
          "| Golden file | `" + golden_path + "` |",
          "| Predictions file | `" + predictions_path + "` |",
          "| Prediction mode | " + mode_label + " |",
          "| Mismatches found | " + str(len(summary.failed_cases)) + " |",
          "",
          "## Aggregate Metrics",
          "",
          "| Metric | Value |",
          "|---|---|",
          "| Intent accuracy | " + _pct(summary.aggregate_intent_accuracy) + " |",
          "| Severity accuracy | " + _pct(summary.aggregate_severity_accuracy) + " |",
          "| Must-human-review accuracy | " + _pct(summary.aggregate_must_human_review_accuracy) + " |",
          "| Evidence doc type recall | " + _pct(summary.aggregate_evidence_doc_type_recall) + " |",
          "| Fallback correctness | " + _pct(summary.aggregate_fallback_correctness) + " |",
          "| No-auto-send compliance | " + _pct(summary.aggregate_no_auto_send_compliance) + " |",
          "",
          "## Risk Flag Metrics (Micro-Averaged)",
          "",
          "| Metric | Value |",
          "|---|---|",
          "| Precision | " + _pct(summary.aggregate_risk_flag_precision) + " |",
          "| Recall | " + _pct(summary.aggregate_risk_flag_recall) + " |",
          "| F1 | " + _pct(summary.aggregate_risk_flag_f1) + " |",
          "",
          "## Mismatch Summary",
          "",
          ]

    if summary.failed_cases:
        md.append("| Case ID | Metric | Expected | Predicted |")
        md.append("|---|---|---|---|")
        sorted_m = sorted(summary.failed_cases, key=lambda x: (x.case_id, x.metric))
        for m in sorted_m:
            exp = m.expected.replace("|", "\|")
            pred = m.predicted.replace("|", "\|")
            md.append("| " + m.case_id + " | " + m.metric + " | " + exp + " | " + pred + " |")
    else:
        md.append("No mismatches found.")

    md.append("")
    md.append("## Limitations")
    md.append("")
    md.append("- **Small deterministic seed dataset**: This evaluation uses a small set of curated deterministic seed data. Results are not statistically significant and should not be used to claim real-world performance.")
    md.append("- **No real embedding provider**: The current evaluation uses fake embeddings. Evidence retrieval metrics will change when a real embedding provider is integrated unless pipeline mode is added later.")
    md.append("- **Not real-world performance**: This report reflects offline evaluation on synthetic/golden data only. It does not represent production behavior.")

    report_str = "\n".join(md)

    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_str, encoding="utf-8")
    return report_str
