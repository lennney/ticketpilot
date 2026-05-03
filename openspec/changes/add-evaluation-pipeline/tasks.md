## Phase 1: Evaluation Data

- [x] 1.1 Create data/eval/tickets_eval.csv with 8-12 seed tickets:
  - Refund, return_exchange, account_issue, logistics, complaint
  - Privacy/account-security, no-evidence, high-risk complaint/legal
  - Technical issue, product consulting for full 8-intent coverage
  - Tickets at LOW, MEDIUM, HIGH severity
  - Tickets with must_human_review=True and False
- [x] 1.2 Create data/eval/golden_expectations.csv
- [x] 1.3 Validate dataset consistency (via load_eval_dataset with cross-reference checks)

## Phase 2: Reusable Evaluation Logic

- [x] 2.1 Create src/ticketpilot/evaluation/__init__.py
- [x] 2.2 Create src/ticketpilot/evaluation/schemas.py (Pydantic models: EvalTicket, GoldenExpectation, EvalDataset, LoadResult)
- [x] 2.3 Create src/ticketpilot/evaluation/loaders.py (CSV loading with validation)
- [x] 2.4 Create src/ticketpilot/evaluation/metrics.py
- [x] 2.5 Create src/ticketpilot/evaluation/predictions.py (prediction loader)
- [x] 2.6 Create src/ticketpilot/evaluation/reporting.py (report writers)

## Phase 3: Evaluation Runner Script

- [x] 3.1 Create scripts/run_eval.py
- [x] 3.2 Test runner manually

## Phase 4: Unit Tests

- [x] 4.1 Create tests/unit/test_evaluation_metrics.py
- [x] 4.2 Create tests/unit/test_evaluation_schemas.py
- [x] 4.3 Create tests/unit/test_evaluation_loaders.py
- [x] 4.4 Create tests/unit/test_evaluation_reporting.py
- [x] 4.5 Create tests/unit/test_evaluation_predictions.py

## Phase 5: Integration Tests

- [ ] 5.1 Create test fixture CSVs
- [ ] 5.2 Create tests/integration/test_evaluation_pipeline.py
- [ ] 5.3 Verify integration tests pass with existing quality gate

## Phase 6: Documentation

- [ ] 6.1 Create docs/technical/evaluation_pipeline.md (deferred to Batch 4)
- [x] 6.2 Update docs/changelog.md (Batch 3)
- [ ] 6.3 Update docs/phase_status.md (deferred to Batch 4)
- [x] 6.4 Run quality gate

## Batch Plan Summary

- Batch 1: Phase 1 (evaluation data) + Phase 2 (schemas + loaders) + Phase 4 (schema + loader tests) + changelog + quality gate
- Batch 2: Phase 2 (metrics) + Phase 4 (metric tests) + changelog + quality gate
- Batch 3: Phase 2 rest (predictions, reporting) + Phase 3 (runner) + remaining tests
- Batch 4: Phase 6 (documentation)
### Phase 1 Details

Required coverage:
- At least 2 tickets per intent class (8 classes = 16+ tickets)
- Tickets covering: LEGAL_RISK, COMPLAINT_RISK, ACCOUNT_SECURITY, INSUFFICIENT_EVIDENCE, NONE
- Tickets at HIGH, MEDIUM, LOW severity
- Tickets with must_human_review=True and False
- Edge cases: empty text, very long text, mixed intents
- At least 1 INSUFFICIENT_EVIDENCE ticket
- At least 1 account-security ticket
### Phase 2 Details - Evaluation Module Functions

loader.py: load_tickets(path), load_golden(path) - CSV loading with validation
metrics.py: intent_accuracy, risk_recall_precision, severity_correctness,
  must_human_review_accuracy, evidence_recall_at_k, citation_validity,
  draft_fallback_correctness, unsupported_claim_correctness, human_review_readiness
comparison.py: compare(ticket_output, golden) -> per-ticket results dict
report.py: build_report(all_results, metadata) -> report dict,
  write_report(report, path) -> None

### Phase 3 Details - Runner Script

CLI: python scripts/run_eval.py [--data-dir DIR] [--output FILE] [--verbose]
Pipeline calls: intake_risk_pipeline(), generate_draft()
Output: JSON report with metadata, summary, per_ticket
Error handling: per-ticket error capture, continue on failure, non-zero exit

### Phase 4 Details - Unit Test Coverage

test_evaluation_metrics.py: Each metric in isolation with various inputs
test_evaluation_loader.py: CSV edge cases, missing columns, empty files
test_evaluation_report.py: Report structure, JSON roundtrip
test_evaluation_comparison.py: Match/mismatch/error scenarios

### Phase 5 Details - Integration Test Coverage

3-5 ticket fixtures covering: refund+evidence, no-evidence, high-risk
Report structure validation: metadata, summary, per_ticket
All 9 metric categories present
Determinism assertion: two runs produce identical report

### Phase 6 Details - Documentation

Technical doc: evaluation_pipeline.md with full schema, metric formulas, examples
Changelog: new evaluation pipeline module entry
Phase status: evaluation pipeline phase tracking
Quality gate: scripts/run_quality_gate.sh must pass