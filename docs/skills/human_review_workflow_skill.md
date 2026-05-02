# Human Review Workflow Skill

## Purpose

Design and implement a human-in-the-loop review workflow for AI-generated draft replies, with structured review actions (Approve, Edit, Escalate, Reject), self-contained audit trail persistence, clear display of risk and evidence information, and an explicit "no auto-send" safety constraint.

## When to Use

- Adding human review to any AI-assisted content generation system
- Designing an audit trail for review decisions
- Building a review console or interface for human reviewers
- Implementing safety constraints that prevent automated action without human approval
- Integrating review workflow with an existing pipeline output

## Required Inputs

- Pipeline or generation output schema (fields to display to reviewer)
- Draft or content schema (what is being reviewed)
- Risk assessment schema (risk flags, severity, must_human_review)
- Understanding of the review actions needed (minimum: approve, reject; recommended: edit, escalate)

## Allowed Scope

- Defining review action types (Approve, Edit, Escalate, Reject)
- Creating a review decision schema with self-contained audit snapshot (ticket state, draft state, reviewer action, timestamp)
- Implementing an append-only persistence store (JSONL or database)
- Building a review console UI (Streamlit, web, or CLI) for human reviewers
- Implementing pure helper functions for determining review trigger reasons and building review decisions
- Documenting the no-auto-send constraint

## Forbidden Scope

- Do NOT add auto-send or reply dispatch functionality (human review records decisions only)
- Do NOT skip the audit trail (every review action must create an immutable record)
- Do NOT bypass must_human_review for high-risk, no-evidence, or unsupported-claim outputs
- Do NOT implement authentication or multi-user workflow in an MVP phase (label-only reviewer identity is acceptable for MVP)
- Do NOT claim production readiness for a Streamlit/JSONL-based review system
- Do NOT add integration tests requiring browser automation in an MVP phase

## Step-by-Step Procedure

1. **Define review actions**
   - Create a ReviewAction enum with at minimum: APPROVE, EDIT, ESCALATE, REJECT
   - Each action should have clear meaning and behavior:
     - APPROVE: Accept content as-is
     - EDIT: Modify content, preserve both original and edited versions
     - ESCALATE: Flag for senior or secondary review, capture escalation reason
     - REJECT: Reject content, capture rejection reason

2. **Define the review decision schema**
   - Create a ReviewDecision Pydantic model with:
     - Identity: review_id, ticket_id
     - Reviewer: reviewer_label (free-text for MVP)
     - Ticket state snapshot: ticket_text, intent, risk_flags
     - Draft state snapshot: original_draft_text, confidence, had_unsupported_claims, was_high_risk
     - Evidence state: citations_summary, evidence_used_count
     - Review action: action (ReviewAction), edited_text, decision_reason
     - Trigger reasons: list of why review was triggered (high_risk, no_evidence, unsupported_claims, generation_error)
     - Timestamp: reviewed_at

3. **Implement review trigger determination**
   - Create a pure function (e.g., `determine_trigger_reasons(result) -> list[str]`) that inspects:
     - Risk assessment: must_human_review, severity == HIGH -> "high_risk"
     - Draft fallback: fallback_reason == "no_evidence" -> "no_evidence"
     - Draft: unsupported_claims non-empty -> "unsupported_claims"
     - Draft fallback: fallback_reason == "generation_error" -> "generation_error"
   - This function must be testable without a UI framework

4. **Implement review decision builder**
   - Create a pure function (e.g., `build_review_decision(result, action, ...) -> ReviewDecision`) that:
     - Extracts citations summary (chunk_id + doc_type pairs)
     - Extracts risk flags (enum values to strings)
     - Extracts confidence, intent, evidence count from draft and pipeline state
     - Returns a fully populated ReviewDecision

5. **Implement append-only persistence**
   - Create a ReviewStore with: save(decision), load_all(), count()
   - Use append-only JSONL for MVP (each line is one JSON-serialized ReviewDecision)
   - Guarantees: append-only (lines never modified/deleted), self-contained (no cross-references), inspectable (standard tools: head, tail, jq)

6. **Build the review console UI (MVP)**
   - Display ticket info (ID, normalized text, intent, risk severity/ flags, must_human_review indicator)
   - Display evidence candidates (expandable, showing source table, score, content excerpt)
   - Display draft reply (read-only text, fallback warnings, unsupported claims section, citations list)
   - Implement action buttons with appropriate input dialogs (EDIT: text area, ESCALATE/REJECT: reason text)
   - Show review history with total record count
   - Display explicit "no auto-send" disclaimer

7. **Verify no auto-send**
   - Audit all action handlers: each should only persist a ReviewDecision to the store
   - No network calls, no API requests, no message dispatch
   - Integration tests should explicitly assert no side effects beyond store append

8. **Document deferred items**
   - Authentication / multi-user workflow
   - Production database backend (replace JSONL)
   - Shared review queue
   - Deployment (Docker, cloud)
   - Trace dashboard / observability
   - Browser automation tests

## Acceptance Checklist

- [ ] ReviewAction enum defined with APPROVE, EDIT, ESCALATE, REJECT
- [ ] ReviewDecision schema with audit trail fields (15+)
- [ ] ReviewStore with save/load_all/count using append-only JSONL
- [ ] determine_trigger_reasons() as pure testable function
- [ ] build_review_decision() as pure data-transformation function
- [ ] Console UI displays ticket info, risk, evidence, and draft
- [ ] All four actions work and persist decisions
- [ ] Explicit "no auto-send" disclaimer visible
- [ ] Integration tests verify persistence for all action types
- [ ] Integration tests verify no auto-send (only JSONL append)
- [ ] No authentication in MVP (reviewer_label is free-text)
- [ ] No auto-send capability exists anywhere in the code

## Common Failure Modes

- **Accidental auto-send**: A "send" or "dispatch" button, or an API call triggered on approve. Audit all action handlers. Integration test for no auto-send.
- **Missing audit trail fields**: If the ReviewDecision doesn't capture the full state at review time, historical records become uninterpretable when the pipeline changes. Include all relevant state as a snapshot.
- **EDIT action loses original draft**: If the reviewer edits, both the original and edited versions must be preserved. The edited_text field should be separate from original_draft_text.
- **Business logic mixed with UI framework**: If determine_trigger_reasons() is inside a Streamlit callback, it cannot be unit tested. Keep business logic in pure functions separate from the UI.
- **No way to know why review was triggered**: If the reviewer sees a draft but doesn't know why the system flagged it (high risk? no evidence? unsupported claims?), they cannot make an informed decision. Populate review_trigger_reasons.
- **Shared mutable state across reviewers**: JSONL files have no locking. In single-user MVP this is acceptable. In multi-user, a database-backed store with proper concurrency control is required.
- **Reviewer identify is free-text**: This is acceptable for MVP but must be documented as deferred. Do not add auth in MVP unless explicitly scoped.

## Reusable Claude Code Prompt Template

```
I need to design a human review workflow for AI-generated content. Walk through:

1. **Review actions** — Define an enum with: APPROVE, EDIT, ESCALATE, REJECT
   - APPROVE: accept as-is, record decision
   - EDIT: modify content, preserve both original and edited
   - ESCALATE: flag for senior review, capture reason
   - REJECT: reject content, capture reason

2. **ReviewDecision schema** — Self-contained audit snapshot:
   - Identity: review_id, ticket_id
   - Reviewer: label (free-text for MVP)
   - Ticket state: text, intent, risk_flags
   - Draft state: original_text, confidence, had_unsupported_claims, was_high_risk
   - Evidence state: citations_summary, evidence_used_count
   - Review action: action, edited_text, decision_reason
   - Trigger reasons: [high_risk, no_evidence, unsupported_claims, generation_error]
   - Timestamp: reviewed_at

3. **Persistence** — Append-only store (JSONL for MVP):
   - save(decision), load_all(), count()
   - Append-only: lines never modified/deleted
   - Self-contained: each line is complete, no cross-references

4. **Console UI** — Display:
   - Ticket info, risk assessment, evidence candidates, draft reply
   - Action buttons with appropriate input dialogs
   - Review history
   - Explicit "no auto-send" disclaimer

5. **No auto-send enforcement**:
   - All actions only persist ReviewDecision
   - No network calls, no API requests, no message dispatch
   - Integration test: assert no side effects beyond store append

Critical constraints:
- No auto-send
- No authentication in MVP
- Business logic as testable pure functions, separate from UI
- Every action creates an immutable audit record
```

## TicketPilot Example

TicketPilot's human review console (Stage 1D) implements the complete workflow:

**ReviewAction enum**: APPROVE ("批准"), EDIT ("编辑"), ESCALATE ("升级"), REJECT ("拒绝").

**ReviewDecision** (15+ fields): Includes review_id, ticket_id, ticket_text, action, edited_text, decision_reason, original_draft_text, confidence, had_unsupported_claims, was_high_risk, intent, risk_flags, citations_summary, evidence_used_count, review_trigger_reasons, reviewer_label, reviewed_at.

**Append-only ReviewStore**: JSONL persistence with save/load_all/count. Each line is a complete, self-contained ReviewDecision. Never modified after writing.

**Pure helper functions**:
- `determine_trigger_reasons()`: Inspects risk flags, fallback reason, and unsupported claims to determine why review was triggered. 40 unit tests.
- `build_review_decision()`: Converts DraftedTicketResult + reviewer action into a fully populated ReviewDecision. Tested for all 4 action types.

**Streamlit console MVP**: Split-column layout — left shows ticket info, risk assessment, evidence candidates; right shows draft reply, citations, action buttons. Explicit "审核控制台 — 不自动发送回复" disclaimer.

**No auto-send**: Verified by 9 integration tests that assert no side effects beyond JSONL append. No network, API, or message dispatch code exists.

**Deferred**: Authentication, production database, shared review queue, deployment, browser automation tests.
