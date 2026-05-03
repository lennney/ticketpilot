# Evaluation Report

**Generated at:** 2026-05-03T07:56:07.108248+00:00

## Dataset Summary

| Field | Value |
|---|---|
| Total cases | 10 |
| Tickets file | `data/eval/tickets_eval.csv` |
| Golden file | `data/eval/golden_expectations.csv` |
| Predictions file | `data/eval/sample_predictions.csv` |
| Prediction mode | CSV |
| Mismatches found | 0 |

## Aggregate Metrics

| Metric | Value |
|---|---|
| Intent accuracy | 100.0% |
| Severity accuracy | 100.0% |
| Must-human-review accuracy | 100.0% |
| Evidence doc type recall | 100.0% |
| Fallback correctness | 100.0% |
| No-auto-send compliance | 100.0% |

## Risk Flag Metrics (Micro-Averaged)

| Metric | Value |
|---|---|
| Precision | 100.0% |
| Recall | 100.0% |
| F1 | 100.0% |

## Mismatch Summary

No mismatches found.

## Limitations

- **Small deterministic seed dataset**: This evaluation uses a small set of curated deterministic seed data. Results are not statistically significant and should not be used to claim real-world performance.
- **No real embedding provider**: The current evaluation uses fake embeddings. Evidence retrieval metrics will change when a real embedding provider is integrated unless pipeline mode is added later.
- **Not real-world performance**: This report reflects offline evaluation on synthetic/golden data only. It does not represent production behavior.