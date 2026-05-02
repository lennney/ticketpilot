## Phase 1: Evaluation Data

- [ ] 1.1 Create data/eval/tickets_eval.csv with 15-25 seed tickets:
  - At least 2 tickets per intent class
  - Tickets covering each risk category
  - Tickets at each severity level
  - Edge cases: empty text, very long text, mixed intents
- [ ] 1.2 Create data/eval/golden_expectations.csv
- [ ] 1.3 Validate dataset consistency

## Phase 2: Reusable Evaluation Logic

- [ ] 2.1 Create src/ticketpilot/evaluation/__init__.py
- [ ] 2.2 Create src/ticketpilot/evaluation/loader.py
- [ ] 2.3 Create src/ticketpilot/evaluation/metrics.py
- [ ] 2.4 Create src/ticketpilot/evaluation/comparison.py
- [ ] 2.5 Create src/ticketpilot/evaluation/report.py

## Phase 3: Evaluation Runner Script

- [ ] 3.1 Create scripts/run_eval.py
- [ ] 3.2 Test runner manually

## Phase 4: Unit Tests

- [ ] 4.1 Create tests/unit/test_evaluation_metrics.py
- [ ] 4.2 Create tests/unit/test_evaluation_loader.py
- [ ] 4.3 Create tests/unit/test_evaluation_report.py
- [ ] 4.4 Create tests/unit/test_evaluation_comparison.py

## Phase 5: Integration Tests

- [ ] 5.1 Create test fixture CSVs
- [ ] 5.2 Create tests/integration/test_evaluation_pipeline.py
- [ ] 5.3 Verify integration tests pass with existing quality gate

## Phase 6: Documentation

- [ ] 6.1 Create docs/technical/evaluation_pipeline.md
- [ ] 6.2 Update docs/changelog.md
- [ ] 6.3 Update docs/phase_status.md
- [ ] 6.4 Run quality gate

## Batch Plan Summary

- Batch 1: Phase 1 (evaluation data)
- Batch 2: Phases 2-3 (evaluation logic + runner)
- Batch 3: Phases 4-5 (tests)
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