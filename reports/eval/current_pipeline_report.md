# Evaluation Report

**Generated at:** 2026-05-03T07:56:29.558709+00:00

## Dataset Summary

| Field | Value |
|---|---|
| Total cases | 10 |
| Tickets file | `data/eval/tickets_eval.csv` |
| Golden file | `data/eval/golden_expectations.csv` |
| Predictions file | `pipeline (generated from local TicketPilot pipeline)` |
| Prediction mode | pipeline (local) |
| Mismatches found | 13 |

## Aggregate Metrics

| Metric | Value |
|---|---|
| Intent accuracy | 80.0% |
| Severity accuracy | 90.0% |
| Must-human-review accuracy | 70.0% |
| Evidence doc type recall | 100.0% |
| Fallback correctness | 90.0% |
| No-auto-send compliance | 50.0% |

## Risk Flag Metrics (Micro-Averaged)

| Metric | Value |
|---|---|
| Precision | 87.5% |
| Recall | 100.0% |
| F1 | 93.3% |

## Mismatch Summary

| Case ID | Metric | Expected | Predicted |
|---|---|---|---|
| case_consulting_001 | no_auto_send_compliance | False | True |
| case_high_risk_001 | intent_accuracy | complaint | other |
| case_logistics_001 | must_human_review_accuracy | False | True |
| case_logistics_001 | no_auto_send_compliance | False | True |
| case_no_evidence_001 | fallback_correctness | True | False |
| case_privacy_001 | intent_accuracy | account_issue | other |
| case_privacy_001 | risk_flags | privacy_risk | low_confidence,privacy_risk |
| case_privacy_001 | severity_accuracy | MEDIUM | LOW |
| case_refund_001 | must_human_review_accuracy | False | True |
| case_refund_001 | no_auto_send_compliance | False | True |
| case_return_ex_001 | must_human_review_accuracy | False | True |
| case_return_ex_001 | no_auto_send_compliance | False | True |
| case_technical_001 | no_auto_send_compliance | False | True |

## Limitations

- **Small deterministic seed dataset**: This evaluation uses a small set of curated deterministic seed data. Results are not statistically significant and should not be used to claim real-world performance.
- **No real embedding provider**: The current evaluation uses fake embeddings. Evidence retrieval metrics will change when a real embedding provider is integrated unless pipeline mode is added later.
- **Not real-world performance**: This report reflects offline evaluation on synthetic/golden data only. It does not represent production behavior.