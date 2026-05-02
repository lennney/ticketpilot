## Phase 1: Review Schemas + Store

- [ ] 1.1 Create `src/ticketpilot/review/__init__.py` with package exports
- [ ] 1.2 Create `src/ticketpilot/review/schemas.py` with:
  - `ReviewAction` enum: APPROVE, EDIT, ESCALATE, REJECT
  - `ReviewDecision` Pydantic model with all audit trail fields:
    - review_id, ticket_id, ticket_text, action, edited_text, decision_reason
    - original_draft_text, confidence, had_unsupported_claims, was_high_risk
    - intent, risk_flags, citations_summary, evidence_used_count, reviewed_at
- [ ] 1.3 Create `src/ticketpilot/review/store.py` with:
  - `ReviewStore` class using JSONL persistence
  - `save(decision)`, `load_all()`, `count()` methods
  - Thread-safe append
- [ ] 1.4 Write unit tests in `tests/unit/test_review_schemas.py`:
  - ReviewAction enum values
  - ReviewDecision valid construction
  - ReviewDecision defaults
- [ ] 1.5 Write unit tests in `tests/unit/test_review_store.py`:
  - Save and load a single decision
  - Save and load multiple decisions
  - Load from empty file
  - Roundtrip data integrity

## Phase 2: Streamlit Review Console

- [ ] 2.1 Create `src/ticketpilot/review/console.py` with Streamlit app:
  - Sidebar: sample ticket selector + raw text input
  - Main panel: ticket details, risk flags, evidence display, draft review
  - Action panel: Approve, Edit, Escalate, Reject buttons
  - Edit mode: expandable text editor pre-filled with draft
  - Review history: scrollable log of past decisions
- [ ] 2.2 Wire `run_pipeline_with_draft()` into the review flow:
  - On ticket selection/input, call the pipeline
  - Display all fields from `DraftedTicketResult`
  - Handle pipeline exceptions gracefully in the UI
- [ ] 2.3 Style the console:
  - Use Streamlit columns for ticket-info/draft-review layout
  - Highlight risk flags and unsupported claims
  - Use color-coded action buttons
- [ ] 2.4 Manual smoke test: run `streamlit run src/ticketpilot/review/console.py`
  - Verify ticket selection works
  - Verify pipeline runs and displays results
  - Verify each action button records a decision
  - Verify review history shows past decisions

## Phase 3: Integration Tests + Quality Gate

- [ ] 3.1 Create `tests/integration/test_review_console.py`:
  - Test that ReviewStore integrates with ReviewDecision roundtrip
  - Test that the console module loads without error
- [ ] 3.2 Update `docs/changelog.md` with human review console entry
- [ ] 3.3 Run full quality gate: `bash scripts/run_quality_gate.sh`
- [ ] 3.4 Update `docs/phase_status.md` with Stage 1D status
- [ ] 3.5 Final acceptance + archive

## Batch Plan Summary

- **Batch 1**: Phase 1 (schemas + store + unit tests). Creates `src/ticketpilot/review/` and `tests/unit/test_review_*.py`. Zero risk to existing code.
- **Batch 2**: Phase 2 (Streamlit console). Adds `console.py`. No modifications to existing modules.
- **Batch 3**: Phase 3 (integration tests + documentation + quality gate + archive).
