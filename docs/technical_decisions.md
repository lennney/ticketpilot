# Technical Decisions

## Core Stack

- Backend: FastAPI (planned, no server code implemented)
- Workflow: LangGraph (planned, no workflow code implemented)
- Database: PostgreSQL
- Vector search: pgvector
- Keyword search: PostgreSQL full-text search
- Fusion: RRF
- Structured output: Pydantic
- Review UI: Streamlit for MVP (planned, no UI implemented)
- Dependency management: uv
- Runtime environment: WSL Ubuntu
- Deployment: Docker Compose

## Development Rules

- Use spec-driven development for non-trivial changes.
- Do not hardcode secrets.
- Keep prompts centralized with prompt_version.
- Use Pydantic schemas for critical outputs.
- Update docs/changelog.md after meaningful changes.

## Retrieval Architecture (Stage 1B Batch 2 — Implemented)

These values reflect the current implementation in `src/ticketpilot/retrieval/`.
If code values differ from this document, the code is authoritative.

### Vector Search (pgvector HNSW)

| Parameter | Value |
|-----------|-------|
| Index type | HNSW |
| m | 16 |
| ef_construction | 200 |
| ef_search | 100 |
| Distance operator | `<=>` (cosine distance) |
| Score formula | `1 - (embedding <=> query_vector)` |

### Fake Embedding Provider

| Parameter | Value |
|-----------|-------|
| Dimension | 384 |
| Seed mechanism | SHA-256 hash of text → first 8 hex chars → random seed |
| Value range | [-1, 1] |
| Status | PIPELINE VERIFICATION ONLY — no semantic meaning |

Note: Real embedding provider (small 384-d, quality 768-d) is planned but not implemented.

### Keyword Search

| Parameter | Value |
|-----------|-------|
| FTS config | `simple` (not `chinese`) |
| Index | GIN on `to_tsvector('simple', content)` |
| Fallback | LIKE on 8 Chinese business terms when FTS returns no results |

### RRF Fusion

| Parameter | Value |
|-----------|-------|
| k | 60 |
| Per-ranker contributions | Tracked in trace |

### Knowledge Base Design (Pending Resolution)

The FAQ/Policy/Case physical separation design is under review (BLOCK-2 audit finding).
Current implementation: single `knowledge_chunks` table with `doc_type` discriminator.
Proposed design: 3 source tables (`knowledge_faq`, `knowledge_policy`, `knowledge_case`) + 1 unified `knowledge_chunks` table with `source_table`/`source_id` references.
See `openspec/changes/close-project-audit-blockers/design.md` for the current decision.

### SourceRouter

Documented in earlier design drafts but NOT implemented. Intent-to-source routing will be added
as part of the `connect-retrieval-to-intake-risk-pipeline` change (deferred, not in current scope).

## Draft Generation Architecture (Stage 1C — Implemented)

These decisions reflect the implementation in `src/ticketpilot/drafting/`.

### Design Principle: Optional Workflow

Draft generation is an **optional workflow**, not part of the default `intake_risk_pipeline()` contract.
The `intake_risk_pipeline()` function continues to return `TicketOutput` unchanged. Callers who want
a draft must use the explicit entrypoint. This prevents the draft module from creating a breaking
change in any downstream consumer (Streamlit, API, tests).

### Entrypoints

- **`generate_draft(ticket_output: TicketOutput) -> DraftReply`** — standalone composition function.
  Instantiates `FakeDraftProvider` + `CitationValidator` internally, wires them together, wraps
  exceptions in a safe fallback draft. Does not modify the input `TicketOutput`.

- **`run_pipeline_with_draft(raw_ticket: RawTicket) -> DraftedTicketResult`** — optional workflow
  entrypoint. Calls the existing 4-stage pipeline, then calls `generate_draft` on the result.
  Returns a `DraftedTicketResult` wrapper containing both `ticket_output` and `draft_reply`.

### Wrapper Schema

`DraftedTicketResult` is a narrow wrapper combining exactly two fields:
- `ticket_output: TicketOutput` — the unchanged pipeline result
- `draft_reply: DraftReply` — the generated draft reply

No additional fields, no pipeline-result abstraction that could replace `TicketOutput`.

### Provider Strategy: FakeDraftProvider Only (MVP)

| Decision | Value |
|----------|-------|
| Provider | `FakeDraftProvider` (deterministic, template-based) |
| LLM calls | None |
| Network calls | None |
| API keys / env vars | None |
| Database queries | None |
| State | Stateless, thread-safe |
| Latency | Sub-millisecond |

The fake provider constructs replies from evidence candidates using a fixed Chinese template:
opening ("您好...") → evidence body with `[N]` citation markers → closing. Each evidence chunk
produces exactly one `Citation`. No external dependencies are required.

### CitationValidator: Deterministic Guardrail

The `CitationValidator` is a **deterministic regex-based guardrail**, not a full NLP claim verifier.
It performs two checks:

1. **Citation existence**: every `[N]` marker in `draft_text` must have a corresponding `Citation`
2. **Claim-coverage scan**: Chinese claim keywords (根据, 按照, 可以, 承诺, 等) without a citation marker
   in the same sentence are flagged

Known limitations:
- Regex patterns are imprecise — false positives and false negatives expected with real text
- Future replacement: LLM-based semantic claim verifier (same interface, different implementation)

### Safety Guarantees

| Scenario | Behavior |
|----------|----------|
| No evidence | Safe fallback text: no deterministic policy promises, confidence=0.0, citations=[] |
| High risk | Draft generated but `must_human_review=True`, confidence capped at 0.5 |
| Unsupported claims detected | `must_human_review=True`, `unsupported_claims` populated with issue descriptions |
| Provider/validator exception | Safe fallback draft returned (no crash), `fallback_reason="generation_error"` |

### Deferred Items (Not in MVP)

The following are explicitly out of scope for Stage 1C and documented as deferred:

- Real LLM provider (OpenAI, Claude, etc.) — `FakeDraftProvider` is the only implementation
- Human review UI (Streamlit) — no UI code exists
- LangGraph workflow orchestration
- Langfuse / Ragas observability
- Persistent `DraftGenerationTrace` storage in database
- Full evaluation pipeline with golden-answer test sets
- Auto-send or one-click reply dispatch
- Multi-turn or conversational draft generation
- Improved reranker or embedding fine-tuning

## Human Review Console Architecture (Stage 1D — Implemented)

### Design: Streamlit MVP, Not Production Frontend

The review console is a **Streamlit single-page application**, not a production-grade
admin panel. It is designed for local demo and manual testing, not for multi-user
deployment. Key architectural decisions:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Streamlit (single-page, no routing) | Zero frontend build step, Python-only, fast iteration |
| Persistence | Append-only JSONL (`ReviewStore`) | Zero infrastructure needed, full audit trail, easy to inspect |
| Review actions | APPROVE / EDIT / ESCALATE / REJECT | Covers all human review outcomes; no auto-send |
| Reviewer identity | Free-text label (`reviewer_label`) | MVP-only — no auth, no login |
| Entrypoint | `run_pipeline_with_draft(raw_ticket)` | Reuses existing pipeline + draft workflow unchanged |

### Audit Trail Design

`ReviewDecision` captures a self-contained snapshot of the review-time state:

| What | How |
|------|-----|
| Why human review was triggered | `review_trigger_reasons: list[str]` — "high_risk", "unsupported_claims", "no_evidence", "generation_error" |
| What the system produced | `original_draft_text`, `confidence`, `citations_summary`, `evidence_used_count` |
| What the reviewer did | `action`, `edited_text`, `decision_reason` |
| System state at review time | `was_high_risk`, `had_unsupported_claims`, `risk_flags`, `intent` |
| When | `reviewed_at` |

### Safety: No Auto-Send

The console has **no send functionality**. All four actions (Approve, Edit, Escalate,
Reject) only persist a `ReviewDecision` to local JSONL. There is no network call,
no API request, no message dispatch. This is a deliberate constraint:

> The review console is a decision-recording interface, not a reply-sending interface.

### Deferred Items

- Authentication / multi-user workflow
- Production database backend (replace JSONL)
- Shared review queue across reviewers
- Deployment (Docker, cloud)
- Trace dashboard / observability integration
- Real-time ticket feed (polling or WebSocket)

## Embedding Model Tiers (Planned, Not Implemented)

| Tier | Dimension | Status |
|------|-----------|--------|
| Fake (testing) | 384 | Implemented |
| Small (real) | 384 | Planned |
| Quality (real) | 768 | Planned |

## Unimplemented Components

The following are in pyproject.toml dependencies but have zero code:
- FastAPI, Uvicorn — web server (planned)
- LangGraph — workflow orchestration (planned)
- Streamlit — review UI (planned)
- Alembic, SQLAlchemy — ORM/migration framework (planned)
- HTTPx — HTTP client (planned)
- Pydantic-settings — config management (planned)
