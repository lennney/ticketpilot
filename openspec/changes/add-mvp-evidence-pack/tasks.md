# Tasks: MVP Evidence Pack

## Batch 0 (Phase 7A): Data Source & Evaluation Dataset Definition

- [x] 0.1 Create `docs/data/evidence_pack_sources.md` — source registry with CSDS, Kaggle, Chinese Chatbot Corpus, public policy pages
- [x] 0.2 Create `docs/data/evaluation_dataset_methodology.md` — construction pipeline, ticket rules, coverage targets, 3 demo scenarios
- [x] 0.3 Create `docs/data/golden_expectation_annotation_guide.md` — field definitions, annotation principles, no-auto-send architecture rule
- [x] 0.4 Create `openspec/changes/add-mvp-evidence-pack/specs/data/spec.md` — data sources and methodology spec
- [x] 0.5 Update proposal.md and tasks.md to reference the new data docs
- [x] 0.6 Update docs/changelog.md with Phase 7A entry
- [ ] 0.7 Run OpenSpec validate add-mvp-evidence-pack --strict
- [ ] 0.8 Run OpenSpec validate --all
- [ ] 0.9 Run quality gate

## Batch 0B (Phase 7B-0): AI-assisted Field Extraction and Ticket Adaptation

- [x] 0B.1 Create `docs/data/ai_field_extraction_adaptation.md` — AI-assisted extraction pipeline, source reference schema, extraction candidate fields, final ticket fields, golden expectation fields, AI/human responsibility matrix, review triggers, prohibited practices, example
- [x] 0B.2 Update docs/changelog.md with Phase 7B-0 entry
- [x] 0B.3 Update openspec/changes/add-mvp-evidence-pack/specs/data/spec.md with AI extraction layer requirements
- [ ] 0B.4 Run OpenSpec validate add-mvp-evidence-pack --strict
- [ ] 0B.5 Run OpenSpec validate --all
- [ ] 0B.6 Run quality gate

## Batch 7B-1: Baseline Audit and Adaptation Workbook

- [x] 1.1 Collect baseline audit data: tickets=10, golden=10, sample_predictions=10, knowledge=36, no_auto_send_compliance=0.5/1.0
- [x] 1.2 Create `docs/data/phase7_baseline_audit.md` — baseline counts, current metrics, Phase 7 targets
- [x] 1.3 Create `docs/data/templates/adaptation_candidates.template.csv` — header + 1 example row
- [x] 1.4 Create `docs/data/ai_extraction_prompt.md` — reusable prompt for AI field extraction with JSON schema
- [x] 1.5 Update docs/changelog.md with Phase 7B-1 entry
- [x] 1.6 Update OpenSpec data spec with baseline audit and workbook requirements
- [ ] 1.7 Run OpenSpec validate add-mvp-evidence-pack --strict
- [ ] 1.8 Run OpenSpec validate --all
- [ ] 1.9 Run quality gate

## Batch 7B-2: Build Adaptation Candidate Pool

- [x] 2.1 Create `data/eval/adaptation_candidates.csv` — 96 synthetic candidates with all 21 fields, covering all 8 issue types, all 8 risk flags, 3 demo scenario groups
- [x] 2.2 Create `docs/data/phase7_candidate_pool_summary.md` — distribution tables, high-risk coverage, key candidates requiring human review
- [x] 2.3 Update docs/changelog.md with Phase 7B-2 entry
- [x] 2.4 Update OpenSpec data spec with candidate pool requirements
- [x] 2.5 Update OpenSpec evaluation spec with candidate pool reference
- [x] 2.6 Run OpenSpec validate add-mvp-evidence-pack --strict
- [x] 2.7 Run OpenSpec validate --all
- [x] 2.8 Run quality gate
- [x] 2.9 Clean up: remove scripts/generate_adaptation_candidates.py (generator script, not needed in repo)

## Batch 3: Baseline Audit and OpenSpec Validation (Original)

- [ ] 3.1 Confirm working tree clean (only reviews.jsonl untracked is acceptable)
- [ ] 3.2 Run OpenSpec validate --all — expect 15/15
- [ ] 3.3 Run quality gate — Ruff ✓, 642 unit ✓, 119 integration ✓, coverage ≥70%
- [ ] 3.4 Record baseline: 10 tickets, 10 golden, 36 knowledge records

## Batch 4: Expand Eval Tickets and Golden Expectations

- [x] 2.1 Expand `data/eval/tickets_eval.csv` from 10 to 101 synthetic Chinese customer service tickets:
  - New domains: invoice (5), payment_dispute (2), billing (2), privacy_account (2+)
  - Existing domains expanded: refund (17), return_exchange (11), account_issue (15), logistics (11), complaint (14), technical_issue (9), product_consulting (8)
  - Multi-intent tickets: refund+complaint (3), account+privacy (2), billing+dispute (2) = 7 total
  - Edge cases: empty text, very long text (589 chars), special characters, mixed Chinese/English, numbers/symbols only
  - Coverage: all 8 intent classes with 8–17 tickets each, all 8 risk flag categories, all 3 severity levels
  - All fields: case_id, original_text, customer_id, submitted_at, scenario_type, notes
- [x] 2.2 Expand `data/eval/golden_expectations.csv` to match (101 entries):
  - One golden entry per eval ticket
  - Fixed: `expected_no_auto_send=true` for ALL tickets (architecture guarantee)
  - All fields: case_id, expected_issue_type, expected_risk_flags, expected_severity, expected_must_human_review, expected_evidence_doc_types, expected_fallback_required, expected_no_auto_send, notes
- [x] 2.3 Validate dataset consistency: all golden entries reference valid ticket IDs, all required columns present
- [x] 2.4 Run OpenSpec validate --all — 16/16 passed
- [x] 2.5 Run quality gate — Ruff ✓, 761 tests ✓, 87% coverage ✓

## Batch 3: Expand Knowledge Base

- [x] 3.1 Expand `data/knowledge/faq_seed.json` from 12 to ~40 records:
  - Add FAQ entries for billing/invoice (5–8), payment_dispute (5–8), privacy/data_protection (5–8)
  - Expand existing domains with additional entries (8–12)
  - Each FAQ: id, doc_type=FAQ, business_domain, title, content, intent_tags
- [x] 3.2 Expand `data/knowledge/policy_seed.json` from 12 to ~30 records:
  - Add policy entries for new domains: billing, refund_extension, privacy, data_retention
  - Each policy: id, doc_type=POLICY, business_domain, policy_code, title, content, effective_date
- [x] 3.3 Expand `data/knowledge/case_seed.json` from 12 to ~25 records:
  - Add case entries for new domains with realistic resolutions
  - Each case: id, doc_type=CASE, business_domain, case_id, issue_summary, resolution, risk_level, compensation_amount
- [x] 3.4 Verify knowledge data loads without error: DB re-seeded, verify_seeding() confirms FAQ=40, Policy=30, Case=25, total_chunks=95, all with source refs and embeddings
- [x] 3.5 Run OpenSpec validate --all — 16/16 passed
- [x] 3.6 Run quality gate — 642 unit, 119 integration (0 skipped), 84.22% coverage, PASSED

## Batch 4: Align No-Auto-Send Metric

- [x] 4.1 Verify `expected_no_auto_send=true` for ALL entries in golden_expectations.csv
- [x] 4.2 Update `data/eval/sample_predictions.csv` with all predicted_no_auto_send=true
- [x] 4.3 Run eval in CSV mode — total_cases=101, no_auto_send_compliance=1.0
- [x] 4.4 Verify no_auto_send_compliance=1.0 in CSV mode report
- [x] 4.5 Run eval in pipeline mode — total_cases=101, no_auto_send_compliance=1.0
- [x] 4.6 Verify no_auto_send_compliance=1.0 in pipeline mode report
- [x] 4.7 Run quality gate — Ruff ✓, 761 tests ✓, 87% coverage ✓

## Batch 5: Generate Evaluation Reports and Demo Scenario Docs

- [x] 5.1 Generate final CSV-mode evaluation report → `reports/eval/evaluation_report.json` + `.md`
- [x] 5.2 Generate final pipeline-mode evaluation report → `reports/eval/current_pipeline_report.json` + `.md`
- [ ] 5.3 Create demo scenario 1: 退款投诉 (refund + complaint / compensation + legal risk)
  - 3–5 sample tickets
  - Expected pipeline flow: intake → classification → risk (COMPLAINT_RISK, COMPENSATION_RISK, LEGAL_RISK, HIGH severity) → retrieval (CASE + POLICY) → draft with high-risk warning → must_human_review
  - Walkthrough steps
- [ ] 5.4 Create demo scenario 2: 隐私/账号异常 (account issue + privacy leak risk)
  - 3–5 sample tickets
  - Expected pipeline flow: intake → classification → risk (ACCOUNT_SECURITY, PRIVACY_RISK, MEDIUM severity) → retrieval (FAQ + POLICY) → draft with privacy warning → must_human_review
  - Walkthrough steps
- [ ] 5.5 Create demo scenario 3: 发票/支付争议 (billing/invoice + payment dispute)
  - 3–5 sample tickets
  - Expected pipeline flow: intake → classification → risk (POLICY_CONFLICT, LOW-MEDIUM severity) → retrieval (FAQ + POLICY + CASE) → draft
  - Walkthrough steps
- [ ] 5.6 Run quality gate — must pass

## Batch 6: Limitations/README Update and Final Quality Gate

- [ ] 6.1 Create or update limitations documentation:
  - Data: synthetic/manufactured Chinese customer service scenarios, not real enterprise data
  - System: local demo/portfolio project, not production-ready
  - Embedding: deterministic fake embedding (384-dim hash), no semantic retrieval quality
  - Real semantic retrieval comparison deferred to Phase 8
  - All replies are drafts requiring human review — no auto-send (architecture-level guarantee)
- [ ] 6.2 Update README.md and README.en.md if ticket/knowledge counts are referenced
- [ ] 6.3 Update docs/changelog.md with Phase 7 entry
- [ ] 6.4 Run OpenSpec validate --all — expect 15/15
- [ ] 6.5 Run quality gate — must pass (Ruff ✓, 642 unit ✓, 119 integration ✓, coverage ≥70%)
- [ ] 6.6 Final commit and push

## Total Batch Summary

| Batch | Description | Files Changed | Validation |
|-------|-------------|---------------|------------|
| 1 | Baseline audit | None | OpenSpec + quality gate |
| 2 | Eval tickets + golden | data/eval/*.csv | OpenSpec + quality gate |
| 3 | Knowledge base | data/knowledge/*.json | OpenSpec + quality gate |
| 4 | No-auto-send alignment | data/eval/*.csv, reports/eval/* | Eval reports (no_auto_send=1.0) |
| 5 | Reports + demo docs | reports/eval/*, docs/demo/* | Quality gate |
| 6 | Limitations + final gate | docs/portfolio/*, README*.md, docs/changelog.md | OpenSpec + quality gate |
