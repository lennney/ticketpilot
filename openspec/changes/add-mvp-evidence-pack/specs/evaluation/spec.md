# add-mvp-evidence-pack — Evaluation Specification

## Baseline (Before Change)

- Eval tickets: 10 (in `data/eval/tickets_eval.csv`)
- Golden expectations: 10 (in `data/eval/golden_expectations.csv`)
- No-auto-send compliance (pipeline mode): 0.5 (5/10 cases incorrectly expect no_auto_send=false)
- No-auto-send compliance (CSV mode): 1.0 (hand-labeled predictions match)
- Evaluation report total_cases: 10
- Full baseline audit: `docs/data/phase7_baseline_audit.md` (recorded 2026-05-04)
- Adaptation candidate pool: `data/eval/adaptation_candidates.csv` (96 candidates, pending human review)
- Knowledge records: 36 expanded to 95 (FAQ=40, Policy=30, Case=25) — Phase 7B-4

## ADDED Requirements

### Requirement: Expanded Evaluation Dataset
The system SHALL provide an expanded evaluation dataset at `data/eval/tickets_eval.csv` containing approximately 100 synthetic Chinese customer service ticket records.

#### Scenario: Eval dataset contains ~100 tickets
- WHEN `load_tickets()` is called on `data/eval/tickets_eval.csv`
- THEN the result contains at least 90 tickets and at most 120 tickets

#### Scenario: All intent classes represented with depth
- WHEN the evaluation dataset is loaded
- THEN each of the 8 intent classes has at least 5 tickets
- AND at least 3 classes have 10+ tickets

#### Scenario: New billing/invoice domain represented
- WHEN the evaluation dataset is loaded
- THEN at least 8 tickets have scenario_type in ("billing", "invoice", "payment_dispute")

#### Scenario: Multi-intent tickets exist
- WHEN the evaluation dataset is loaded
- THEN at least 5 tickets have scenario_type indicating combined intents (e.g., "refund+complaint", "account+privacy")

#### Scenario: Edge case tickets present
- WHEN the evaluation dataset is loaded
- THEN at least one ticket has empty or single-character original_text
- AND at least one ticket has original_text exceeding 500 characters
- AND at least one ticket contains mixed Chinese/English text
- AND at least one ticket contains special characters or numbers only

#### Scenario: All risk flag types covered
- WHEN loaded golden expectations are analyzed
- THEN all 8 risk flag types (complaint, compensation, legal, account_security, privacy, policy_conflict, low_confidence, insufficient_evidence) appear across the dataset

#### Scenario: Severity distribution is balanced
- WHEN loaded golden expectations are analyzed
- THEN each severity level (LOW, MEDIUM, HIGH) has at least 15 tickets

### Requirement: Golden Expectations Consistency
The system SHALL maintain golden expectations at `data/eval/golden_expectations.csv` with exactly one entry per eval ticket.

#### Scenario: One-to-one mapping with tickets
- WHEN both CSVs are loaded
- THEN len(golden) == len(tickets)
- AND every ticket case_id has a matching golden entry

#### Scenario: No-auto-send is always true for architecture guarantee
- WHEN golden expectations are loaded
- THEN every entry has `expected_no_auto_send` = "true" (representing architecture-level draft-only constraint)

### Requirement: Evaluation Report Generation
The system SHALL generate evaluation reports with approximately 100 cases in both CSV and pipeline modes.

#### Scenario: CSV mode report covers all tickets
- WHEN `scripts/run_eval.py` is run in CSV prediction mode
- THEN the output report contains total_cases matching the ticket count

#### Scenario: Pipeline mode report covers all tickets
- WHEN `scripts/run_eval.py` is run in pipeline prediction mode
- THEN the output report contains total_cases matching the ticket count

#### Scenario: No-auto-send compliance is 1.0 in both modes
- WHEN evaluation reports are generated in both modes
- THEN aggregate_metrics.no_auto_send_compliance == 1.0 in both reports

## MODIFIED Requirements

### Requirement: No-Auto-Send Metric Definition (Changed)
The no_auto_send_compliance metric SHALL be redefined from a per-case prediction match to an architecture-level invariant.

**Old definition (inconsistent):**
- `no_auto_send_compliance` was scored per-case against golden expectations where `expected_no_auto_send` varied by risk level. Low-risk tickets expected `false`, high-risk expected `true`. The metric measured whether pipeline prediction matched per-case golden label.

**New definition (architecture-level):**
- `no_auto_send_compliance` MUST be scored against the architectural invariant: ALL pipeline output is draft-only (no send channel exists). Every ticket's prediction MUST have `predicted_no_auto_send=true`. The metric is 1.0 if and only if every case predicts `true`.

#### Scenario: Pipeline always predicts no_auto_send=true
- WHEN the pipeline processes any ticket (any intent, any risk level)
- THEN `predicted_no_auto_send` in the prediction output is always `true`

#### Scenario: CSV mode predictions match architecture guarantee
- WHEN sample_predictions.csv is loaded for CSV-mode evaluation
- THEN every row has `predicted_no_auto_send` = "true"

## DELETED Requirements

(None — metrics are redefined, not removed.)

## Data Sources

- All eval tickets are **synthetic**: manually crafted Chinese customer service scenarios.
- No real enterprise customer data is used.
- Golden expectations are manually labeled by the developer based on deterministic pipeline behavior and domain knowledge.
- Evaluations do not test semantic retrieval quality (fake embeddings are used).

## Validation

- OpenSpec validate --all passes (15/15)
- Quality gate passes (Ruff, 642 unit tests, 119 integration tests, 0 skipped, coverage ≥70%)
- Evaluation reports generate in both CSV and pipeline modes without error
- No-auto-send compliance = 1.0 in both report modes
