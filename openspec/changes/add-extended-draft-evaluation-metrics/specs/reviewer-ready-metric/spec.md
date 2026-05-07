# reviewer-ready-metric Specification

## ADDED Requirements

### Purpose

Define the reviewer-ready metric for evidence-grounded draft evaluation. Reviewer-ready rate measures whether drafts are structurally safe enough for efficient human review — not whether they are auto-sendable.

---

### Requirement: Reviewer-Ready Definition

The system SHALL define reviewer-ready as a case where all three conditions hold: citation validation is valid, claim guard passed, and no unsupported claims.

A case is **reviewer-ready** when ALL of the following are true:
1. `citation_validation.is_valid == True`
2. `guard_result.guard_passed == True`
3. `len(draft.unsupported_claims) == 0`

#### Scenario: Reviewer-ready case
- **WHEN** all three conditions are True
- **THEN** the case is reviewer-ready

#### Scenario: Not reviewer-ready — citation validation failed
- **WHEN** `citation_validation.is_valid == False`
- **THEN** the case is NOT reviewer-ready

#### Scenario: Not reviewer-ready — guard failed
- **WHEN** `guard_result.guard_passed == False`
- **THEN** the case is NOT reviewer-ready

#### Scenario: Not reviewer-ready — unsupported claims
- **WHEN** `len(unsupported_claims) > 0`
- **THEN** the case is NOT reviewer-ready

---

### Requirement: Reviewer-Ready Does Not Override Human Review

HIGH-risk cases SHALL remain `must_human_review = True` even when reviewer-ready.

#### Scenario: HIGH risk + reviewer-ready
- **WHEN** `severity == HIGH` and the case is reviewer-ready
- **THEN** `must_human_review == True` AND `reviewer_ready == True`
- **AND** the case appears in the reviewer-ready count

#### Scenario: No auto-send
- **WHEN** a case is reviewer-ready
- **THEN** it is NOT eligible for auto-send
- **AND** the report explicitly states "reviewer-ready does not mean auto-send"

---

### Requirement: Reviewer-Ready Rate Computation

The system SHALL compute reviewer-ready rate as:
```
reviewer_ready_rate = reviewer_ready_cases / total_cases
```

#### Scenario: All reviewer-ready
- **WHEN** 20 of 25 cases are reviewer-ready
- **THEN** `reviewer_ready_rate()` returns 0.8

#### Scenario: Partial reviewer-ready
- **WHEN** 15 of 25 cases are reviewer-ready
- **THEN** `reviewer_ready_rate()` returns 0.6

---

### Requirement: Reviewer-Ready Reported Per Provider

The comparison report SHALL include reviewer-ready rate for each provider.

#### Scenario: Per-provider table
- **WHEN** the comparison summary is generated
- **THEN** it contains a row per provider with reviewer_ready_rate

---

### Requirement: Reviewer-Ready Failures Listed by Reason

The system SHALL list reviewer-ready failures by cause.

#### Scenario: Failure breakdown
- **WHEN** cases are not reviewer-ready
- **THEN** the report lists: citation validation failures, guard failures, unsupported claims (counts per reason)

---

### Requirement: Reviewer-Ready Does Not Mean Auto-Send

The reviewer-ready metric and report SHALL explicitly state that reviewer-ready does not permit auto-send.

#### Scenario: Disclaimer in report
- **WHEN** the reviewer-ready metric is reported
- **THEN** the report includes: "Reviewer-ready means the draft is structurally safe enough for human review. It does NOT mean the draft can be auto-sent. HIGH-risk cases always require human review."
