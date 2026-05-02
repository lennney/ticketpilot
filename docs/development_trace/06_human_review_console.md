# Stage 1D: Human Review Console

## Stage Goal

Build the human review interface for TicketPilot: a Streamlit-based console where human reviewers can paste raw tickets, view the full pipeline output (intent, risk, evidence, draft), and record review decisions (Approve, Edit, Escalate, Reject) with a complete audit trail persisted to append-only JSONL.

## Business Problem Addressed

TicketPilot generates draft replies, but drafts cannot be sent without human approval — especially for high-risk tickets, tickets with unsupported claims, or tickets lacking sufficient evidence. Before this stage:

- There was no interface for human reviewers to interact with pipeline outputs
- There was no way to record review decisions or build an audit trail
- Reviewers had to manually copy pipeline output and paste it elsewhere

The review console solves these problems by providing:

- A single-page application for the complete review workflow
- Self-contained audit records for every review decision
- Clear display of risk flags, evidence, and unsupported claims alongside the draft
- A deliberate "no auto-send" constraint — the console records decisions only

## Key Design Decisions

### 1. Streamlit for MVP (not production frontend)
- **Decision**: Use Streamlit single-page application, not React/Next.js or a full web framework.
- **Rationale**: Zero frontend build step, Python-only, fast iteration. Streamlit is appropriate for local demo and manual testing, not for multi-user production deployment.
- **Alternatives**: React/Next.js (full production UI, overkill for MVP), Tkinter/PyQt (desktop-only, no web access).

### 2. Append-only JSONL persistence (not database)
- **Decision**: `ReviewStore` writes to append-only JSONL files. Each review decision is one JSON line.
- **Rationale**: Zero infrastructure needed (no database setup). Full audit trail preserved (append-only means no data loss). Easy to inspect with standard tools (`head`, `tail`, `jq`).
- **Production path**: The `ReviewStore` interface can be replaced with a database-backed implementation without changing the console or schemas.

### 3. Four review actions (not binary approve/reject)
- **Decision**: `ReviewAction` enum with four values: APPROVE, EDIT, ESCALATE, REJECT.
- **Rationale**: Covers all human review outcomes. EDIT preserves the original draft alongside the edited version. ESCALATE captures escalation reason. No action sends the draft anywhere.

### 4. ReviewDecision captures self-contained audit snapshot
- **Decision**: `ReviewDecision` includes ticket_id, ticket_text, original_draft_text, confidence, had_unsupported_claims, was_high_risk, intent, risk_flags, citations_summary, evidence_used_count, and reviewed_at.
- **Rationale**: Every field captures a snapshot of the state at review time, making the record self-contained for later analysis. If the pipeline changes later, historical review records still contain the full context.

### 5. `determine_trigger_reasons()` as a pure function
- **Decision**: The logic for determining why human review was triggered (high_risk, no_evidence, unsupported_claims, generation_error) is a pure, testable function separate from Streamlit's widget lifecycle.
- **Rationale**: Keeps business logic testable without Streamlit infrastructure. The function receives a `DraftedTicketResult` and returns `list[str]` — simple, stateless, side-effect-free.

### 6. Explicit "no auto-send" safety constraint
- **Decision**: The console has no send functionality. All four actions only persist a `ReviewDecision` to local JSONL. No network call, no API request, no message dispatch.
- **Rationale**: Deliberate constraint to prevent accidental auto-send. The console is a decision-recording interface, not a reply-sending interface.

## Implementation Scope

### Batch 1: Review Schema and Store Foundation
- Created `src/ticketpilot/review/schemas.py` with `ReviewAction` enum and `ReviewDecision` Pydantic model (15+ audit fields)
- Created `src/ticketpilot/review/store.py` with `ReviewStore` (save, load_all, count) using append-only JSONL persistence
- Created `src/ticketpilot/review/__init__.py` with clean exports
- Added unit tests: 22 tests (11 schema + 11 store)

### Batch 2: Streamlit Console MVP
- Created `src/ticketpilot/review/console.py` with the full Streamlit review application
- Console features: RawTicket JSON input, pipeline processing display, risk/evidence/draft review, action buttons (Approve/Edit/Escalate/Reject), review history log
- Added `determine_trigger_reasons()` and `build_review_decision()` as pure, testable helper functions
- Added 40 unit tests for console helper functions

### Batch 3: Integration Tests + Documentation + Quality Gate
- Added `tests/integration/test_review_console.py` with 9 integration tests covering all four action types, audit field preservation, and no-auto-send verification
- Updated `docs/technical_decisions.md` with Human Review Console Architecture section
- Updated `docs/phase_status.md` with Stage 1D (ACCEPTED)
- Verified Streamlit 1.56.0 is importable (no `pyproject.toml` change needed)

## Forbidden Scope

- No modifications to `pipeline.py`, drafting, retrieval, risk, intake, classification, or database code
- No React/Next.js frontend
- No authentication or user management (reviewer label is free-text)
- No production deployment or Docker
- No real customer service system API integration
- No auto-send or one-click reply dispatch
- No bulk operations
- No complex search/filter on review history
- No LangGraph, Langfuse, Ragas observability
- No integration tests requiring browser automation

## Tests and Quality Gate Result

| Metric | Value |
|--------|-------|
| Unit tests (Batch 1) | 22 new (schema + store) |
| Unit tests (Batch 2) | 40 new (console helpers) |
| Integration tests (Batch 3) | 9 new (review flow) |
| Total unit tests | 325 passed (285 prior + 40 new) |
| Total integration tests | 74 passed (65 prior + 9 new) |
| 0 skipped integration tests | Confirmed |
| Ruff | All checks passed |
| OpenSpec validate --all | 11/11 passed |
| Quality gate | PASSED |
| No existing tests modified | Confirmed |
| No pipeline, drafting, retrieval, risk, intake, classification, or DB code modified | Confirmed |
| No auto-send capability added | Confirmed |

## Major Risks

| Risk | Handling |
|------|----------|
| **Streamlit is not production-grade** | Acceptable for MVP and demo purposes. A future React/Next.js UI would replace it while reusing the same schemas and store. |
| **JSONL persistence is not suitable for multi-user or production use** | Acceptable for MVP. The `ReviewStore` interface can be replaced with a database-backed implementation. |
| **No authentication means anyone who can access the Streamlit URL can review tickets** | Acceptable for local MVP. All sample data is synthetic seed data. |
| **Reviewer identity is free-text label, no auth** | MVP-only. A future change should add proper reviewer identity (login, role, permissions). |
| **No integration tests for the console UI** | 9 integration tests cover the data flow and persistence. Browser automation (Selenium/Playwright) is deferred. |

## Deferred Items

- Authentication / multi-user workflow with login, roles, and permissions
- Production database backend (replace JSONL with shared DB)
- Shared review queue across multiple reviewers
- Deployment (Docker, cloud infrastructure)
- Trace dashboard / observability integration (Langfuse, Ragas)
- Real-time ticket feed (polling or WebSocket)
- Browser automation integration tests (Selenium/Playwright)
- Auto-send / reply dispatch integration with customer service platforms

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| `38ff0b4` | 2026-05-02 | spec: add human review console OpenSpec change |
| `6e33746` | 2026-05-02 | feat: add review schema and JSONL store foundation |
| `86a162c` | 2026-05-02 | feat: add reviewer_label to ReviewDecision schema |
| `d2f08e2` | 2026-05-02 | feat: add review_trigger_reasons to ReviewDecision schema |
| `7014fa3` | 2026-05-02 | feat: add Streamlit human review console MVP |
| `ac1ba23` | 2026-05-02 | test: finalize human review console coverage |
| `def4afa` | 2026-05-02 | chore: archive human review console OpenSpec change |

## Reusable Patterns

1. **ReviewAction enum + ReviewDecision audit model** — A 4-action review system (Approve/Edit/Escalate/Reject) with self-contained audit snapshot is reusable for any human-in-the-loop AI system. The pattern ensures every decision is traceable and reviewable.
2. **Append-only JSONL ReviewStore** — Simple, zero-infrastructure persistence with built-in audit trail. The interface pattern (save/load_all/count) is easily replaced with a database backend without changing callers.
3. **Pure helper functions separated from Streamlit lifecycle** — `determine_trigger_reasons()` and `build_review_decision()` testable without Streamlit infrastructure. This pattern is reusable for any Streamlit app that contains business logic.
4. **No-auto-send as architectural constraint** — The deliberate absence of send functionality is documented and tested. Integration tests explicitly assert no side effects beyond JSONL append. Reusable for any system where safety requires explicit human approval before action.
5. **Batch implementation pattern** — Schema + store (Batch 1) -> UI (Batch 2) -> Integration tests + docs + quality gate (Batch 3). Each batch is independently testable and mergable.
