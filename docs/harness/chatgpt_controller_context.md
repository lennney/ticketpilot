# ChatGPT Controller Context — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Notion is a human-facing dashboard only — this file and its siblings are the canonical project handoff.*

---

## 1. Project Snapshot

| Field | Value |
|---|---|
| **Project** | TicketPilot — local, deterministic, no-LLM, no-auto-send human review workflow for customer service ticket triage |
| **Stack** | Python 3.11+, PostgreSQL 16 + pgvector 0.8+, psycopg-binary, uv, pytest, ruff, OpenSpec |
| **Repository** | `github.com/lennney/ticketpilot` |
| **Harness** | AI Development Harness (AGENTS.md + prompts/harness/*.md) |
| **Data** | 101 synthetic eval tickets, 106 synthetic knowledge records |
| **Embedding** | FakeEmbeddingProvider (default, 384-d, deterministic); OpenAICompatibleProvider (opt-in via .env.local, 1024-d) |
| **Retrieval** | Hybrid: PostgreSQL FTS (keyword) + pgvector HNSW (vector) → RRF fusion (k=60) |

## 2. Latest Clean Baseline

| Check | Result |
|---|---|
| Unit tests | 1078 passed |
| Integration tests | 146 passed, 0 skipped |
| Coverage | ≥70% (86.56%) |
| Ruff | All checks passed |
| OpenSpec validate --all | 24/24 passed (post-Phase-13.10 archive) |
| Secret scan | Clean |
| Overclaim scan | Clean |

## 3. Completed Phases

| Phase | Status | Summary |
|---|---|---|
| Phase 1–6 | Archived | Foundation, pipeline, specs, schema, retrieval baseline |
| Phase 7 | Archived | Evaluation pipeline (offline eval, metrics, CLI) |
| Phase 8 | Archived | Real retrieval upgrade (comparison, fake-vs-real analysis) |
| Phase 9 | Archived | Evaluation-driven knowledge coverage optimization. 11 P0 records added, Provider Identity Gate established. |
| Phase 10 | **Archived** | Hybrid Retrieval Ranking Diagnosis — Doc-ID Recall@10 = 91.9%, 32/41 (78%) wrong cases reclassified as metric granularity. |
| Phase 11 | **Archived** | Evidence-Grounded LLM Draft Generation — 8-layer safety architecture, LLMProvider + FakeLLMProvider, ClaimGuard, offline draft evaluation (8 deterministic metrics). |
| Phase 12A | **Archived** | OpenAI-compatible LLM provider for offline comparison — OpenAICompatibleProvider, 25-case fixture set, comparison runner, mock tests, real provider pending local env configuration. |
| Phase 12B | **Archived** | Agent Error Memory and Repair Learning System — harness/process improvement only, no product runtime changes. |
| Phase 12C | **Archived** | Optional Real Provider Run — fake baseline validated, real provider (deepseek-v4-pro) run completed 2026-05-07. |
| Phase 12D.1 | **Completed** | Resolved untracked openspec/specs/error-memory directory — promoted spec was not committed in Phase 12B archive. |
| Phase 13 | **Archived** | Extended Draft Evaluation Metrics — extended Phase 12 comparison with citation validation, claim guard, reviewer-ready metrics. OpenSpec change created. |
| Phase 13.10 | **Archived** | Guard-Aware Provider Prompting Experiment — real provider guard pass 4%→84%, citation validation 12%→76%, reviewer-ready 4%→64%. OpenSpec change archived, spec promoted. |
| Phase 13.10.2 | **Completed** | Clean archive working tree — staged deletions committed, intermediate timestamped eval files restored to working tree. |
| Phase 14.1 | **Active** | Guard Architecture Improvement Planning — granular failure taxonomy OpenSpec change created, Phase 13.10 failure analysis complete, 7 sub-tasks planned (14.1 done, 14.2-14.7 pending). |

## 4. Current Working Context

**Phase 12A complete and archived. Phase 12B (Error Memory) is the current active batch. Phase 12C is the next recommended phase after archive.**

### Phase 11 Evidence Chain

Phase 11 (Evidence-Grounded LLM Draft Generation) completed all 10 sub-phases:

The diagnosis followed 7 sub-phases in sequence:

| Sub-Phase | Key Deliverable |
|---|---|
| 10.2 Trace Audit | Confirmed trace has all runtime data, only export gap |
| 10.3 P0 Trace Export | Vector recall 93.8%, keyword 31.2%, fused top-10 75.0% |
| 10.4 Bottleneck Classification | 75% = metric granularity, 18.8% = RRF fusion, 6.2% = vector miss |
| 10.5 Doc-Level Labels (P0) | `expected_relevant_doc_ids` populated for 14 cases |
| 10.5.1 P0 Real Pipeline Eval | 10/14 P0 cases doc-ID correct at top-10 (71.4%) |
| 10.7 Full Label Expansion | 86/101 cases labeled |
| 10.7.5 Full Dataset Real Eval | **Thesis confirmed**: 32/41 (78%) reclassified. Doc-ID Recall@10 = 91.9% |
| 10.8 Portfolio Snapshot | Created `phase10_hybrid_ranking_diagnosis_snapshot.md` |
| 10.9 Final Validation + Archive | Quality gate: 778 unit, 119 integration, 0 skipped, 85.27%, OpenSpec 16/16 |

### Key Findings (Archived)

- Vector recall with real provider: **93.8%** — P0 records ARE being retrieved
- Keyword recall: **31.2%** — most P0 records are vector-only → vulnerable to RRF dual-source bias
- Doc-ID Recall@10: **91.9%** (+32.5% over doc-type 59.4%)
- **32/41 (78%) wrong cases reclassified as doc-ID found** — metric granularity thesis confirmed
- **7 zero-hit cases**: query expansion candidates
- **32 partial-hit cases**: fusion ranking candidates
- **9 genuine misses**: 5 edge cases + 4 domain cases

### Immutable Baselines

- Phase 7/8/9 reports are read-only
- Phase 10 reports under `reports/retrieval/phase10_*` are read-only
- Archived OpenSpec change is at `openspec/changes/archive/2026-05-06-add-hybrid-retrieval-ranking-diagnosis/`
- Specs promoted: `openspec/specs/retrieval-evaluation/`, `openspec/specs/retrieval-trace/`
- Portfolio snapshots (Phase 8/9/10) are read-only
- Phase 13.10 archived: `openspec/changes/archive/2026-05-07-add-guard-aware-provider-prompting/`
- Spec promoted: `openspec/specs/guard-aware-prompting/spec.md`

## 5. Active OpenSpec Change

**Phase 15.2 — align-chat-support-product-experience** (active, Phase 15.2 done)
- Phase 15.1: planning and spec created
- Phase 15.2: chat module (`src/ticketpilot/chat/`), Streamlit UI skeleton, 50 unit tests
- Tasks: 15.2 (done) → 15.3-15.8 pending
- Scope: Phase 15.3 pipeline-to-chat adapter is next
- Phase 14 guard taxonomy paused (14.3-14.7), guard remains as safety foundation

**Phase 14.1 — add-guard-architecture-improvement-planning** (active, guard scope paused)
- Phase 14.2/14.2.1 complete (guard taxonomy data model)
- Phase 14.3-14.7 paused,优先级低于 chat demo

## 6. Current Decisions

## 6. Current Decisions

| # | Decision | Rationale | Date |
|---|---|---|---|
| D1 | Phase 10 is diagnosis-only — no tuning | Trace-first is more trustworthy than blind optimization | 2026-05-06 |
| D2 | Fake provider = pipeline mechanics only | Fake embeddings are deterministic but semantically meaningless | 2026-05-06 |
| D3 | Real provider (OpenAICompatible) required for semantic conclusions | Real embeddings produce meaningful vector recall | 2026-05-06 |
| D4 | GitHub docs/harness is source of truth for ChatGPT context | Notion is human-facing dashboard, not AI handoff | 2026-05-06 |
| D5 | Internal iteration preferred over micro-confirmations | User requested harness-mode operation, stop only on explicit conditions | 2026-05-06 |
| D6 | Add doc-level golden labels as next priority | Primary bottleneck was metric granularity, not retrieval quality | 2026-05-06 |
| D7 | Phase 10 is closed; do not continue retrieval tuning inside Phase 10 | Thesis confirmed, evaluation infrastructure built, archive complete | 2026-05-06 |
| D8 | Default next phase is Evidence-Grounded LLM Draft Generation | Product frontier moves from evidence retrieval to evidence-grounded generation; continued retrieval tuning has diminishing portfolio value | 2026-05-06 |
| D9 | Phase 11 complete — 8-layer safety architecture validated | Safety architecture is foundational for AI-assisted workflows; demonstrating safety-first design has portfolio value | 2026-05-06 |
| D10 | Phase 11 archived; next phase is Demo Readiness | Phase 11 archived, Phase 12 (Demo Readiness and Portfolio Delivery) is recommended next | 2026-05-06 |
| D11 | Phase 13 complete — extended draft evaluation metrics confirmed | Real provider guard pass 4%→84% after guard-aware prompt; 4 remaining failures are correct guard behavior; OpenSpec archived | 2026-05-07 |
| D12 | Guard-aware prompting is effective but not sufficient | Real provider guard pass improved from 4% to 84% via structured prompt; remaining failures (risk escalation, unsupported claims) require guard architecture improvement not prompt-only fix | 2026-05-07 |
| D13 | Phase 13.10 is archived; next phase is TBD | All Phase 13 changes complete and archived; no active OpenSpec change; next batch to be defined | 2026-05-07 |
| D14 | Guard taxonomy enables granular failure analysis | Phase 13.10 failures collapse to booleans; granular taxonomy (8 types) enables per-failure-type metrics and targeted improvement | 2026-05-07 |

See `docs/harness/controller_decision_log.md` for full log.

## 7. Next Actions

| Priority | Action | Phase | Type | Status |
|---|---|---|---|---|
| 1 | Phase 15.1 Chat Support Product Re-alignment Planning | 15.1 | Spec | Done |
| 2 | Phase 15.2 Chat Demo UI Skeleton | 15.2 | Runtime | Done |
| 3 | Phase 15.3 Pipeline-to-Chat Adapter | 15.3 | Runtime | Pending |
| — | Phase 14.3 Safe Language Classifier | 14.3 | Runtime | Pending |
| — | Phase 14.4 Claim Guard Integration | 14.4 | Runtime | Pending |
| — | Phase 14.5 Evaluation Runner Extension | 14.5 | Runtime | Pending |
| — | Phase 14.6 Reviewer Console / Portfolio | 14.6 | Docs | Pending |
| — | Phase 14.7 Final Validation and Archive | 14.7 | Validation | Pending |
| — | Query expansion audit (from Phase 10 findings) | — | Analysis | Future |
| — | Query expansion audit (from Phase 10 findings) | — | Analysis | Future |
| — | Guard architecture improvement for risk escalation compliance | — | Analysis | Future |

See `docs/harness/controller_next_actions.md` for full details with allowed/forbidden files and validation commands.

## 8. Stop Conditions

If any of the following trigger, stop and report:

1. Unknown large-scale src/tests/data modifications with no explanation
2. Need to modify retrieval algorithm, RRF logic, embedding provider, or chunking architecture
3. Need to add or modify knowledge seed data
4. Need to modify golden expectations
5. Real API key required but unavailable locally — record as skipped, do not ask for key
6. Full quality gate or necessary tests fail after 2 consecutive repair attempts
7. Integration tests skipped count > 0 (for archive/push)
8. .env / .env.local / API key / token / Authorization header may enter git
9. Risk of overwriting Phase 7/8/9/10 baseline reports or portfolio docs
10. Forbidden claims in reports: production-ready, real enterprise validated, real customer data, real-world benchmark, auto-send, replace human agent, 线上效果, 行业 benchmark

## 9. New ChatGPT Window Boot Prompt

When opening a new ChatGPT window to work on TicketPilot, start with:

```
You are working on TicketPilot, a local deterministic human review workflow for
customer service ticket triage. Read `AGENTS.md` for the project constitution.

Current state:
- Phase 15.2 active — chat demo UI skeleton created
- Active OpenSpec change: align-chat-support-product-experience
- Current baseline: 1137 unit (+50), 146 integration, 0 skipped
- Product direction: chat-style AI customer service copilot (e-commerce scenario)
- Backend complete: intent classification, risk detection, evidence retrieval, draft generation, citation validation, claim guard, human review console
- Chat module: src/ticketpilot/chat/ with schemas and Streamlit UI skeleton
- Next: Phase 15.3 pipeline-to-chat adapter

Key boundaries:
- Local demo / portfolio prototype — not production
- All data is synthetic — no real customer data
- No auto-send — architectural invariant
- Human-in-the-loop for high-risk outputs
- Offline evaluation only — not a production benchmark

Read `docs/harness/chatgpt_controller_context.md` for full context.
Read `docs/harness/controller_decision_log.md` for decision history.
Read `docs/harness/controller_next_actions.md` for next batch details.
Read `docs/harness/controller_session_log.md` for recent handoff summaries.

Validate status: git status --short
Full validation: openspec validate --all
```

## 10. Update Rules

1. **Every batch must update** `docs/harness/chatgpt_controller_context.md` if project status, phase, or next actions changed.
2. **Every batch must update** `docs/harness/controller_session_log.md` with a structured handoff summary.
3. **Controller context is NOT a chat transcript** — never store full conversation logs, API keys, secrets, or raw private communication.
4. **Store only structured handoff summaries**: phase changes, key decisions, validation results, next actions.
5. **Notion is a human-facing dashboard** — the canonical source of truth is `docs/harness/`.
6. **Update before final commit** — controller context updates should be included in the same commit as the batch output.
7. **Return at end of every batch** whether controller context was updated.
