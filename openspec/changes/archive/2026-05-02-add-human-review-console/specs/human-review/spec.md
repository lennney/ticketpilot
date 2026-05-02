# Human Review Console Specification

## ADDED Requirements

### Requirement: ReviewAction Enum
The system SHALL define a ReviewAction enum with four values: APPROVE, EDIT, ESCALATE, REJECT.

#### Scenario: ReviewAction has four values
- **WHEN** ReviewAction is inspected
- **THEN** it contains exactly APPROVE, EDIT, ESCALATE, and REJECT

#### Scenario: ReviewAction is a string enum
- **WHEN** ReviewAction.APPROVE is compared to the string "approve"
- **THEN** they are equal

### Requirement: ReviewDecision Schema
The system SHALL define a ReviewDecision Pydantic model with fields: review_id (str), ticket_id (str), ticket_text (str), action (ReviewAction), edited_text (str | None), decision_reason (str), original_draft_text (str), confidence (float), had_unsupported_claims (bool), was_high_risk (bool), intent (str), risk_flags (list[str]), citations_summary (list[dict]), evidence_used_count (int), reviewed_at (datetime).

#### Scenario: Valid ReviewDecision constructs successfully
- **WHEN** ReviewDecision is created with all required fields
- **THEN** it passes Pydantic validation and serializes to JSON

#### Scenario: ReviewDecision defaults are correct
- **WHEN** ReviewDecision is created without optional fields
- **THEN** edited_text defaults to None
- **AND** decision_reason defaults to ""
- **AND** had_unsupported_claims defaults to False
- **AND** was_high_risk defaults to False
- **AND** risk_flags defaults to empty list
- **AND** citations_summary defaults to empty list
- **AND** evidence_used_count defaults to 0

#### Scenario: ReviewDecision JSON serialization roundtrip
- **WHEN** ReviewDecision is serialized via model_dump_json() and deserialized
- **THEN** all fields are preserved correctly

#### Scenario: ReviewDecision rejects invalid action
- **WHEN** ReviewDecision is created with action set to an invalid string
- **THEN** Pydantic ValidationError is raised

### Requirement: ReviewStore Persistence
The system SHALL implement ReviewStore as a JSONL-based persistence layer for review decisions.

#### Scenario: ReviewStore saves and loads a single decision
- **WHEN** a ReviewDecision is saved via ReviewStore.save()
- **THEN** ReviewStore.load_all() returns a list containing that decision

#### Scenario: ReviewStore accumulates multiple decisions
- **WHEN** three ReviewDecisions are saved sequentially
- **THEN** ReviewStore.load_all() returns a list of three decisions in order

#### Scenario: ReviewStore handles empty file
- **WHEN** ReviewStore.load_all() is called on an empty or non-existent file
- **THEN** it returns an empty list

#### Scenario: ReviewStore roundtrip preserves all fields
- **WHEN** a ReviewDecision is saved then loaded
- **THEN** all fields including nested fields match the original

### Requirement: Streamlit Review Console
The system SHALL provide a Streamlit-based console for human review of evidence-grounded draft replies.

#### Scenario: Console loads without error
- **WHEN** the console module is imported
- **THEN** no ImportError or RuntimeError is raised

#### Scenario: Console displays ticket input options
- **WHEN** the console is rendered
- **THEN** it provides a sample ticket selector or raw text input
- **AND** it shows a button to process the selected ticket

#### Scenario: Console displays full processing output
- **WHEN** a ticket is processed through the pipeline
- **THEN** the console displays: ticket text, intent classification, risk assessment, evidence candidates, draft reply, and citations

#### Scenario: Console highlights risk and unsupported claims
- **WHEN** a high-risk ticket or draft with unsupported claims is displayed
- **THEN** the console visually distinguishes these from normal drafts
- **AND** must_human_review status is shown prominently

#### Scenario: Console supports approve action
- **WHEN** the reviewer clicks Approve
- **THEN** a ReviewDecision with action=APPROVE is saved
- **AND** the original draft text is preserved in the decision

#### Scenario: Console supports edit action
- **WHEN** the reviewer clicks Edit and submits edited text
- **THEN** an editable text area is shown pre-filled with the draft
- **AND** a ReviewDecision with action=EDIT and edited_text is saved

#### Scenario: Console supports escalate action
- **WHEN** the reviewer clicks Escalate and provides notes
- **THEN** a ReviewDecision with action=ESCALATE and decision_reason is saved

#### Scenario: Console supports reject action
- **WHEN** the reviewer clicks Reject
- **THEN** a ReviewDecision with action=REJECT is saved

#### Scenario: Console records review history
- **WHEN** multiple reviews have been performed
- **THEN** the console displays a scrollable history of past decisions

#### Scenario: Console does not auto-send
- **WHEN** any action is taken (Approve, Edit, Escalate, Reject)
- **THEN** no network call, API request, or send operation is performed
- **AND** the only side effect is a local JSONL append

### Requirement: No-Evidence / High-Risk Visibility
The console SHALL ensure that no-evidence fallback and high-risk tickets are clearly visible to the reviewer.

#### Scenario: No-evidence fallback is labeled
- **WHEN** a draft was generated with empty evidence
- **THEN** the console shows "No evidence found" or equivalent label
- **AND** the fallback message is displayed

#### Scenario: High-risk badge is shown
- **WHEN** must_human_review is True on the DraftReply
- **THEN** the console shows a high-risk badge or warning
- **AND** the risk assessment flags are displayed

## Test Strategy

### Unit Tests

**test_review_schemas.py:**
- ReviewAction has 4 values and is a string enum
- ReviewDecision valid construction with all fields
- ReviewDecision default values for optional fields
- ReviewDecision JSON serialization roundtrip
- ReviewDecision rejects invalid action value

**test_review_store.py:**
- Save and load single decision
- Save and load multiple decisions
- Load from empty/non-existent file returns empty list
- Roundtrip data integrity for all fields
- Multiple saves are append-only (no data loss)

### Integration Tests

**test_review_console.py:**
- ReviewStore with ReviewDecision roundtrip using temp file
- Console module imports cleanly

### What NOT to Test

- Streamlit UI interactions (widget clicks, page navigation): Streamlit is a UX layer; these are covered by manual smoke testing
- Real customer service API integration: out of scope
- Authentication or authorization: out of scope
- Draft generation correctness: already covered by Stage 1C tests
- Pipeline correctness: already covered by existing unit + integration tests
