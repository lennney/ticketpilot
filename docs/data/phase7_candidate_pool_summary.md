# Phase 7 Adaptation Candidate Pool Summary

## Status

- **Phase**: 7B-2
- **Date**: 2026-05-04
- **File**: `data/eval/adaptation_candidates.csv`
- **Total candidates**: 96

## Important Notice

`adaptation_candidates.csv` is **not** the final evaluation dataset. It is an intermediate adaptation workbook:

- All records have `human_review_status=pending` — not yet reviewed
- All records have `ready_for_final_eval=false` — not ready for evaluation
- The next phase (7B-3) will involve human review, confirmation, and migration to `tickets_eval.csv` / `golden_expectations.csv`
- AI-generated candidate fields (`possible_issue_type`, `possible_risk_flags`, etc.) are suggestions only

## Distribution

### Issue Type

| Issue type | Count |
|---|---:|
| refund | 15 |
| return_exchange | 11 |
| account_issue | 14 |
| technical_issue | 9 |
| product_consulting | 8 |
| logistics | 11 |
| complaint | 12 |
| other | 16 |
| **Total** | **96** |

### Risk Flags

| Risk flag | Count |
|---|---:|
| complaint_risk | 31 |
| policy_conflict | 15 |
| compensation_risk | 14 |
| legal_risk | 8 |
| insufficient_evidence | 8 |
| account_security_risk | 7 |
| privacy_risk | 7 |
| low_confidence | 1 |

All 8 risk flag types are covered.

### Scenario Group

| Scenario group | Count |
|---|---:|
| refund_complaint | 9 |
| privacy_account | 11 |
| invoice_payment | 11 |
| normal_case | 65 |

### Evidence Doc Types Distribution

| Doc types | Count |
|---|---:|
| [FAQ] | 23 |
| [Policy, Case] | 30 |
| [FAQ, Policy] | 22 |
| [FAQ, Policy, Case] | 11 |
| [Case] | 5 |
| [FAQ, Case] | 4 |
| [Policy] | 1 |

### Source Usage Type

| Source usage type | Count |
|---|---:|
| scenario_reference | 66 |
| wording_reference | 22 |
| policy_reference | 8 |

## High-Risk Samples Coverage

The candidate pool includes the following high-risk scenarios:

| Scenario | Examples |
|---|---|
| Lawyer / legal threat | refund with legal risk, complaint with legal escalation |
| Compensation demand | refund with compensation, logistics compensation |
| Privacy leak / phone leak | phone number leaked, ID info used without consent |
| Account abnormality / theft | account stolen, unauthorized login, address changed |
| Duplicate payment / payment dispute | double charge, payment without order |
| Policy conflict | past return window, invoice policy dispute, price drop |
| Public exposure threat | complaint threatening social media exposure |

## Candidates Requiring Key Human Review

The following candidates have ambiguity or complexity that warrants special attention during human review:

| Candidate ID | Issue | Reason |
|---|---|---|
| cand_003 | refund + policy_conflict | Issue type could be either refund or complaint; risk flag appropriateness needs confirmation |
| cand_015 | refund + legal_risk | Legal threat is explicit, but severity and evidence doc type choices need review |
| cand_023 | return_exchange + compensation_risk | Whether compensation demand warrants HIGH severity needs judgment |
| cand_036 | account_issue + privacy + legal | Multiple overlapping risks; must_human_review is clearly true but severity needs calibration |
| cand_050 | technical_issue → system error charged no order | May belong to multiple issue types; scenario group may need reassignment |
| cand_072 | logistics + complaint + compensation | Mixed scenario; evidence doc type selection needs confirmation |
| cand_086 | other → invoice_payment | Invoice request categorized as "other" — could be a separate issue type in future |
| cand_091 | duplicate payment | Belongs to invoice_payment group; could also be classified as refund |
| cand_094 | account issue + identity theft + legal | High-complexity scenario requiring careful risk flag and severity calibration |
| cand_096 | privacy + legal + complaint (address leaked) | Extreme case; privacy_risk and legal_risk are clear but human review must confirm routing |

## Data Provenance

All candidates are **synthetic**. No real customer data, no external dataset records. Reference scenarios are inspired by common Chinese e-commerce after-sales patterns but every ticket text is original.

## Next Step

Phase 7B-3 will perform human review on these candidates, confirm or correct fields, and migrate confirmed records to `data/eval/tickets_eval.csv` and `data/eval/golden_expectations.csv`.
