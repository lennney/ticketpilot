# Evaluation Pipeline

## Overview

The evaluation pipeline provides offline, deterministic measurement of TicketPilot behavior against a curated set of golden evaluation data. It covers intent classification, risk flagging, severity correctness, evidence doc type recall, draft fallback handling, and human-review decision compliance.

**Pipeline type:** Local / deterministic / seed-data-based evaluation only. No real embedding provider, real LLM, network, API, or external service calls are involved.

**Source modules:**
- `src/ticketpilot/evaluation/` — schemas, loaders, metrics, predictions, reporting
- `scripts/run_eval.py` — CLI entrypoint supporting both CSV-prediction and pipeline-prediction modes

---

## Evaluation Dataset Design

### `data/eval/tickets_eval.csv`

10 deterministic seed tickets covering 8 intent classes, 5 risk flag categories, 3 severity levels, and edge cases.

| case_id | Intent (scenario) | Severity | Risk Flags | Must Human Review | Notes |
|---|---|---|---|---|---|
| case_refund_001 | refund | LOW | (none) | false | Standard refund with order number |
| case_return_ex_001 | return_exchange | LOW | (none) | false | Return/exchange due to size |
| case_acct_001 | account_issue | LOW | account_security_risk | true | Account frozen |
| case_logistics_001 | logistics | LOW | (none) | false | Delivery not received |
| case_complaint_001 | complaint | MEDIUM | complaint_risk, compensation_risk | true | Service complaint with compensation demand |
| case_privacy_001 | account_issue | MEDIUM | privacy_risk | true | Privacy/data leak concern |
| case_no_evidence_001 | refund | LOW | insufficient_evidence | true | Vague short request |
| case_high_risk_001 | complaint | HIGH | legal_risk, compensation_risk | true | Legal threat with compensation demand |
| case_technical_001 | technical_issue | LOW | (none) | false | App technical issue |
| case_consulting_001 | product_consulting | LOW | (none) | false | Product specification inquiry |

### `data/eval/golden_expectations.csv`

Golden expectations for all 10 tickets. Each row defines the expected pipeline output:

- `expected_issue_type` — one of 8 intent classes
- `expected_risk_flags` — semicolon-separated list (e.g., `complaint_risk;compensation_risk`)
- `expected_severity` — LOW, MEDIUM, or HIGH
- `expected_must_human_review` — true/false
- `expected_evidence_doc_types` — semicolon-separated doc type codes (FAQ, POLICY, CASE)
- `expected_fallback_required` — true/false
- `expected_no_auto_send` — true/false

### `data/eval/sample_predictions.csv`

Matching predictions for all 10 evaluation tickets. Structure mirrors `golden_expectations.csv` with `predicted_*` field names. Used for CLI smoke tests and CSV-prediction-mode evaluation.

---

## Metric Definitions

All metrics are computed by `src/ticketpilot/evaluation/metrics.py` as pure, deterministic functions operating on in-memory `EvalPrediction` and `GoldenExpectation` objects.

### `intent_accuracy`

Exact match between `predicted_issue_type` and `expected_issue_type`.

- **Per-case:** 1.0 if match, 0.0 otherwise.
- **Aggregate:** percentage of cases where intent matches.

### `severity_accuracy`

Exact match between `predicted_severity` and `expected_severity`.

- **Per-case:** 1.0 if match, 0.0 otherwise.
- **Aggregate:** percentage of cases where severity matches.

### `must_human_review_accuracy`

Exact match between `predicted_must_human_review` and `expected_must_human_review`.

- **Per-case:** 1.0 if match, 0.0 otherwise.
- **Aggregate:** percentage of cases where human-review flag matches.

### `evidence_doc_type_recall`

Recall of expected evidence document types in the predicted set. For each case:

```
recall = |expected_doc_types ∩ predicted_doc_types| / |expected_doc_types|
```

- 1.0 when `expected_doc_types` is empty (trivially satisfied).
- **Aggregate:** micro-averaged across all cases.

### `fallback_correctness`

Exact match between `predicted_fallback_required` and `expected_fallback_required`.

- **Per-case:** 1.0 if match, 0.0 otherwise.
- **Aggregate:** percentage of cases where fallback flag matches.

### `no_auto_send_compliance`

Exact match between `predicted_no_auto_send` and `expected_no_auto_send`.

- **Per-case:** 1.0 if match, 0.0 otherwise.
- **Aggregate:** percentage of cases where no-auto-send flag matches.

### `risk_flag_metrics`

Micro-averaged precision, recall, and F1 across all risk flags in the dataset (not per-case average).

| Metric | Definition |
|---|---|
| **Precision** | `|true positives| / (|true positives| + |false positives|)` |
| **Recall** | `|true positives| / (|true positives| + |false negatives|)` |
| **F1** | `2 * precision * recall / (precision + recall)` |

Micro-averaging correctly handles multi-flag cases where per-case averaging would give misleading weight to cases with few flags.

---

## CLI Usage

### CSV Prediction Mode

Evaluate manually-curated predictions against golden expectations:

```bash
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --predictions data/eval/sample_predictions.csv \
  --out-json reports/eval/evaluation_report.json \
  --out-md reports/eval/evaluation_report.md
```

### Pipeline Prediction Mode

Generate predictions by running the local TicketPilot pipeline against each eval ticket, then evaluate:

```bash
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --prediction-mode pipeline \
  --out-json reports/eval/current_pipeline_report.json \
  --out-md reports/eval/current_pipeline_report.md
```

In pipeline mode, each ticket goes through the full pipeline (`run_pipeline_with_draft`) before metric computation. Predictions are derived from pipeline output:
- `predicted_issue_type` from intent classification
- `predicted_risk_flags` from risk assessment
- `predicted_severity` from risk assessment
- `predicted_must_human_review` from risk assessment and DraftReply
- `predicted_evidence_doc_types` from evidence candidate doc types
- `predicted_fallback_required` from DraftReply fallback state
- `predicted_no_auto_send` always True

---

## Report Output Formats

### JSON Report (`--out-json`)

Structured machine-readable report with:

```json
{
  "metadata": {
    "generated_at": "ISO-8601 timestamp",
    "tickets_file": "data/eval/tickets_eval.csv",
    "golden_file": "data/eval/golden_expectations.csv",
    "predictions_file": "path or 'pipeline (generated from local TicketPilot pipeline)'",
    "prediction_mode": "csv | pipeline"
  },
  "summary": {
    "total_cases": 10,
    "mismatches_found": 0,
    "intent_accuracy": 1.0,
    "severity_accuracy": 1.0,
    "must_human_review_accuracy": 1.0,
    "evidence_doc_type_recall": 1.0,
    "fallback_correctness": 1.0,
    "no_auto_send_compliance": 1.0,
    "risk_flag_precision": 1.0,
    "risk_flag_recall": 1.0,
    "risk_flag_f1": 1.0
  },
  "per_case": [
    {
      "case_id": "case_refund_001",
      "intent_accuracy": 1.0,
      "severity_accuracy": 1.0,
      "must_human_review_accuracy": 1.0,
      "evidence_doc_type_recall": 1.0,
      "fallback_correctness": 1.0,
      "no_auto_send_compliance": 1.0,
      "risk_flag_precision": 1.0,
      "risk_flag_recall": 1.0,
      "risk_flag_f1": 1.0
    }
  ],
  "mismatches": [],
  "limitations": [
    "Small deterministic seed dataset...",
    "No real embedding provider...",
    "Not real-world performance..."
  ]
}
```

### Markdown Report (`--out-md`)

Human-readable report with:
- Dataset summary table (files, total cases, mismatch count, prediction mode)
- Aggregate metrics table (intent accuracy, severity accuracy, must-human-review accuracy, evidence doc type recall, fallback correctness, no-auto-send compliance)
- Risk flag metrics table (micro-averaged precision, recall, F1)
- Mismatch summary table (case_id, metric, expected, predicted)
- Limitations section

See sample reports in `reports/eval/` for examples:
- `evaluation_report.md` — CSV prediction mode (perfect match)
- `current_pipeline_report.md` — Pipeline prediction mode (realistic current performance)

---

## Current Limitations

- **Small deterministic seed dataset:** Only 10 curated tickets. Results are not statistically significant and should not be used to claim real-world performance.
- **No real embedding provider:** The current evaluation uses fake embeddings. Evidence retrieval metrics will change when a real embedding provider is integrated.
- **Not real-world performance:** This pipeline reflects offline evaluation on synthetic/golden data only. It does not represent production behavior.
- **Coverage gap:** The evaluation dataset does not cover all possible intent/severity/risk-flag combinations, edge cases, or real customer language patterns.
- **Deterministic only:** All metrics are computed from in-memory data. There is no online or A/B evaluation capability.

---

## Deferred Items

- **Realistic data pack:** A larger, more diverse evaluation dataset with real-world language patterns to improve statistical significance.
- **Real embedding evaluation:** Evidence retrieval quality measurement using a real embedding provider (e.g., OpenAI, Cohere) instead of fake embeddings.
- **Real LLM evaluation:** Draft quality measurement using a real LLM provider instead of the deterministic `FakeDraftProvider`.
- **Online evaluation:** End-to-end evaluation against a live production-like environment.
- **Regression detection:** Automated comparison of evaluation results across pipeline changes to detect regressions.

---

## References

- `docs/evaluation_plan.md` — High-level evaluation strategy and plan
- `docs/technical/testing_strategy.md` — Testing strategy covering unit, integration, and evaluation testing
- `scripts/run_eval.py` — CLI entrypoint for running evaluation
- `data/eval/` — Evaluation dataset (tickets, golden expectations, sample predictions)
- `reports/eval/` — Generated evaluation reports
