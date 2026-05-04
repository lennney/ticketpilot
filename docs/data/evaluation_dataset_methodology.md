# TicketPilot Evaluation Dataset Methodology

## Objective

The Phase 7 evaluation dataset is designed to evaluate TicketPilot as a **customer-support workflow system**, not as a general chatbot or open-domain RAG system.

It focuses on:
- intent classification (8 types);
- risk triage (8 risk flags + severity grading);
- evidence retrieval (FAQ / Policy / Case layered sources);
- no-evidence fallback behavior;
- draft-only no-auto-send architecture guarantee;
- human-review routing decisions.

## Dataset construction pipeline

```
Public / open reference sources
        │
        ▼
Scenario extraction — identify common customer-service scenarios
  from CSDS dialogue topics, Kaggle ticket categories, public policy domains
        │
        ▼
Issue taxonomy mapping — map extracted scenarios to TicketPilot's
  8 fixed issue types (refund, return_exchange, account_issue,
  technical_issue, product_consulting, logistics, complaint, other)
        │
        ▼
Manual rewriting into synthetic Chinese tickets —
  single-turn, customer → support, free of real personal data
        │
        ▼
Privacy and realism check — verify no real PII, no direct copy
        │
        ▼
Golden expectation annotation — assign expected_issue_type,
  expected_risk_flags, expected_severity, expected_must_human_review,
  expected_doc_types, expected_fallback_behavior, expected_no_auto_send
        │
        ▼
Evaluation pipeline validation — run CSV-mode and pipeline-mode
  evaluation, verify reports produce valid metrics
        │
        ▼
Limitations update — document synthetic provenance, fake embedding
  constraint, draft-only architecture, no production readiness
```

## Ticket construction rules

Each final ticket MUST be:
- **Single-turn**: one customer message per ticket, no multi-turn conversation.
- **Chinese**: simplified Chinese customer-service language.
- **Customer-service or after-sales oriented**: e-commerce after-sales domain (refund, return, logistics, account, payment, etc.).
- **Free of real personal data**: no real names, phone numbers, ID numbers, or addresses. Placeholder data only.
- **Manually adapted**: rewritten by hand from reference sources, not raw-copied.
- **Mapped to one of the 8 fixed issue types**: each ticket must have exactly one primary issue type.

## Fixed issue types

1. `refund` — 退款
2. `return_exchange` — 退换货
3. `account_issue` — 账号问题
4. `technical_issue` — 技术问题
5. `product_consulting` — 产品咨询
6. `logistics` — 物流
7. `complaint` — 投诉
8. `other` — 其他

## Scenario coverage target

The Phase 7 target is approximately 100 tickets.

Recommended distribution:

| Issue type | Target count |
|---|---:|
| refund | 14 |
| return_exchange | 12 |
| account_issue | 14 |
| technical_issue | 10 |
| product_consulting | 10 |
| logistics | 12 |
| complaint | 14 |
| other | 14 |

The distribution does not need to be perfectly equal, but every issue type MUST have enough cases to support per-class review (minimum 8 per type).

## Risk coverage target

The dataset MUST include all 8 risk flag types:
- `complaint_risk`
- `compensation_risk`
- `legal_risk`
- `privacy_risk`
- `account_security_risk`
- `policy_conflict`
- `insufficient_evidence`
- `low_confidence`

High-risk examples MUST include:
- Lawyer letter / legal threat (legal_risk)
- Compensation demand (compensation_risk)
- Personal information leakage (privacy_risk)
- Account abnormality (account_security_risk)
- Payment dispute (policy_conflict)
- Invoice dispute (policy_conflict)
- Policy conflict (policy_conflict)
- Unsupported user demand (insufficient_evidence / low_confidence)

## Strong demo scenarios

Phase 7 MUST include three strong demo scenarios:

### Demo 1: Refund complaint (退款投诉)

A customer asks for a refund and escalates with complaint, compensation, or legal language.

Expected behavior:
- `issue_type` may be `refund` or `complaint` depending on wording.
- `complaint_risk` / `compensation_risk` / `legal_risk` SHOULD be detected when applicable.
- `must_human_review` MUST be `true`.
- Evidence SHOULD prefer policy and case records.
- Draft MUST NOT make unsupported refund promises.

### Demo 2: Privacy / account issue (隐私/账号异常)

A customer reports account abnormality, leaked phone number, real-name information, address, or identity information.

Expected behavior:
- `issue_type` SHOULD be `account_issue` or `complaint` depending on wording.
- `privacy_risk` and/or `account_security_risk` SHOULD be detected.
- Severity SHOULD be `HIGH` when privacy leakage is explicit.
- `must_human_review` MUST be `true`.
- Evidence SHOULD include privacy/account policy.

### Demo 3: Invoice / payment issue (发票/支付争议)

A customer reports invoice failure, duplicate payment, incorrect amount, or payment dispute.

Expected behavior:
- `issue_type` SHOULD map to `refund`, `technical_issue`, `complaint`, or `other` depending on final taxonomy.
- Payment/invoice policy evidence SHOULD be retrieved.
- High-risk routing is required when complaint, compensation, or legal wording appears.
- Draft MUST NOT promise refund, compensation, or invoice reissue without evidence.

## Evaluation modes

Phase 7 supports two evaluation modes:

1. **CSV/sample prediction evaluation** — Loads pre-written sample_predictions.csv for fast metric computation without running the full pipeline.
2. **Pipeline-backed evaluation** — Runs each ticket through the full TicketPilot pipeline to generate predictions, then computes metrics against golden expectations.

If `sample_predictions.csv` cannot be fully synchronized with the expanded dataset, pipeline-backed evaluation becomes the primary Phase 7 report, and CSV evaluation is explicitly marked as requiring future synchronization.
