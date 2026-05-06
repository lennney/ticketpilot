# Spec: Error Memory System

## Purpose

Defines the agent error memory and repair learning system for TicketPilot's AI Development Harness. This is a harness/process improvement spec, not a product runtime feature.

## ADDED Requirements

### Requirement: Raw Error Logging

The system SHALL record each error encountered during development with structured fields: id, date, phase, batch, error_type, symptom, root_cause, failed_command, repair_action, validation_after_fix, prevention_rule, recurrence_count, severity, promoted_to, related_files, commit_hash, status.

#### Scenario: New error logged
- **WHEN** a harness batch encounters an error
- **THEN** an error_memory.jsonl entry is created with all required fields

#### Scenario: Error entry complete
- **WHEN** error_memory.jsonl entry is created
- **THEN** it contains id, date, phase, error_type, symptom, root_cause, failed_command, repair_action, prevention_rule, severity, status

---

### Requirement: Structured Error Memory

The system SHALL use JSONL format for error memory entries. Each entry is append-only. Entries support audit and search.

#### Scenario: JSONL format
- **WHEN** an error entry is created
- **THEN** it is valid JSON when parsed individually

#### Scenario: Error searchable
- **WHEN** searching for error_type="encoding"
- **THEN** all encoding-related errors are found via grep or JSON parsing

---

### Requirement: Post-Failure Reflection

The system SHALL provide a post-failure reflection template that forces structured analysis of each failure.

#### Scenario: Template available
- **WHEN** a harness batch fails validation
- **THEN** the post_failure_reflection.md template guides the analysis

#### Scenario: Template includes prevention rule
- **WHEN** post-failure reflection is completed
- **THEN** a prevention_rule field is populated

---

### Requirement: Lesson Promotion Rules

The system SHALL promote lessons based on recurrence and severity:

- Same error twice: update repair_playbook
- Preventable by test: add regression test proposal
- Cross-phase impact: promote to AGENTS.md only after confirmation
- Harness process improvement: promote to preflight_checklist or agent_learning_rules

#### Scenario: Recurring error
- **WHEN** the same error occurs twice
- **THEN** repair_playbook is updated with the fix

#### Scenario: Testable error
- **WHEN** an error could have been prevented by a test
- **THEN** a regression test proposal is added to the entry

---

### Requirement: Preflight Checklist Update Rules

The system SHALL maintain a preflight checklist that is updated when systemic issues are discovered.

#### Scenario: New preflight check
- **WHEN** an error reveals a missing preflight check
- **THEN** preflight_checklist.md is updated

---

### Requirement: Regression Test Recommendation Rules

The system SHALL recommend regression tests when errors are preventable by automated checks.

#### Scenario: Test recommendation
- **WHEN** an error could be caught by a test
- **THEN** the error entry includes a regression_test_proposal field

---

### Requirement: Stale Memory Audit Rules

The system SHALL provide a memory audit template to prevent error memory from growing stale or contradictory.

#### Scenario: Audit template available
- **WHEN** periodic audit is needed
- **THEN** memory_audit.md guides the audit process

#### Scenario: Obsolete rules removed
- **WHEN** audit finds obsolete rules
- **THEN** they are marked stale or removed

---

### Requirement: Secret/Privacy Constraints

The error memory system SHALL explicitly exclude:
- API keys, tokens, Authorization headers
- Full chat transcripts
- Raw provider responses
- Private or emotional conversation content

#### Scenario: No API key in memory
- **WHEN** error is logged
- **THEN** no API key appears in the entry

#### Scenario: No chat transcript
- **WHEN** error is logged
- **THEN** no full chat transcript is stored

---

### Requirement: No Chat Transcript Storage

The system SHALL only store error metadata (type, symptom, command, fix, prevention). Full conversation content is never stored.

#### Scenario: Concise entries
- **WHEN** error_memory.jsonl entry is created
- **THEN** it contains only: error type, symptom, failed command, repair action, prevention rule