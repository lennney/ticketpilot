## Context

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot. The existing pipeline processes a raw ticket through intake, classification, risk assessment, evidence retrieval, and optional draft generation — producing a `DraftedTicketResult` with a `TicketOutput` and `DraftReply`.

**Current state**: Draft generation is complete and archived. The system can generate evidence-grounded draft replies with citations, confidence scores, and guard flags. But there is no interface for human reviewers to act on these drafts.

**Constraints**:
- MUST NOT modify `src/ticketpilot/pipeline.py`, `src/ticketpilot/schema/ticket.py`, or `src/ticketpilot/schema/evidence.py`
- MUST NOT modify retrieval, risk, intake, classification, drafting core logic
- MUST NOT add real LLM provider, LangGraph, Langfuse, Ragas
- MUST NOT auto-send drafts
- MUST keep Streamlit as the only frontend technology for MVP

## Goals / Non-Goals

**Goals:**
- `ReviewAction` enum: `APPROVED`, `EDITED`, `ESCALATED`, `REJECTED`
- `ReviewDecision` schema with full audit trail fields
- JSONL-based review record persistence
- Streamlit review console MVP with:
  - Ticket input / sample selection
  - Full ticket processing display (text, intent, risk, evidence, draft)
  - Action panel (Approve, Edit, Escalate, Reject)
  - Review history log
- Wire `run_pipeline_with_draft()` into the review flow
- Unit tests for schemas and persistence
- Integration tests for the full review flow

**Non-Goals:**
- React / Next.js frontend
- Authentication or user management
- Production deployment or Docker
- Real customer service system API integration
- Real LLM provider
- LangGraph, Langfuse, Ragas observability
- Modifying retrieval, risk, drafting, intake, classification, or pipeline code
- Auto-send or one-click send
- Bulk operations
- Complex search/filter on review history

## Architecture

```
┌──────────────────────────────────────────────────────┐
│               Streamlit Review Console               │
│                                                      │
│  ┌─────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Ticket  │→ │ Process +    │→ │ Review Action   │  │
│  │ Input   │  │ Draft Review │  │ Panel           │  │
│  └─────────┘  └──────────────┘  └────────┬───────┘  │
│                                          │          │
│                                          v          │
│  ┌────────────────────────────────────────────────┐ │
│  │          Review History Log                    │ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
           │
           v
┌──────────────────────────┐
│     JSONL Store          │
│  (local file storage)    │
│  reviews.jsonl           │
└──────────────────────────┘
```

### Screen Layout (Ticket Review View)

```
┌─────────────────────────────────────────────────────┐
│ Header: Ticket #{id} — Intent — Severity            │
├────────────────────────┬────────────────────────────┤
│ Left Panel (60%)       │ Right Panel (40%)          │
│                        │                            │
│ [TICKET INFO]          │ [RISK FLAGS]               │
│ Original text          │ • must_human_review: True   │
│ Normalized text        │ • LEGAL_RISK               │
│ Customer ID            │ • COMPENSATION_RISK        │
│ Submitted at           │                            │
│                        │ [EVIDENCE]                  │
│ [DRAFT REPLY]          │ FAQ (score 0.85):          │
│ 您好，关于您反馈的     │   "退货需要在7天内申请..." │
│ refund问题，根据相关   │ Policy (score 0.72):       │
│ 资料[1]...             │   "根据消费者权益法..."    │
│                        │                            │
│ ┌─────────────────────┐│ [CITATIONS]                 │
│ │ Action buttons:     ││ • [1] → chunk_id           │
│ │ [Approve] [Escalate]││ • [2] → chunk_id           │
│ │ [Reject]            ││                            │
│ │ [Edit ▼]            ││ [UNSUPPORTED CLAIMS]       │
│ │ (expands text area) ││ (if any)                   │
│ └─────────────────────┘│                            │
└────────────────────────┴────────────────────────────┘
```

## New Schemas

### ReviewAction Enum

```python
class ReviewAction(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    ESCALATE = "escalate"
    REJECT = "reject"
```

### ReviewDecision Schema

Audit-oriented record of a human review action. Every field captures a snapshot of the state at review time, making the record self-contained for later analysis.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `review_id` | `str` | required | UUID, unique identifier for this review record |
| `ticket_id` | `str` | required | Links to the processed ticket |
| `ticket_text` | `str` | required | Original ticket text (self-contained audit) |
| `action` | `ReviewAction` | required | The reviewer's action |
| `edited_text` | `str | None` | `None` | Edited draft text (populated for EDIT action) |
| `decision_reason` | `str` | `""` | Business reason for the decision |
| `original_draft_text` | `str` | required | The draft text before any edits |
| `confidence` | `float` | `0.0` | Confidence score from the original draft |
| `had_unsupported_claims` | `bool` | `False` | Whether the draft had unsupported claims |
| `was_high_risk` | `bool` | `False` | Whether the ticket was high risk |
| `intent` | `str` | `""` | Intent classification label |
| `risk_flags` | `list[str]` | `[]` | Risk flags from assessment |
| `citations_summary` | `list[dict]` | `[]` | Brief citation summary for audit |
| `evidence_used_count` | `int` | `0` | Number of evidence items used in the draft |
| `reviewed_at` | `datetime` | `utcnow()` | When the review was performed |

### Reviewer Identity

For MVP, the console accepts a simple reviewer label (text input or name field). No authentication, no login. The `reviewer_id` or `reviewer_label` is recorded with each decision but validation is minimal. This keeps Batch 1 focused on the data contract.

A future change should add proper reviewer identity (login, role, permissions).

### ReviewStore

```python
class ReviewStore:
    """JSONL-based persistence for review decisions."""

    def __init__(self, path: str = "reviews.jsonl"):
        ...

    def save(self, decision: ReviewDecision) -> None:
        """Append a review decision to the JSONL file."""

    def load_all(self) -> list[ReviewDecision]:
        """Load all review decisions from the JSONL file."""

    def count(self) -> int:
        """Return the number of stored decisions."""
```

### Streamlit State Flow

```
User input / sample ticket
        ↓
run_pipeline_with_draft(raw_ticket)
        ↓
DraftedTicketResult displayed
        ↓
Reviewer views ticket, evidence, draft, citations
        ↓
Reviewer takes action:
  APPROVE → record decision, no text change
  EDIT    → show text editor, save edited version
  ESCALATE→ record with escalation notes
  REJECT  → record with rejection reason
        ↓
ReviewDecision saved to JSONL
```

## Safety Constraints

1. The console MUST NOT auto-send or expose any "Send" action. All drafts require human approval before any hypothetical downstream use.
2. The console MUST display `must_human_review` status prominently. High-risk and unsupported-claim drafts must be visually distinguishable from standard drafts.
3. The console MUST display unsupported claims when present. A reviewer should not need to manually compare draft text to citations.
4. The console MUST display all evidence candidates and their scores alongside citations, so the reviewer can assess evidence quality.
5. The `Approve` action does not send the draft anywhere. It only records the decision. Future integration with a send mechanism is explicitly deferred.
6. The `Edit` action preserves the original draft alongside the edited version in the `ReviewDecision`. No data is lost.
7. The console operates on the `run_pipeline_with_draft()` entrypoint only. It does not bypass or modify the pipeline.
8. Review records are append-only JSONL. No in-place edits. This ensures a basic audit trail.

## File Layout

```
src/ticketpilot/
  review/
    __init__.py              # Exports: ReviewAction, ReviewDecision, ReviewStore
    schemas.py               # ReviewAction, ReviewDecision
    store.py                 # ReviewStore (JSONL persistence)
    console.py               # Streamlit review console app
tests/
  unit/
    test_review_schemas.py   # ReviewDecision schema validation
    test_review_store.py     # ReviewStore read/write
  integration/
    test_review_console.py   # Full review flow integration
```

### Dependency Graph

```
schemas.py  (depends on nothing in the project — standalone Pydantic model)
     ^
     |
  store.py  (depends on schemas.py)
     ^
     |
 console.py (depends on store.py + drafting.pipeline + ticket schema)
```

## Risks / Trade-offs

[Risk] JSONL persistence is not suitable for multi-user or production use.
→ Acceptable for MVP. The store interface (`ReviewStore`) can be replaced with a database-backed implementation without changing the console or schemas.

[Risk] Streamlit is not a production-grade review UI.
→ Acceptable for MVP and demo purposes. The Streamlit app demonstrates the workflow and data model. A future React/Next.js UI would replace it while reusing the same schemas and store.

[Risk] No authentication means anyone who can access the Streamlit URL can review tickets.
→ Acceptable for local MVP. All sample data is synthetic/seed data. No real customer data is used.

[Risk] The review console adds no new tests for draft generation itself.
→ Correct by design. The console is a UI layer over existing functions. Draft generation correctness is already covered by unit + integration tests from Stage 1C.

## Open Questions

- Should `EScalate` include a target (e.g., "escalate to legal team") or remain a free-text field? MVP: free-text only.
- Should the sample ticket selector use hardcoded examples or read from seed data? MVP: hardcoded examples that match the seed data tickets.
- Should the review console be launched separately (`streamlit run`) or via a CLI entrypoint? MVP: `streamlit run` directly.
