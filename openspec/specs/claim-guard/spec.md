# claim-guard Specification

## Purpose
TBD - created by archiving change add-evidence-grounded-llm-draft. Update Purpose after archive.
## Requirements
### Requirement: Citation Existence Validation
The system SHALL verify every [chunk_id] reference in draft_text corresponds to a valid Citation referencing a real EvidenceCandidate.

#### Scenario: Valid citation passes
- **WHEN** draft_text references [chunk_id] that exists in citations and matches an EvidenceCandidate
- **THEN** the guard check passes for citation existence

#### Scenario: Invalid chunk_id fails
- **WHEN** draft_text references [chunk_id] that does not exist in citations or evidence
- **THEN** the guard flags it as a failure in GuardResult

#### Scenario: No citations passes trivially
- **WHEN** draft_text has no [chunk_id] references
- **THEN** citation existence check passes trivially

### Requirement: Unsupported Claim Detection
The system SHALL detect statements making factual or policy claims without accompanying citations.

#### Scenario: Uncited claim detected
- **WHEN** draft_text contains a factual statement without [chunk_id] citation
- **THEN** GuardResult.has_uncited_claims is True

#### Scenario: Greeting is exempt
- **WHEN** draft_text contains only a greeting without citation
- **THEN** it is not flagged as an uncited claim

#### Scenario: Fully cited draft passes
- **WHEN** all substantive claims in draft_text have citations
- **THEN** GuardResult.has_uncited_claims is False

### Requirement: Forbidden Promise Detection
The system SHALL detect and flag specific forbidden promise patterns in draft_text.

#### Scenario: Refund amount detected
- **WHEN** draft_text contains "退款XX元" or "赔偿XX元" pattern
- **THEN** GuardResult.has_forbidden_promise is True and the promise is listed in forbidden_promise_details

#### Scenario: Legal action guarantee detected
- **WHEN** draft_text contains "我们一定会起诉" or similar legal guarantee
- **THEN** GuardResult.has_forbidden_promise is True

#### Scenario: Account change detected
- **WHEN** draft_text contains "已为您修改密码" or similar account action
- **THEN** GuardResult.has_forbidden_promise is True

#### Scenario: Resolution timeline detected
- **WHEN** draft_text contains "X天内解决" or "保证X天"
- **THEN** GuardResult.has_forbidden_promise is True

#### Scenario: Liability admission detected
- **WHEN** draft_text contains "承认责任" or "我方过错"
- **THEN** GuardResult.has_forbidden_promise is True

#### Scenario: Clean draft passes
- **WHEN** draft_text contains no forbidden promise patterns
- **THEN** GuardResult.has_forbidden_promise is False

### Requirement: Evidence Sufficiency Check
The system SHALL assess whether evidence sufficiently covers the customer's request.

#### Scenario: Sufficient evidence passes
- **WHEN** evidence candidates cover the customer's issue
- **THEN** GuardResult.evidence_sufficiency is "sufficient"

#### Scenario: Partial evidence flagged
- **WHEN** some but not all aspects of the request are covered by evidence
- **THEN** GuardResult.evidence_sufficiency is "partial"

#### Scenario: No evidence flagged
- **WHEN** no evidence candidates match the customer's request
- **THEN** GuardResult.evidence_sufficiency is "insufficient"

### Requirement: Risk-Aware Check
The system SHALL verify high-risk flags are acknowledged in the draft.

#### Scenario: Legal risk acknowledged
- **WHEN** RiskAssessment has LEGAL_RISK
- **THEN** guard verifies draft mentions escalation to human review

#### Scenario: Compensation risk acknowledged
- **WHEN** RiskAssessment has COMPENSATION_RISK
- **THEN** guard verifies draft mentions escalation to human review

#### Scenario: Privacy risk acknowledged
- **WHEN** RiskAssessment has PRIVACY_RISK
- **THEN** guard verifies draft mentions escalation to human review

#### Scenario: Account security risk acknowledged
- **WHEN** RiskAssessment has ACCOUNT_SECURITY_RISK
- **THEN** guard verifies draft mentions escalation to human review

#### Scenario: No risk flags trivially passes
- **WHEN** RiskAssessment has no high-risk flags
- **THEN** risk_flags_respected is True

### Requirement: Guard Failure Forces Human Review
The system SHALL set must_human_review=True when guard_passed is False.

#### Scenario: Guard failure triggers human review
- **WHEN** GuardResult.guard_passed is False
- **THEN** DraftReply.must_human_review is True

#### Scenario: Guard pass does not change review status
- **WHEN** GuardResult.guard_passed is True and risk assessment did not require review
- **THEN** DraftReply.must_human_review remains as determined by risk assessment

### Requirement: High-Risk Forces Human Review
The system SHALL set must_human_review=True when RiskAssessment.must_human_review is True, regardless of guard results.

#### Scenario: High-risk overrides guard pass
- **WHEN** RiskAssessment.must_human_review is True and guard_passed is True
- **THEN** DraftReply.must_human_review is True

#### Scenario: High-risk plus guard failure
- **WHEN** RiskAssessment.must_human_review is True and guard_passed is False
- **THEN** DraftReply.must_human_review is True and both reasons are recorded

### Requirement: Full GuardResult Output
The system SHALL produce a complete GuardResult object attached to DraftReply.guard_results.

#### Scenario: GuardResult has all fields
- **WHEN** GuardResult is created
- **THEN** it contains citation_coverage, has_uncited_claims, has_forbidden_promise, forbidden_promise_details, evidence_sufficiency, risk_flags_respected, guard_passed

#### Scenario: GuardResult attached to DraftReply
- **WHEN** guard check runs and DraftReply is generated
- **THEN** DraftReply.guard_results is populated with the GuardResult

#### Scenario: GuardResult defaults when guard is skipped
- **WHEN** no guard check runs (e.g., during fallback)
- **THEN** DraftReply.guard_results may be None

### Requirement: Deterministic Guard
The system SHALL operate the claim guard deterministically using rule-based pattern matching.

#### Scenario: Same input same output
- **WHEN** claim guard is called twice with identical inputs
- **THEN** both GuardResult outputs are identical

#### Scenario: No network calls
- **WHEN** claim guard runs
- **THEN** no HTTP requests, no API calls, no database queries are made

