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
| Unit tests | 1001 passed |
| Integration tests | 140 passed, 0 skipped |
| Coverage | ≥70% |
| Ruff | All checks passed |
| OpenSpec validate --all | 19/19 passed (post-Phase-11 archive) |
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

## 4. Current Working Context

**Phase 11 complete and archived. Phase 12 is the next recommended phase.**

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

## 5. Active OpenSpec Change

**Phase 11.8 — Offline Draft Evaluation** (active)
- draft_metrics.py with 4 pure metric functions + summary aggregation
- DraftEvaluationRow + DraftEvaluationSummary schemas in evaluation/schemas.py
- CLI runner run_draft_evaluation.py using FakeLLMProvider (no network, no API keys)
- 32 unit tests + 7 integration tests, all pass
- Markdown report: scope boundaries, metric definitions, summary, limitations

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

See `docs/harness/controller_decision_log.md` for full log.

## 7. Next Actions

| Priority | Action | Phase | Type | Status |
|---|---|---|---|---|
| 1 | Demo Readiness and Portfolio Delivery — Phase 12 | 12 | Docs | Next |
| — | Real Provider Optional Experiment (only if explicitly prioritized) | 12 | Analysis | Alternative |
| — | Query expansion audit (from Phase 10 findings) | — | Analysis | Future |

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
- Phase 10 cleanly archived
- Phase 11.4 code complete — active OpenSpec change: add-evidence-grounded-llm-draft
- Current baseline: 878 unit, 119 integration, 0 skipped, 86.35% coverage
- Latest commit: pending
- Metric granularity thesis confirmed: 78% of wrong cases reclassified as doc-ID found
- Doc-ID Recall@10: 91.9% (+32.5% over doc-type 59.4%)

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
