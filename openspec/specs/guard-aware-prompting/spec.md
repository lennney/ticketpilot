# guard-aware-prompting Specification

## Purpose
TBD - created by archiving change add-guard-aware-provider-prompting. Update Purpose after archive.
## Requirements
### Requirement: Inline Citation Markers

The `OpenAICompatibleProvider` prompt MUST instruct the LLM to include inline `[chunk_id]` citation markers for every substantive factual or policy claim in the generated draft.

#### Scenario: Citation format matches evidence block IDs
- **WHEN** evidence block contains `[chunk_id]: {uuid}` and LLM cites this evidence
- **THEN** the draft text includes `[{uuid}]` format after the cited statement
- **AND** numeric `[1]`, `[2]` markers are not used as the primary citation format

#### Scenario: Numeric citation format is not valid
- **WHEN** evidence is formatted as `[1] Title: content...`
- **THEN** the prompt explicitly instructs not to use `[1]`, `[2]` numeric format
- **AND** claim guard's `_extract_chunk_ids()` will not recognize these as valid citations

#### Scenario: No citation markers in draft text
- **WHEN** LLM generates substantive content without `[chunk_id]` markers
- **THEN** claim guard detects `has_uncited_claims=True`
- **AND** human review is correctly triggered

---

### Requirement: Evidence Sufficiency Fallback

The `OpenAICompatibleProvider` prompt MUST instruct the LLM to use safe fallback text when the provided evidence does not support answering the customer's question.

#### Scenario: Insufficient evidence triggers safe fallback
- **WHEN** available evidence does not contain information relevant to the customer's question
- **THEN** the LLM generates the safe fallback text: `抱歉，基于目前的信息，无法为您提供准确的客服回复，建议您转人工客服获取详细帮助。`
- **AND** `must_human_review` is set to `True`

#### Scenario: Safe fallback lacks citation markers
- **WHEN** the LLM generates safe fallback text
- **THEN** the citation validator detects no `[chunk_id]` markers in the text
- **AND** citation validation fails (correctly — safe fallback should be reviewed)

---

### Requirement: Forbidden Promise Patterns

The `OpenAICompatibleProvider` prompt MUST instruct the LLM not to include forbidden promise patterns in the draft.

#### Scenario: Forbidden refund amount pattern detected
- **WHEN** draft contains pattern matching `退款\d+元` or `退款金额`
- **THEN** claim guard sets `has_forbidden_promise=True`
- **AND** guard fails (`guard_passed=False`)

#### Scenario: Forbidden compensation pattern detected
- **WHEN** draft contains pattern matching `赔偿\d+元` or `赔偿金额`
- **THEN** claim guard sets `has_forbidden_promise=True`
- **AND** guard fails

---

### Requirement: No-Auto-Send Boundary

The `OpenAICompatibleProvider` prompt MUST state that the generated reply is a draft only and cannot be auto-sent without human review.

#### Scenario: Draft is explicitly marked as non-final
- **WHEN** the prompt includes no-auto-send instruction
- **THEN** the generated text is presented as a draft reply
- **AND** the system architecture enforces no-auto-send at runtime (not enforced by prompt alone)

---

### Requirement: Risk Flag Escalation Acknowledgment

The `OpenAICompatibleProvider` prompt MUST instruct the LLM to include escalation acknowledgment language when the ticket contains HIGH or CRITICAL severity or risk flags.

#### Scenario: HIGH severity ticket requires escalation
- **WHEN** `severity` is `high` or `critical`
- **THEN** the prompt instructs the LLM to suggest human review/escalation
- **AND** claim guard's `risk_flags_respected` check looks for escalation keywords

#### Scenario: Risk flag present without escalation
- **WHEN** ticket has `legal`, `compensation`, or `privacy` risk flag
- **AND** draft does not include escalation acknowledgment language (转人工, 人工处理, etc.)
- **THEN** claim guard sets `risk_flags_respected=False`
- **AND** guard fails

---

