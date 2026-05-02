# Human Review Console MVP

## Why

The system can now generate evidence-grounded draft replies, but has no interface for human reviewers to act on them. Without a review console, the draft generation workflow produces output that cannot be approved, edited, escalated, or rejected — breaking the "human-in-the-loop" design that is the core safety guarantee of the system.

**Target gap**: Stage 1C produces `DraftReply` with citations, confidence, and guard flags. But there is no UI to:
- View a ticket with its full processing context
- Review the generated draft alongside retrieved evidence
- Approve, edit, escalate, or reject a draft
- Record review decisions for audit

## What Changes

1. Add `ReviewDecision` schema with fields: `ticket_id`, `action` (Approve/Edit/Escalate/Reject), `edited_text`, `reviewer_notes`, `reviewed_at`, `original_draft_text`, `had_unsupported_claims`, `was_high_risk`
2. Add Streamlit-based review console MVP with screens for:
   - Ticket selection (sample tickets or raw input)
   - Ticket detail + evidence view
   - Draft review with citation display
   - Action panel (Approve / Edit / Escalate / Reject)
   - Review history log
3. Persist review records to local JSONL storage
4. Wire `run_pipeline_with_draft()` into the review flow
5. Display risk flags, evidence candidates, citations, and unsupported claims alongside the draft

## Out of Scope

- React / Next.js frontend
- Authentication / user management
- Production deployment
- Real customer service system integration
- Real LLM provider (FakeDraftProvider remains the only provider)
- LangGraph, Langfuse, Ragas
- Modifying retrieval, risk, drafting, intake, classification, or pipeline core logic
- Auto-send or one-click send
