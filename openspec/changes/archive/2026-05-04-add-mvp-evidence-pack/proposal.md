# Proposal: MVP Evidence Pack / Evaluatable Product Prototype Pack

## Executive Summary

TicketPilot currently has 10 eval tickets, 10 golden expectations, 36 knowledge records (12 each for FAQ/Policy/Case), and 2 evaluation reports showing aggregate metrics. The system is functionally complete as a demo but lacks the data scale, evaluation breadth, and demo depth needed to serve as a convincing "evaluatable product prototype."

This change expands the evaluation dataset to ~100 tickets, the knowledge base to 80–120 records/chunks, corrects the no-auto-send compliance metric to reflect the architecture-level guarantee (all system output is draft-only, not per-case), generates a new baseline evaluation report, updates limitations documentation, and adds 3 strong demo scenarios.

No new system features, no real LLM, no real embeddings, no production infrastructure.

## Baseline (Current State)

### Evaluation Data
- **Eval tickets**: 10 (in `data/eval/tickets_eval.csv`)
- **Golden expectations**: 10 (in `data/eval/golden_expectations.csv`, 1:1 with tickets)
- **Intent coverage**: 8/8 classes (refund, return_exchange, account_issue, logistics, complaint, privacy, technical_issue, product_consulting)
- **Risk coverage**: complaint, compensation, account_security, privacy, legal (partial), insufficient_evidence
- **Severity distribution**: 6 LOW, 2 MEDIUM, 1 HIGH
- **Ticket domains**: refund, return_exchange, account, logistics, complaint, privacy, no-evidence, high-risk, technical, consulting

### Knowledge Base
- **FAQ records**: 12 (7 business domains, doc_type=FAQ)
- **Policy records**: 12 (7 business domains, doc_type=POLICY)
- **Case records**: 12 (7 business domains, doc_type=CASE)
- **Total**: 36 records
- **Business domains**: refund, return_exchange, account, logistics, complaint, technical, product_consulting
- **Missing domains**: privacy/data_protection, billing/invoice, payment_dispute

### Evaluation Reports
- **CSV mode report** (`evaluation_report.json`): intent_accuracy=1.0, severity_accuracy=1.0, must_human_review_accuracy=1.0, evidence_doc_type_recall=1.0, fallback_correctness=1.0, no_auto_send_compliance=1.0, risk_flag_f1=1.0
- **Pipeline mode report** (`current_pipeline_report.json`): intent_accuracy=0.8, severity_accuracy=0.9, must_human_review_accuracy=0.7, evidence_doc_type_recall=1.0, fallback_correctness=0.9, no_auto_send_compliance=0.5, risk_flag_f1=0.93
- **Total cases**: 10

### No-Auto-Send Metric Issue
Current golden expectations inconsistently set `expected_no_auto_send=true` only for high-risk/must-review tickets and `false` for low-risk ones. This contradicts the architecture-level constraint that ALL system output is draft-only. The metric must be redefined to always expect `no_auto_send=true` for every pipeline-generated prediction, reflecting the fact that no send channel exists.

## Problem Statement

1. **Data scale too small**: 10 tickets and 36 knowledge records are insufficient to demonstrate pipeline behavior across diverse scenarios. The evaluation dataset does not cover billing, invoice, payment disputes, or multi-intent tickets.

2. **No-auto-send metric misaligned**: The metric currently measures per-case prediction vs. golden expectation, but the constraint is architectural — always true, not risk-dependent.

3. **Demo depth insufficient**: Only the existing Streamlit console serves as a demo surface. Three scripted demo scenarios (refund+complaint, privacy/account, billing/payment) with sample tickets and walkthrough steps are needed.

4. **Limitations documentation incomplete**: Current README limitations section is accurate but brief. A structured limitations document covering synthetic data provenance, fake embedding implications, draft-only architecture, and no-production-readiness disclaimer is needed.

5. **Evaluation report out of date**: Current reports reflect 10 cases from May 3. After expanding to ~100 tickets, a new baseline report must be generated in both CSV and pipeline modes.

## Proposed Solution

### Batch 0 (Phase 7A): Data Source & Evaluation Dataset Definition
- Create `docs/data/evidence_pack_sources.md` — source registry documenting all external datasets used as reference, with usage, limitations, and license/access notes.
- Create `docs/data/evaluation_dataset_methodology.md` — construction pipeline from public reference sources to synthetic Chinese eval tickets, with scenario/risk coverage targets and ticket construction rules.
- Create `docs/data/golden_expectation_annotation_guide.md` — field definitions and annotation principles for golden expectations.
- Create `openspec/changes/add-mvp-evidence-pack/specs/data/spec.md` — data sources and methodology spec.
- Update proposal and tasks to reference the new data docs.
- No source code, eval data, knowledge data, or reports modified.

### Batch 1: Baseline Audit and OpenSpec Validation
- No code or data changes.
- Confirm working tree clean, OpenSpec validate --all passes, quality gate passes.
- Record baseline metrics in this proposal.

### Batch 2: Expand Eval Tickets and Golden Expectations
- Expand `data/eval/tickets_eval.csv` from 10 to ~100 tickets.
- Expand `data/eval/golden_expectations.csv` from 10 to ~100 entries (1:1).
- Fix `expected_no_auto_send` to always be `true` for all pipeline-mode predictions.
- Add synthetic Chinese customer service tickets covering:
  - New domains: billing/invoice, payment_dispute, privacy/data_protection
  - Multi-intent tickets (e.g., refund + complaint, account + privacy)
  - Edge cases: empty text, very short, very long, special characters
  - All 8 intent classes with 8–15 tickets each
  - All risk flag categories
  - All severity levels
- Do NOT modify `src/`, `tests/`, `reports/`, READMEs in this batch.

### Batch 3: Expand Knowledge Base
- Add ~30 FAQ records (from 12 to ~40), covering billing/invoice, payment_dispute, privacy/data_protection.
- Add ~20 Policy records (from 12 to ~30), with new domain policies.
- Add ~15 Case records (from 12 to ~25), with new domain case resolutions.
- Target: 80–120 total records/chunks.
- All synthetic, manually crafted Chinese customer service content.
- Do NOT modify `src/` or `tests/` in this batch.

### Batch 4: Align No-Auto-Send Metric
- Fix golden expectations: set `expected_no_auto_send=true` for ALL tickets (architecture guarantee).
- Fix sample_predictions.csv (if used in CSV mode) to match.
- Run eval in both CSV and pipeline modes to verify no_auto_send_compliance=1.0.
- Do NOT modify evaluation logic (`src/ticketpilot/evaluation/`).

### Batch 5: Generate Evaluation Reports and Demo Docs
- Run `scripts/run_eval.py` in CSV mode → new `evaluation_report.json`.
- Run `scripts/run_eval.py` in pipeline mode → new `current_pipeline_report.json`.
- Create 3 demo scenario documentation files:
  - Scenario 1: 退款投诉 (refund + complaint — compensation/legal risk)
  - Scenario 2: 隐私/账号异常 (account issue + privacy leak risk)
  - Scenario 3: 发票/支付争议 (billing/invoice + payment dispute)
- Each scenario doc includes: sample ticket text, expected pipeline behavior, risk flags, knowledge retrieval targets, draft expectations.

### Batch 6: Limitations/README Update and Final Quality Gate
- Update `docs/portfolio/limitations.md` or equivalent with structured limitations:
  - Data is synthetic/manufactured customer service scenarios, not real enterprise data
  - Not a production customer-service system
  - Default deterministic fake embedding — no semantic retrieval quality
  - Real semantic retrieval comparison deferred to Phase 8
  - All replies are drafts requiring human review — no auto-send
- Update README.md and README.en.md if needed.
- Update docs/changelog.md.
- Run OpenSpec validate --all.
- Run full quality gate.
- Commit all changes.

## What This Change Does NOT Do

- Does not add real LLM provider (remains deterministic templates).
- Does not add real embedding provider (remains fake 384-dim hash vectors).
- Does not modify any `src/ticketpilot/` production code.
- Does not modify any `tests/` files.
- Does not modify pipeline, retrieval, risk, drafting, or review console behavior.
- Does not create or modify Streamlit review console.
- Does not introduce API keys, real enterprise data, or external services.
- Does not weaken quality gate or skip integration tests.
- Does not claim production readiness.

## Scope

### In Scope
- `docs/data/evidence_pack_sources.md`: data source registry and adaptation policy
- `docs/data/evaluation_dataset_methodology.md`: dataset construction methodology
- `docs/data/golden_expectation_annotation_guide.md`: golden expectation annotation guide
- `data/eval/tickets_eval.csv`: expand from 10 to ~100 tickets
- `data/eval/golden_expectations.csv`: expand from 10 to ~100 entries
- `data/eval/sample_predictions.csv`: update if needed
- `data/knowledge/faq_seed.json`: expand from 12 to ~40
- `data/knowledge/policy_seed.json`: expand from 12 to ~30
- `data/knowledge/case_seed.json`: expand from 12 to ~25
- `reports/eval/evaluation_report.json`: regenerate
- `reports/eval/current_pipeline_report.json`: regenerate
- 3 demo scenario docs (under `docs/demo/` or `docs/portfolio/`)
- Limitations documentation
- README minor updates
- docs/changelog.md update

### Out of Scope
- Real LLM or real embedding
- `src/ticketpilot/` changes
- `tests/` changes
- New system features or pipeline behavior changes
- Authenticated/production deployment
- Real enterprise data
- Performance benchmarking
