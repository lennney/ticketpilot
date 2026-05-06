# human-review Specification

## ADDED Requirements

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
