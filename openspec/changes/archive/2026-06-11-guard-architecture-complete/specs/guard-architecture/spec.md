# Guard Architecture — Granular Failure Taxonomy Specification

## Purpose

Extend `GuardResult` with a granular `GuardFailureType` taxonomy to classify distinct guard failure modes. The taxonomy enables per-failure-type metrics, better failure interpretation, and targeted improvement strategies. This spec extends — not replaces — the existing `claim-guard` and `guard-aware-prompting` specs. All existing guard checks, boolean fields, and `guard_passed` logic remain unchanged.

---

## ADDED Requirements

### Requirement: Guard Taxonomy Classification

The system SHALL classify each guard failure into one or more `GuardFailureType` values.

#### Scenario: Unsupported policy claim
- **WHEN** `has_uncited_claims=True`
- **THEN** `failure_reasons` includes `UNSUPPORTED_POLICY_CLAIM`
- **AND** `guard_passed` remains `False`

#### Scenario: Forbidden promise
- **WHEN** `has_forbidden_promise=True`
- **THEN** `failure_reasons` includes `FORBIDDEN_PROMISE`
- **AND** `guard_passed` remains `False`

#### Scenario: Missing risk escalation
- **WHEN** `risk_flags_respected=False` (HIGH severity ticket or risk flag present, escalation language absent)
- **THEN** `failure_reasons` includes `MISSING_RISK_ESCALATION`
- **AND** `guard_passed` remains `False`

#### Scenario: Evidence insufficient fallback
- **WHEN** draft text matches safe fallback text exactly
- **THEN** `failure_reasons` includes `EVIDENCE_INSUFFICIENT_FALLBACK`
- **AND** this is distinct from `UNSUPPORTED_POLICY_CLAIM`

#### Scenario: Ambiguous guard case
- **WHEN** available data is insufficient to determine a specific failure type
- **THEN** `failure_reasons` includes `AMBIGUOUS_GUARD_CASE`
- **AND** this surfaces ambiguity rather than hiding it

#### Scenario: Multiple failure reasons
- **WHEN** draft has multiple failure types (e.g., unsupported claims AND forbidden promise)
- **THEN** `failure_reasons` includes all applicable types
- **AND** `guard_passed` remains `False`

#### Scenario: Guard passes with no failures
- **WHEN** `guard_passed=True`
- **THEN** `failure_reasons` is an empty list `[]`

---

### Requirement: Safe Escalation Language

The system SHALL detect safe escalation language in the draft text.

#### Scenario: Safe escalation statement detected
- **WHEN** draft contains keywords: 人工处理, 转人工客服, 需要人工审核, 人工审查, 升级至人工, 已升级人工
- **THEN** a safe escalation statement is present
- **AND** `failure_reasons` does NOT include `MISSING_RISK_ESCALATION` solely on this basis

#### Scenario: Escalation language does not override guard failure
- **WHEN** draft contains escalation language AND `has_uncited_claims=True`
- **THEN** `failure_reasons` includes both `SAFE_ESCALATION_STATEMENT` and `UNSUPPORTED_POLICY_CLAIM`
- **AND** `guard_passed` remains `False`

#### Scenario: Escalation language does not satisfy risk escalation requirement
- **WHEN** ticket has HIGH severity and draft contains escalation language
- **THEN** risk escalation requirement is satisfied for `risk_flags_respected`
- **AND** `risk_flags_respected=True` only if escalation language is present

---

### Requirement: Manual Review Acknowledgement

The system SHALL detect manual review acknowledgement in the draft text.

#### Scenario: Manual review acknowledgement detected
- **WHEN** draft contains keywords: 人工审核, 需人工 review, 人工确认, 需人工介入
- **THEN** `failure_reasons` may include `MANUAL_REVIEW_ACKNOWLEDGEMENT`
- **AND** this is distinct from `SAFE_ESCALATION_STATEMENT`

#### Scenario: Manual review acknowledgement does not override guard failure
- **WHEN** draft acknowledges manual review but contains forbidden promise
- **THEN** `failure_reasons` includes `MANUAL_REVIEW_ACKNOWLEDGEMENT` and `FORBIDDEN_PROMISE`
- **AND** `guard_passed` remains `False`

---

### Requirement: Evidence-Insufficient Fallback

The system SHALL classify safe fallback drafts as `EVIDENCE_INSUFFICIENT_FALLBACK`.

#### Scenario: Safe fallback text matched
- **WHEN** draft text matches: `抱歉，基于目前的信息，无法为您提供准确的客服回复，建议您转人工客服获取详细帮助。`
- **THEN** `failure_reasons` includes `EVIDENCE_INSUFFICIENT_FALLBACK`
- **AND** `unsupported_claims` in draft may be empty (fallback is exempt)

#### Scenario: Safe fallback is a distinct failure type
- **WHEN** draft uses safe fallback
- **THEN** `failure_reasons` does NOT include `UNSUPPORTED_POLICY_CLAIM`
- **AND** `EVIDENCE_INSUFFICIENT_FALLBACK` is the appropriate type

---

### Requirement: Risk Escalation Acknowledgement

The system SHALL detect when HIGH severity or risk-flagged tickets lack escalation acknowledgment.

#### Scenario: HIGH severity without escalation
- **WHEN** ticket severity is `high` or `critical` AND draft does not contain escalation keywords
- **THEN** `risk_flags_respected=False`
- **AND** `failure_reasons` includes `MISSING_RISK_ESCALATION`

#### Scenario: Risk flag present without escalation
- **WHEN** ticket has risk flag (legal, compensation, privacy, account_security) AND draft lacks escalation language
- **THEN** `risk_flags_respected=False`
- **AND** `failure_reasons` includes `MISSING_RISK_ESCALATION`

#### Scenario: Escalation present with risk flag
- **WHEN** ticket has risk flag AND draft contains escalation keywords (人工, 转人工, 人工处理, etc.)
- **THEN** `risk_flags_respected=True`
- **AND** `failure_reasons` does not include `MISSING_RISK_ESCALATION`

---

### Requirement: No Guard Weakening

The taxonomy SHALL NOT weaken any existing guard check.

#### Scenario: Existing boolean fields unchanged
- **WHEN** `has_uncited_claims`, `has_forbidden_promise`, `risk_flags_respected` are computed
- **THEN** the existing logic is unchanged
- **AND** `failure_reasons` is computed in addition to (not instead of) booleans

#### Scenario: guard_passed unchanged
- **WHEN** `guard_passed` is computed
- **THEN** it is the AND of existing boolean checks
- **AND** the taxonomy does not change its value

#### Scenario: Human review requirement unchanged
- **WHEN** `guard_passed=False`
- **THEN** `must_human_review=True`
- **AND** the taxonomy does not change this propagation

#### Scenario: No-auto-send invariant unchanged
- **WHEN** a draft is generated
- **THEN** it is never auto-sent
- **AND** the taxonomy does not affect this architectural constraint

---

### Requirement: Taxonomy Is Informational

The taxonomy SHALL provide granular failure classification without changing system behavior.

#### Scenario: Taxonomy used for reporting
- **WHEN** per-failure-type metrics are computed
- **THEN** they are derived from `failure_reasons` for reporting purposes only
- **AND** they do not affect `guard_passed` or `must_human_review`

#### Scenario: Backward compatibility
- **WHEN** existing code reads `has_uncited_claims`, `has_forbidden_promise`, `guard_passed`
- **THEN** these fields behave identically to before this spec
- **AND** the taxonomy is additive only

---

## Non-Requirements

### Scenario: Taxonomy does not prevent failures
- **WHEN** taxonomy classifies a failure type
- **THEN** it does not prevent that failure from occurring
- **AND** prevention remains the responsibility of prompt engineering and guard architecture

### Scenario: Ambiguous cases are not resolved
- **WHEN** a case is classified as `AMBIGUOUS_GUARD_CASE`
- **THEN** the taxonomy does not resolve the ambiguity
- **AND** manual investigation may be required

### Scenario: Taxonomy does not change FakeLLMProvider behavior
- **WHEN** `TICKETPILOT_LLM_PROVIDER=fake`
- **THEN** `GuardResult.failure_reasons` is computed using the same logic
- **AND** FakeLLMProvider template-based output is unaffected by taxonomy
