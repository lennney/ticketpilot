# provider-comparison-metrics Specification

## ADDED Requirements

### Purpose

Define the extended output schema and reporting format for the Phase 12/13 provider comparison runner. The comparison evaluates FakeLLMProvider vs OpenAICompatibleProvider on a fixed synthetic fixture set using offline evaluation only.

---

### Requirement: Extended Per-Case Row Schema

The provider comparison runner SHALL output extended per-case rows containing citation validation and claim guard results.

#### Scenario: Extended row fields
- **WHEN** a case is processed by `generate_draft()`
- **THEN** the row contains: case_id, scenario, provider, confidence, must_human_review, has_citations, citation_validation_is_valid, valid_cited_evidence_count, invalid_cited_evidence_count, available_evidence_count, citation_precision, evidence_coverage, guard_passed, has_forbidden_promise, has_uncited_claims, unsupported_claims_count, reviewer_ready, latency_ms (if measured)

---

### Requirement: Same Metrics for Fake and Real Provider

The comparison runner SHALL compute the same extended metrics for both FakeLLMProvider and OpenAICompatibleProvider when configured.

#### Scenario: Fake provider run
- **WHEN** FakeLLMProvider is run on the fixture set
- **THEN** extended rows include all citation validation and claim guard fields

#### Scenario: Real provider run
- **WHEN** OpenAICompatibleProvider is configured and run on the fixture set
- **THEN** extended rows include the same fields as the fake provider run

---

### Requirement: Fake Provider Does Not Require Real API

The comparison runner SHALL run the fake provider baseline without any API keys, environment configuration, or network access.

#### Scenario: Fake baseline without config
- **WHEN** `scripts/run_phase12_llm_provider_comparison.py` is run
- **THEN** FakeLLMProvider produces results without requiring TICKETPILOT_LLM_PROVIDER, TICKETPILOT_LLM_API_KEY, or any other environment variable

---

### Requirement: Real Provider Is Opt-In Only

The real provider SHALL only run when explicitly configured in `.env.local`. If not configured, the runner skips the real provider and reports it as not configured.

#### Scenario: Real provider not configured
- **WHEN** TICKETPILOT_LLM_PROVIDER is not set or set to "fake"
- **THEN** the comparison runner skips the real provider and logs "Real provider not configured"

#### Scenario: Real provider configured
- **WHEN** TICKETPILOT_LLM_PROVIDER=openai_compatible and required env vars are set
- **THEN** the runner calls the real provider and includes results in the report

---

### Requirement: Report Marks Provider Configuration Status

The comparison report SHALL clearly state whether each provider was configured or not.

#### Scenario: Report header
- **WHEN** the markdown report is generated
- **THEN** it states "FakeLLMProvider: always available (default)" and "OpenAICompatibleProvider: [configured / not configured]"

---

### Requirement: Report Uses Offline Boundary Wording

All provider comparison reports SHALL include explicit boundary statements.

#### Scenario: Required boundary wording
- **WHEN** a provider comparison report is generated
- **THEN** it includes: "offline provider comparison", "fixed synthetic case set", "not a benchmark", "not online performance", "not real enterprise validation"

---

### Requirement: Summary Metrics Include All Extended Metrics

The comparison summary SHALL include citation precision avg, evidence coverage avg, unsupported claim rate, forbidden promise rate, guard pass rate, citation validation pass rate, and reviewer-ready rate, per provider.

#### Scenario: Summary table
- **WHEN** the summary JSON is generated
- **THEN** it contains a table with: provider, cases, success, avg_confidence, human_review_triggers, citation_precision_avg, evidence_coverage_avg, unsupported_claim_rate, forbidden_promise_rate, guard_pass_rate, citation_validation_pass_rate, reviewer_ready_rate
