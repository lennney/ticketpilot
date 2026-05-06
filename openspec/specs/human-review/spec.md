# human-review Specification

## Purpose
TBD - created by archiving change add-human-review-console. Update Purpose after archive.
## Requirements
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

### Requirement: Drafts Are Reviewable Drafts Only
The system SHALL present all generated drafts as reviewable drafts in the human review console, never as final customer replies.

#### Scenario: Draft displayed for review
- **WHEN** a DraftReply is generated
- **THEN** it is displayed in the human review console for review

#### Scenario: No auto-dispatch
- **WHEN** any draft is generated
- **THEN** there is no code path that sends it to a customer

### Requirement: Existing Review Actions Unchanged
The system SHALL preserve the four existing review actions: Approve, Edit, Escalate, Reject.

#### Scenario: Approve works
- **WHEN** reviewer clicks Approve
- **THEN** ReviewDecision with action=APPROVE is saved

#### Scenario: Edit works
- **WHEN** reviewer edits the draft and clicks Edit
- **THEN** ReviewDecision with action=EDIT and edited_text is saved

#### Scenario: Escalate works
- **WHEN** reviewer clicks Escalate
- **THEN** ReviewDecision with action=ESCALATE is saved

#### Scenario: Reject works
- **WHEN** reviewer clicks Reject
- **THEN** ReviewDecision with action=REJECT is saved

### Requirement: Guard Results Visible to Reviewer
The system SHALL display GuardResult information in the review console before the reviewer makes a decision.

#### Scenario: Guard pass/fail displayed
- **WHEN** a draft with guard results is shown
- **THEN** the review console shows guard_passed status

#### Scenario: Guard details displayed
- **WHEN** guard has failures
- **THEN** the review console shows which checks failed and why

#### Scenario: Evidence sufficiency displayed
- **WHEN** a draft is shown
- **THEN** the review console shows evidence_sufficiency status

### Requirement: Risk Flags and Guard Failures Visible
The system SHALL display risk assessment and guard failure details in the review console.

#### Scenario: Risk flags displayed
- **WHEN** a draft is shown for review
- **THEN** the review console shows risk flags and severity

#### Scenario: Escalation reason displayed
- **WHEN** must_human_review is True
- **THEN** the review console shows escalation_reason

#### Scenario: Provider identity displayed
- **WHEN** a draft is shown
- **THEN** the review console shows which provider generated it

### Requirement: No Automatic Customer Reply
The system SHALL NOT contain code paths that send approved drafts to customers.

#### Scenario: ReviewDecision is terminal output
- **WHEN** a review action is taken
- **THEN** the output is a ReviewDecision JSONL record, not a customer-facing dispatch

#### Scenario: No send channel in review module
- **WHEN** the review module is inspected
- **THEN** no API calls, message queues, or webhooks for sending replies exist

### Requirement: ReviewDecision Schema Extension
The system SHALL extend ReviewDecision with guard_results, provider_id, and escalation_reason fields.

#### Scenario: ReviewDecision includes guard_results
- **WHEN** a ReviewDecision is created for an LLM-generated draft
- **THEN** it includes guard_results from the draft

#### Scenario: ReviewDecision includes provider_id
- **WHEN** a ReviewDecision is created
- **THEN** it includes provider_id from the draft

#### Scenario: ReviewDecision includes escalation_reason
- **WHEN** a ReviewDecision is created for a draft with must_human_review=True
- **THEN** it includes escalation_reason

#### Scenario: Backward compatible
- **WHEN** ReviewDecision is created with minimal fields (no guard_results, provider_id, escalation_reason)
- **THEN** it still validates successfully

### Requirement: Complete Audit Context
The system SHALL record complete context in each ReviewDecision for audit purposes.

#### Scenario: ReviewDecision has full context
- **WHEN** a ReviewDecision is saved
- **THEN** it includes ticket_text, draft_text, citations_summary, evidence_used_count, risk_flags, guard_results, provider_id, reviewer action, and timestamp

### Requirement: High-Risk Routing
The system SHALL route drafts with must_human_review=True to human review. No bypass is permitted.

#### Scenario: must_human_review routes to review
- **WHEN** DraftReply.must_human_review is True
- **THEN** the pipeline sets status to require human review

#### Scenario: No bypass mechanism
- **WHEN** must_human_review is True
- **THEN** no configuration flag or code path can bypass human review

