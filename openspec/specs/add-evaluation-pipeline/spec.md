# add-evaluation-pipeline Specification

## Purpose
TBD - created by archiving change add-evaluation-pipeline. Update Purpose after archive.
## Requirements
### Requirement: Evaluation Dataset Schema
The system SHALL define an evaluation dataset as a CSV file
at data/eval/tickets_eval.csv with columns: ticket_id (str, unique),
raw_text (str), expected_intent (str), expected_risk_flags
(str, pipe-delimited), expected_severity (str: HIGH|MEDIUM|LOW),
expected_must_human_review (bool), expected_evidence_doc_ids
(str, pipe-delimited), expected_citations_valid (bool),
expected_fallback (str: none|no_evidence|high_risk|generation_error),
expected_unsupported_claims (bool), notes (str, optional).

#### Scenario: Valid tickets CSV loads successfully
- WHEN load_tickets() is called with a valid CSV path
- THEN it returns a list of dicts with all columns present

#### Scenario: Missing required column raises ValueError
- WHEN load_tickets() is called with a CSV missing a required column
- THEN a ValueError is raised identifying the missing column

#### Scenario: Duplicate ticket_id raises ValueError
- WHEN load_tickets() is called with a CSV containing duplicate ticket_id
- THEN a ValueError is raised

#### Scenario: At least 15 tickets in evaluation dataset
- WHEN the evaluation dataset is loaded
- THEN it contains at least 15 tickets

#### Scenario: All intent classes represented
- WHEN the evaluation dataset is loaded
- THEN at least one ticket exists for each of the 8 intent classes

#### Scenario: All risk categories represented
- WHEN the evaluation dataset is loaded
- THEN at least one ticket exists for each risk category

### Requirement: Golden Expectations Schema
The system SHALL define golden expectations as a CSV file
at data/eval/golden_expectations.csv with columns matching
the expected_* fields, keyed by ticket_id.

#### Scenario: Golden expectations load successfully
- WHEN load_golden() is called with a valid CSV path
- THEN it returns a dict keyed by ticket_id

#### Scenario: All ticket_ids in golden exist in tickets
- WHEN both CSVs are loaded
- THEN every golden ticket_id exists in tickets_eval

### Requirement: Intent Classification Accuracy Metric
The system SHALL compute intent classification accuracy as
the fraction of tickets where classification.intent matches expected_intent exactly.

#### Scenario: All intents correct yields accuracy 1.0
- WHEN all classification intents match expected intents
- THEN intent_accuracy.value equals 1.0

#### Scenario: Half intents correct yields accuracy 0.5
- WHEN exactly half of classification intents match
- THEN intent_accuracy.value equals 0.5

#### Scenario: Empty list yields accuracy 0.0
- WHEN the input lists are empty
- THEN intent_accuracy.value equals 0.0, correct=0, total=0

#### Scenario: Result dict has correct structure
- WHEN intent_accuracy is computed
- THEN the result dict contains keys: value, correct, total, error, details

### Requirement: Risk Flag Recall / Precision Metric
The system SHALL compute risk flag recall and precision
as macro-averaged fractions across all tickets.

#### Scenario: Full overlap yields recall 1.0 and precision 1.0
- WHEN all expected flags appear in actual flags
- THEN risk_flag_recall.value equals 1.0
- AND risk_flag_precision.value equals 1.0

#### Scenario: Partial overlap yields proportional scores
- WHEN 2 of 4 expected flags appear in actual output
- THEN risk_flag_recall.value equals 0.5

#### Scenario: No expected flags yields recall 0.0
- WHEN expected flags list is empty
- THEN recall for that ticket is 0.0

#### Scenario: No actual flags yields precision 1.0
- WHEN actual flags list is empty
- THEN precision for that ticket is 1.0

### Requirement: Severity Correctness Metric
The system SHALL compute severity correctness as the fraction
of tickets where risk_assessment.severity matches expected_severity.

#### Scenario: All severities correct yields 1.0
- WHEN all risk assessment severities match expected
- THEN severity_correctness.value equals 1.0

### Requirement: must_human_review Trigger Accuracy Metric
The system SHALL compute must_human_review accuracy as the fraction
of tickets where risk_assessment.must_human_review matches expected.

#### Scenario: All matches yield accuracy 1.0
- WHEN all must_human_review values match
- THEN must_human_review_accuracy.value equals 1.0

### Requirement: Evidence Recall@k Metric
The system SHALL compute evidence recall@k for k=1, 3, 5
as the fraction of expected doc IDs appearing in top-k candidates.

#### Scenario: Full recall at k=3
- WHEN all expected doc IDs appear in top-3 evidence candidates
- THEN evidence_recall_at_3.value equals 1.0

#### Scenario: k=5 recall >= k=3 recall >= k=1 recall
- WHEN recall@k is computed for all k
- THEN recall@5 >= recall@3 >= recall@1 (monotonic property)

### Requirement: Citation Validity Rate Metric
The system SHALL compute citation validity rate as the fraction
of draft citations where the cited chunk ID exists in evidence
candidates and the evidence excerpt is non-empty.

#### Scenario: All citations valid yields 1.0
- WHEN every citation references an existing chunk
- THEN citation_validity_rate.value equals 1.0

#### Scenario: Some citations invalid yields proportional rate
- WHEN 5 of 10 citations reference nonexistent chunks
- THEN citation_validity_rate.value equals 0.5

#### Scenario: No citations yields 0.0
- WHEN no citations are produced
- THEN citation_validity_rate.value equals 0.0, total=0

### Requirement: Draft Fallback Correctness Metric
The system SHALL compute draft fallback correctness as
the fraction where actual fallback type matches expected.

#### Scenario: All fallbacks match yields 1.0
- WHEN every ticket fallback type matches expected
- THEN draft_fallback_correctness.value equals 1.0

### Requirement: Unsupported-Claim Guard Correctness Metric
The system SHALL compute unsupported-claim guard correctness
as the fraction where unsupported_claims presence matches expectation.

#### Scenario: Guard fires correctly for all tickets
- WHEN unsupported_claims presence matches expectation for every ticket
- THEN unsupported_claim_guard_correctness.value equals 1.0

### Requirement: Human-Review Decision Readiness Metric
The system SHALL compute human-review decision readiness as
a composite score checking: final_intent matches expected,
must_human_review matches risk flag, and timestamp exists.

#### Scenario: All sub-checks pass yields 1.0
- WHEN all three sub-conditions pass for all tickets
- THEN human_review_readiness.value equals 1.0

### Requirement: Evaluation Runner
The system SHALL implement scripts/run_eval.py as a standalone
Python script that loads dataset, runs pipeline, compares outputs,
and writes a structured JSON report.

#### Scenario: Runner produces valid report
- WHEN run_eval.py is executed with valid data
- THEN it produces a JSON report with metadata, summary, per_ticket

#### Scenario: Runner is deterministic
- WHEN run_eval.py is executed twice with same input
- THEN both output reports are identical

#### Scenario: Runner handles pipeline errors gracefully
- WHEN a ticket fails processing
- THEN the error is recorded in failed_tickets list and processing continues

#### Scenario: Runner exits with non-zero on failure
- WHEN any ticket fails processing
- THEN the runner exits with a non-zero exit code

### Requirement: Report Format
The system SHALL produce evaluation reports in JSON format
with three top-level sections: metadata, summary, per_ticket.

#### Scenario: Report contains metadata
- WHEN a report is generated
- THEN metadata includes: timestamp, dataset, num_tickets, failed_tickets, constraints

#### Scenario: Report contains per_ticket results
- WHEN a report is generated
- THEN per_ticket has one entry per ticket with ticket_id, results, errors

### Requirement: Limitations Documentation
The system SHALL document all evaluation limitations in report metadata.

#### Scenario: Report includes fake embedding limitation
- WHEN a report is generated
- THEN metadata.constraints states evaluation uses fake embeddings

#### Scenario: Report includes fake draft limitation
- WHEN a report is generated
- THEN metadata.constraints states evaluation uses fake draft provider

#### Scenario: Report includes dataset size limitation
- WHEN a report is generated
- THEN metadata.constraints states results are not statistically significant

### Requirement: Determinism
The evaluation pipeline SHALL be deterministic: identical input
data and code always produce identical output reports.

#### Scenario: Two identical runs produce identical output
- WHEN the evaluation is run twice with same data and code
- THEN the output reports are byte-identical

### Requirement: No Production Code Modification
The evaluation pipeline SHALL NOT modify any existing
production code in src/ticketpilot/.

#### Scenario: Existing tests pass after evaluation addition
- WHEN all existing tests are run
- THEN they pass without modification

#### Scenario: No src/ files are modified
- WHEN the evaluation change is applied
- THEN only new files are created; no existing src/ files are modified

