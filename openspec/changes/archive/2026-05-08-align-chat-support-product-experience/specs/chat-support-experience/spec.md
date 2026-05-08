# Chat Support Experience Specification

## Purpose

Align TicketPilot's product experience toward a chat-style AI customer service copilot that resembles real e-commerce AI support (e.g., Taobao/JD). The chat demo surfaces existing backend capabilities (intent classification, risk assessment, evidence retrieval, draft generation, citation validation, claim guard, human review) through a user-facing interface. Guard taxonomy remains the safety foundation; chat demo is the product experience layer.

---

## ADDED Requirements

### Requirement: Chat Support Entry

The system SHALL accept a user message through a chat input field.

#### Scenario: User submits valid message
- **WHEN** the user types "我要退款，订单号12345" and clicks send
- **THEN** the message appears in chat history as a user message
- **AND** the pipeline processes the message

#### Scenario: User submits empty message
- **WHEN** the user sends an empty message
- **THEN** the system shows an error or ignores the input

#### Scenario: User submits whitespace-only message
- **WHEN** the user sends a message with only whitespace
- **THEN** the system shows an error or ignores the input

---

### Requirement: AI First Response Draft

The system SHALL generate an evidence-grounded AI draft reply and display it in the chat.

#### Scenario: Draft generated with citations
- **WHEN** evidence is retrieved and the LLM provider generates a draft
- **THEN** the draft appears in the chat as an AI message
- **AND** the draft contains inline citation markers like `[chunk_id]`

#### Scenario: No evidence generates safe fallback
- **WHEN** evidence retrieval returns no results
- **THEN** the fallback message includes "建议转人工处理"
- **AND** the draft does not make policy promises

#### Scenario: FakeLLMProvider is deterministic
- **WHEN** the FakeLLMProvider generates a draft
- **THEN** the generation is deterministic (same input produces same output)
- **AND** no network call is made to any external LLM API

---

### Requirement: Risk-Based Human Escalation

The system SHALL route to human review based on risk severity and guard result.

#### Scenario: HIGH severity always triggers human review
- **WHEN** a HIGH severity ticket is processed
- **THEN** `human_review_required` is set to `True`
- **AND** the AI draft is shown with a "人工审核" notice

#### Scenario: LOW severity + guard pass does not require review
- **WHEN** a LOW severity ticket has sufficient evidence and `guard_pass=True`
- **THEN** `human_review_required` is set to `False`
- **AND** the draft is shown as ready

#### Scenario: MEDIUM severity + guard fail triggers review
- **WHEN** a MEDIUM severity ticket has `guard_pass=False`
- **THEN** `human_review_required` is set to `True`
- **AND** `failure_reasons` are displayed

#### Scenario: No evidence triggers human review
- **WHEN** no evidence is retrieved for a ticket
- **THEN** `human_review_required` is set to `True`
- **AND** the system generates safe escalation language

---

### Requirement: Evidence Panel

The system SHALL display retrieved evidence grouped by type (FAQ / Policy / Case).

#### Scenario: Evidence displayed with metadata
- **WHEN** evidence candidates are retrieved
- **THEN** each evidence item shows: chunk_id, title, doc_type, score
- **AND** evidence is grouped by type (FAQ, Policy, Case)

#### Scenario: No evidence shows placeholder
- **WHEN** no evidence is retrieved
- **THEN** the evidence panel shows "暂无相关证据"

---

### Requirement: Human Review Handoff

The system SHALL allow human reviewers to review, approve, edit, escalate, or reject drafts.

#### Scenario: Human review button opens review console
- **WHEN** `human_review_required` is `True`
- **AND** the reviewer clicks "进行人工审核"
- **THEN** the review console opens with full context (user message, evidence, draft, guard result)

#### Scenario: Reviewer approves draft
- **WHEN** the reviewer clicks "Approve"
- **THEN** the decision is recorded with `action=approve`
- **AND** the chat session shows "已通过审核"

#### Scenario: Reviewer escalates draft
- **WHEN** the reviewer clicks "Escalate"
- **THEN** the decision is recorded with `action=escalate`
- **AND** the chat session shows "已升级处理"

#### Scenario: Reviewer rejects draft
- **WHEN** the reviewer clicks "Reject"
- **THEN** the decision is recorded with `action=reject`
- **AND** the chat session shows "已拒绝草稿"

#### Scenario: Reviewer edits draft
- **WHEN** the reviewer edits the draft text and clicks "Save"
- **THEN** the new draft text is saved
- **AND** the decision is recorded with `action=edit` and `new_draft_text`

---

### Requirement: No Auto-Send Boundary

The system SHALL NOT automatically send any draft reply to any recipient.

#### Scenario: Draft is display-only
- **WHEN** a draft is generated and `guard_pass=True`
- **THEN** the draft is displayed in the UI
- **AND** no message is sent to any user, channel, or API endpoint

#### Scenario: Approval is local-only
- **WHEN** a human reviewer approves a draft
- **THEN** the decision is recorded locally
- **AND** no message is sent to any recipient

#### Scenario: All actions are local
- **WHEN** any action is taken in the chat demo
- **THEN** all actions are local to the demo environment
- **AND** no external system is called

---

### Requirement: Synthetic Demo Data Boundary

The system SHALL use only synthetic data for demonstration purposes.

#### Scenario: Synthetic tickets used
- **WHEN** a user submits a message
- **THEN** the system processes it against 101 synthetic eval tickets
- **AND** evidence is retrieved from 106 synthetic knowledge records

#### Scenario: Evidence from synthetic knowledge base
- **WHEN** evidence is displayed in the chat
- **THEN** all evidence comes from the synthetic knowledge base
- **AND** no real customer names, orders, or personal data are used

#### Scenario: Review decisions are local
- **WHEN** the reviewer takes an action
- **THEN** the decision is stored locally in reviews.jsonl
- **AND** no real customer is notified

---

### Requirement: Chat State Machine

The system SHALL maintain a chat session state and transition correctly.

#### Scenario: Idle on startup
- **WHEN** the chat demo starts
- **AND** no message is sent
- **THEN** the session state is `IDLE`

#### Scenario: Processing on message submit
- **WHEN** the user submits a message from `IDLE` state
- **THEN** the session transitions to `PROCESSING`

#### Scenario: Draft ready when guard passes
- **WHEN** a draft is generated and `human_review_required=False`
- **THEN** the session transitions to `DRAFT_READY`

#### Scenario: Human review when required
- **WHEN** a draft is generated and `human_review_required=True`
- **THEN** the session transitions to `HUMAN_REVIEW`

#### Scenario: Reviewed after reviewer action
- **WHEN** the reviewer approves, edits, or escalates
- **THEN** the session transitions to `REVIEWED`

---

### Requirement: Guard Result Display

The system SHALL display guard validation results alongside the draft.

#### Scenario: Guard pass shown as green
- **WHEN** `guard_pass=True`
- **THEN** a green checkmark is shown
- **AND** "guard_passed" is indicated

#### Scenario: Guard fail shown with failure reasons
- **WHEN** `guard_pass=False`
- **THEN** a red X is shown
- **AND** `failure_reasons` are displayed as a list

#### Scenario: No positive signals in failure reasons
- **WHEN** `failure_reasons` is populated
- **THEN** `SAFE_ESCALATION_STATEMENT` and `MANUAL_REVIEW_ACKNOWLEDGEMENT` do NOT appear
- **AND** only actual failure types are listed

---

### Requirement: Citation Markers in Draft

The system SHALL display citation markers inline in the AI draft.

#### Scenario: Citations shown inline
- **WHEN** a draft references evidence chunks
- **THEN** citation markers like `[chunk_id]` are shown inline
- **AND** clicking a marker highlights the corresponding evidence

#### Scenario: Uncited substantive warning
- **WHEN** a draft has no citations and is substantive content
- **THEN** `has_uncited_claims` is shown as a warning
- **AND** `guard_pass=False` is indicated
