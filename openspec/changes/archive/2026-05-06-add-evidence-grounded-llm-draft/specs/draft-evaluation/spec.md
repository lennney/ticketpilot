# draft-evaluation Specification

## ADDED Requirements

### Requirement: Offline Evaluation Only
The system SHALL evaluate draft quality offline using existing evaluation data without requiring real LLM API access.

#### Scenario: Evaluation runs with FakeLLMProvider
- **WHEN** draft evaluation is executed
- **THEN** it completes using FakeLLMProvider without network access

#### Scenario: Evaluation uses 101-ticket dataset
- **WHEN** draft evaluation runs
- **THEN** it uses the same EvalDataset (101 synthetic tickets) as existing evaluation

### Requirement: Citation Precision Metric
The system SHALL compute citation precision as valid_citations / total_citations.

#### Scenario: All citations valid
- **WHEN** all citations reference valid evidence chunk_ids
- **THEN** citation precision is 1.0

#### Scenario: Some citations invalid
- **WHEN** 3 of 5 citations reference valid evidence
- **THEN** citation precision is 0.6

#### Scenario: No citations
- **WHEN** there are no citations
- **THEN** citation precision is 0.0 (or undefined, handled gracefully)

### Requirement: Evidence Coverage Metric
The system SHALL compute evidence coverage as cited_evidence_items / total_evidence_items.

#### Scenario: All evidence cited
- **WHEN** every evidence item is cited at least once
- **THEN** evidence coverage is 1.0

#### Scenario: Partial evidence cited
- **WHEN** 2 of 4 evidence items are cited
- **THEN** evidence coverage is 0.5

#### Scenario: No evidence items
- **WHEN** there are no evidence items
- **THEN** evidence coverage is 0.0 (or undefined, handled gracefully)

### Requirement: Unsupported Claim Rate Metric
The system SHALL compute unsupported claim rate as drafts_with_unsupported_claims / total_drafts.

#### Scenario: All drafts have citations
- **WHEN** no draft has unsupported claims
- **THEN** unsupported claim rate is 0.0

#### Scenario: Some drafts have unsupported claims
- **WHEN** 3 of 10 drafts have unsupported claims
- **THEN** unsupported claim rate is 0.3

### Requirement: Safe Fallback Rate Metric
The system SHALL compute safe fallback rate as correct_fallbacks / total_no_evidence_cases.

#### Scenario: All no-evidence cases fall back
- **WHEN** every no-evidence case correctly produces fallback draft
- **THEN** safe fallback rate is 1.0

#### Scenario: No no-evidence cases
- **WHEN** no cases require fallback
- **THEN** safe fallback rate is 1.0 (trivially)

### Requirement: Human Review Trigger Correctness
The system SHALL compute the proportion of cases where must_human_review matches the expected value.

#### Scenario: All triggers correct
- **WHEN** every case's must_human_review matches golden expectation
- **THEN** human review trigger correctness is 1.0

#### Scenario: Some triggers incorrect
- **WHEN** 8 of 10 cases have correct must_human_review
- **THEN** human review trigger correctness is 0.8

### Requirement: Forbidden Promise Rate Metric
The system SHALL compute the proportion of drafts with detected forbidden promises.

#### Scenario: No forbidden promises
- **WHEN** no draft contains forbidden promises
- **THEN** forbidden promise rate is 0.0

#### Scenario: Some forbidden promises
- **WHEN** 1 of 20 drafts contains a forbidden promise
- **THEN** forbidden promise rate is 0.05

### Requirement: Guard Pass Rate Metric
The system SHALL compute the proportion of drafts where guard_passed is True.

#### Scenario: All guards pass
- **WHEN** every draft has guard_passed=True
- **THEN** guard pass rate is 1.0

#### Scenario: Some guards fail
- **WHEN** 15 of 20 drafts have guard_passed=True
- **THEN** guard pass rate is 0.75

### Requirement: No Real-World Benchmark Claims
The system SHALL NOT claim production-level quality, industry benchmark performance, or real-world validation in evaluation reports.

#### Scenario: Disclaimer in evaluation report
- **WHEN** a draft evaluation report is generated
- **THEN** it includes the disclaimer "Offline evaluation on 101 synthetic tickets — not a production benchmark"

#### Scenario: No benchmark claims
- **WHEN** evaluation report is inspected
- **THEN** it contains no claims of production-ready or real-world performance

### Requirement: Golden Expectations Extension
The system SHALL extend GoldenExpectation with optional draft-specific fields.

#### Scenario: extension fields are optional
- **WHEN** GoldenExpectation is created with expected_citation_count
- **THEN** it validates successfully

#### Scenario: Existing golden data is backward-compatible
- **WHEN** existing golden expectations are loaded
- **THEN** they validate without draft-specific fields

### Requirement: Evaluation Report Integration
The system SHALL include draft metrics in standard evaluation report output (JSON + Markdown), distinguished from classification/risk/evidence metrics.

#### Scenario: Draft metrics in JSON report
- **WHEN** a JSON evaluation report is generated
- **THEN** it includes a draft_metrics section separate from other metric sections

#### Scenario: Draft metrics in Markdown report
- **WHEN** a Markdown evaluation report is generated
- **THEN** it includes a draft metrics section separate from other metric sections

### Requirement: Deterministic Fixture Tests
The system SHALL test draft evaluation metrics using deterministic fixture data.

#### Scenario: Known inputs produce expected outputs
- **WHEN** draft evaluation is run with fixture data
- **THEN** all computed metrics match expected values

### Requirement: Provider Identity in Evaluation
The system SHALL record which provider generated the evaluated drafts in all evaluation reports.

#### Scenario: Provider identity in report
- **WHEN** an evaluation report is generated
- **THEN** it records which provider generated the evaluated drafts

#### Scenario: Fake provider disclaimer
- **WHEN** FakeLLMProvider is used for evaluation
- **THEN** the report includes the disclaimer "Deterministic fake provider — draft quality metrics reflect pipeline mechanics, not semantic generation quality"
