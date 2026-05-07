# draft-evaluation-metrics Specification

## ADDED Requirements

### Purpose

Define deterministic metric functions for evaluating evidence-grounded draft generation quality. Metrics are computed offline from `DraftGenerationResult` objects produced by `generate_draft()`. No real LLM API calls, no network dependencies.

---

### Requirement: Citation Precision Metric

The system SHALL provide a `citation_precision()` function that computes the proportion of valid citations among all cited evidence IDs.

#### Scenario: Fully valid citations
- **WHEN** `valid_cited_evidence_ids` = 5 and `cited_evidence_ids` = 5
- **THEN** `citation_precision()` returns 1.0

#### Scenario: Partially valid citations
- **WHEN** `valid_cited_evidence_ids` = 3 and `cited_evidence_ids` = 5
- **THEN** `citation_precision()` returns 0.6

#### Scenario: No citations
- **WHEN** `cited_evidence_ids` is empty
- **THEN** `citation_precision()` returns None (not an error — no citations to validate)

#### Scenario: Citations with no evidence available
- **WHEN** `cited_evidence_ids` is non-empty and `available_evidence_ids` is empty
- **THEN** `citation_precision()` returns 0.0 (citation to nothing)

---

### Requirement: Evidence Coverage Metric

The system SHALL provide an `evidence_coverage()` function that computes the proportion of available evidence IDs that were cited.

#### Scenario: Partial coverage
- **WHEN** `valid_cited_evidence_ids` = 2 and `available_evidence_ids` = 5
- **THEN** `evidence_coverage()` returns 0.4

#### Scenario: Full coverage
- **WHEN** `valid_cited_evidence_ids` = 4 and `available_evidence_ids` = 4
- **THEN** `evidence_coverage()` returns 1.0

#### Scenario: No evidence available
- **WHEN** `available_evidence_ids` is empty
- **THEN** `evidence_coverage()` returns None

---

### Requirement: Unsupported Claim Rate

The system SHALL provide an `unsupported_claim_rate()` function that computes the proportion of cases with non-empty unsupported_claims.

#### Scenario: Mixed cases
- **WHEN** 3 of 10 cases have `len(unsupported_claims) > 0`
- **THEN** `unsupported_claim_rate()` returns 0.3

#### Scenario: All clean
- **WHEN** 0 of 10 cases have unsupported claims
- **THEN** `unsupported_claim_rate()` returns 0.0

---

### Requirement: Forbidden Promise Rate

The system SHALL provide a `forbidden_promise_rate()` function that computes the proportion of cases where claim guard detected a forbidden promise.

#### Scenario: Forbidden promise detected
- **WHEN** `guard_result.has_forbidden_promise` is True for 1 of 10 cases
- **THEN** `forbidden_promise_rate()` returns 0.1

---

### Requirement: Guard Pass Rate

The system SHALL provide a `guard_pass_rate()` function that computes the proportion of cases where claim guard passed all checks.

#### Scenario: Mixed guard results
- **WHEN** 8 of 10 cases have `guard_result.guard_passed == True`
- **THEN** `guard_pass_rate()` returns 0.8

---

### Requirement: Citation Validation Pass Rate

The system SHALL provide a `citation_validation_pass_rate()` function that computes the proportion of cases where citation validation passed.

#### Scenario: Citation validation results
- **WHEN** `citation_validation.is_valid == True` for 9 of 10 cases
- **THEN** `citation_validation_pass_rate()` returns 0.9

---

### Requirement: Metric Determinism

All metric functions SHALL be pure functions with no side effects.

#### Scenario: Same input produces same output
- **WHEN** `citation_precision()` is called with the same DraftGenerationResult twice
- **THEN** it returns the same value both times

#### Scenario: No network calls
- **WHEN** any metric function is called
- **THEN** no network requests are made

---

### Requirement: JSON and Markdown Serialization

Metrics SHALL be serializable to JSON for machine-readable reports and to Markdown tables for human-readable reports.

#### Scenario: JSON serialization
- **WHEN** metric summary is serialized to JSON
- **THEN** it is valid JSON with all metric names and numeric values

#### Scenario: Markdown table
- **WHEN** metric summary is rendered as Markdown
- **THEN** it uses pipe-separated tables readable by humans

---

### Requirement: None Handling

Metrics that cannot be computed SHALL return `None` (not 0, not an error).

#### Scenario: Cannot compute due to missing data
- **WHEN** citation precision cannot be computed (no citations)
- **THEN** function returns None

#### Scenario: None is not treated as zero
- **WHEN** a metric returns None
- **THEN** it is not counted as a pass or a fail
- **THEN** aggregate None values are excluded from rate computation or clearly labeled
