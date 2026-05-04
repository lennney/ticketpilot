# Phase 7 Baseline Audit

## Audit Date

2026-05-04

## Purpose

This document records the Phase 7 baseline before expanding the evaluation dataset. All numbers are measured from the current working tree, not estimated. The baseline serves as a reference point for measuring progress and ensuring no regressions.

## Current State

### Evaluation Data (data/eval/)

| File | Row count | Notes |
|---|---|---|
| `tickets_eval.csv` | 10 | 10 synthetic Chinese customer service tickets |
| `golden_expectations.csv` | 10 | 1:1 with tickets |
| `sample_predictions.csv` | 10 | Hand-labeled predictions for CSV-mode evaluation |

### Knowledge Base (data/knowledge/)

| File | Record count | Doc type |
|---|---|---|
| `faq_seed.json` | 12 | FAQ |
| `policy_seed.json` | 12 | POLICY |
| `case_seed.json` | 12 | CASE |
| **Total** | **36** | 3 doc types across 7 business domains |

### Evaluation Reports (reports/eval/)

| File | Exists | Mode | Cases |
|---|---|---|---|
| `evaluation_report.json` | Yes | CSV (from sample_predictions) | 10 |
| `current_pipeline_report.json` | Yes | Pipeline | 10 |
| `evaluation_report.md` | Yes | CSV mode markdown | 10 |
| `current_pipeline_report.md` | Yes | Pipeline mode markdown | 10 |

### Current Metric Values

| Metric | CSV mode | Pipeline mode |
|---|---|---|
| intent_accuracy | 1.0 | 0.8 |
| severity_accuracy | 1.0 | 0.9 |
| must_human_review_accuracy | 1.0 | 0.7 |
| evidence_doc_type_recall | 1.0 | 1.0 |
| fallback_correctness | 1.0 | 0.9 |
| no_auto_send_compliance | **1.0** | **0.5** |
| risk_flag_f1 | 1.0 | 0.93 |

### No-Auto-Send Compliance Issue

Current pipeline-mode no_auto_send_compliance = 0.5. This is because `expected_no_auto_send` in `golden_expectations.csv` is set to `false` for 5 low-risk tickets. This contradicts the architecture-level constraint that **all** TicketPilot output is draft-only (no send channel exists). Phase 7 will fix this by setting `expected_no_auto_send=true` for all tickets.

### Baseline Data Counts Summary

| Item | Current | Phase 7 Target |
|---|---|---|
| Eval tickets | 10 | ~100 |
| Golden expectations | 10 | ~100 (1 per ticket) |
| Knowledge records/chunks | 36 | 80–120 |
| Demo scenarios | 0 (ad-hoc) | 3 (refund complaint, privacy/account, invoice/payment) |
| No-auto-send compliance (pipeline) | 0.5 | 1.0 (architecture fix) |

## Scope Boundary

This audit records the baseline only. No data files have been modified.

- `data/eval/tickets_eval.csv` — unchanged
- `data/eval/golden_expectations.csv` — unchanged
- `data/eval/sample_predictions.csv` — unchanged
- `data/knowledge/` — unchanged
- `reports/` — unchanged
- `src/` — unchanged
- `tests/` — unchanged

## Next Step

Batch 7B-2 will expand the formal eval tickets and golden expectations. All data expansion will follow the methodology defined in Phase 7A and the AI-assisted extraction layer defined in Phase 7B-0.
