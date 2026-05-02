# Human Review Console

## Overview

The human review console is a **Streamlit single-page application MVP** where human reviewers can inspect pipeline outputs and record review decisions. It is not a production frontend — it has no authentication, no multi-user support, and no deployment configuration.

**Source module:** `src/ticketpilot/review/console.py`

## Streamlit MVP

### Architecture

```
┌──────────────────────────────────────────────────┐
│              Streamlit Review Console             │
│                                                    │
│  ┌─────────────┐     ┌──────────────────────────┐ │
│  │ Left Column  │     │     Right Column          │ │
│  │  - 工单信息   │     │  - 草稿回复 (read-only)    │ │
│  │  - 风险评估   │     │  - 引用列表                │ │
│  │  - 证据候选   │     │  - 审核操作按钮            │ │
│  │  - 缺失信息   │     │  - 编辑/升级/拒绝弹窗      │ │
│  └─────────────┘     └──────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────────┐
│  │  ReviewStore (append-only JSONL)                 │
│  └──────────────────────────────────────────────────┘
└──────────────────────────────────────────────────┘
```

### Framework Decision

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Streamlit (single-page) | Zero frontend build step, Python-only, fast iteration |
| Persistence | Append-only JSONL | Zero infrastructure, full audit trail, easy inspection |
| Deployment | Local-only | No Docker, no cloud, no CI/CD |

### Input

The console accepts a `RawTicket` in JSON format pasted into a text area. Clicking "处理工单" calls `run_pipeline_with_draft()` on the input and displays the full output.

### Display Fields

The console is split into two columns:

**Left column (工单信息):**
- Ticket ID
- Normalized text
- Intent classification with confidence
- Risk severity (color-coded: red=HIGH, orange=MEDIUM, green=LOW)
- Risk flags (comma-separated list)
- Must-human-review indicator (red/green badge)
- Evidence candidates (expandable, showing source table, score, content excerpt)
- Missing information list

**Right column (草稿回复):**
- Draft text (read-only text area, 200px height)
- Fallback warnings (no_evidence, generation_error) with colored alert boxes
- Unsupported claims section (expandable, shown when present)
- Citation list (numbered, showing chunk_id and doc_type)
- Review action buttons

## Approve / Edit / Escalate / Reject

### ReviewAction Enum

```python
class ReviewAction(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    ESCALATE = "escalate"
    REJECT = "reject"
```

### Action Behaviors

| Action | Button | Input Required | Effect |
|--------|--------|---------------|--------|
| **Approve** | "批准" | None | Accepts the draft as-is, records approval to JSONL |
| **Edit** | "编辑" | Edited text | Shows text area; stores both original and edited versions |
| **Escalate** | "升级" | Escalation reason | Captures reason for senior review |
| **Reject** | "拒绝" | Rejection reason | Captures reason for rejection |

Each action triggers `_save_and_display()`, which:
1. Calls `build_review_decision()` to construct a `ReviewDecision`
2. Persists it via `ReviewStore.save()`
3. Shows a success message with the `review_id`
4. Displays the total number of stored records

## ReviewDecision

**Source:** `src/ticketpilot/review/schemas.py`

The `ReviewDecision` captures a self-contained snapshot of the review-time state:

| Category | Fields |
|----------|--------|
| **Identity** | `review_id`, `ticket_id` |
| **Reviewer** | `reviewer_label` (free-text, no auth) |
| **Ticket state** | `ticket_text`, `intent`, `risk_flags` |
| **Draft state** | `original_draft_text`, `confidence`, `had_unsupported_claims`, `was_high_risk` |
| **Evidence state** | `citations_summary`, `evidence_used_count` |
| **Review action** | `action`, `edited_text`, `decision_reason` |
| **Trigger reasons** | `review_trigger_reasons` — "high_risk", "no_evidence", "unsupported_claims", "generation_error" |
| **Timestamp** | `reviewed_at` |

### Helper Functions

**`determine_trigger_reasons(result: DraftedTicketResult) -> list[str]`**

A pure, testable function that inspects the pipeline result to determine why human review was triggered. Checks:
- `risk.must_human_review` or `risk.severity == HIGH` -> "high_risk"
- `draft.fallback_reason == "no_evidence"` -> "no_evidence"
- `draft.unsupported_claims` non-empty -> "unsupported_claims"
- `draft.fallback_reason == "generation_error"` -> "generation_error"

**`build_review_decision(result, action, edited_text, decision_reason) -> ReviewDecision`**

A pure data-transformation function that converts a `DraftedTicketResult` + reviewer action into a fully populated `ReviewDecision`. Extracts:
- Citations summary (chunk_id + doc_type pairs)
- Risk flags (enum values -> strings)
- Confidence, intent, evidence count from the draft and pipeline state

## ReviewStore JSONL

**Source:** `src/ticketpilot/review/store.py`

### Persistence Model

- **Format**: Append-only JSONL (one JSON object per line)
- **Default path**: `reviews.jsonl` (in the current working directory)
- **Operations**: `save(decision)`, `load_all()`, `count()`

### Storage Guarantees

| Property | Guarantee |
|----------|-----------|
| Append-only | Lines are never modified or deleted after writing |
| Audit trail | Every review decision is permanently recorded |
| Inspectable | Readable with standard tools: `head`, `tail`, `jq` |
| Survives restarts | Persisted to filesystem, not in-memory |
| Self-contained | Each line is a complete `ReviewDecision` — no cross-references needed |

### Production Path

The `ReviewStore` interface (save/load_all/count) can be replaced with a database-backed implementation without changing the console or schema. The JSONL implementation is suitable for local demo only.

## Append-Only Audit Trail

Every review action creates an immutable record. Key properties:

- **No deletes**: Records are never removed
- **No updates**: Records are never modified
- **Append only**: New records are added by appending lines to the JSONL file
- **Self-contained**: Each record contains a full snapshot of the review-time state, so historical records remain interpretable even if the pipeline changes

## No Auto-Send

**The console has no send functionality.** All four actions only persist a `ReviewDecision` to local JSONL. There is:
- No network call
- No API request
- No message dispatch
- No email integration
- No customer service platform integration

The console title explicitly states: "TicketPilot 审核控制台" with the caption "审核控制台 — 不自动发送回复".

Integration tests explicitly verify that no side effects beyond JSONL append occur.

## Deferred Items

- **Authentication / multi-user workflow** — Reviewer label is free-text; no login, roles, or permissions
- **Production database backend** — Replace JSONL with a shared database for multi-user access
- **Shared review queue** — No assignment, prioritization, or queue management across reviewers
- **Deployment** — No Docker container, no cloud deployment configuration
- **Trace dashboard / observability** — No Langfuse/Ragas integration for review analytics
- **Real-time ticket feed** — No polling or WebSocket for incoming tickets
- **Browser automation tests** — No Selenium/Playwright integration tests for the UI
- **Auto-send / reply dispatch** — Deliberately excluded; would require customer service platform integration
