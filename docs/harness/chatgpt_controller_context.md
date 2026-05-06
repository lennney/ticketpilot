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
| Unit tests | 770 passed |
| Integration tests | 119 passed, 0 skipped |
| Coverage | 85.29% |
| Ruff | All checks passed |
| OpenSpec validate --all | 16/16 passed |
| Secret scan | Clean |

## 3. Completed Phases

| Phase | Status | Summary |
|---|---|---|
| Phase 1–6 | Archived | Foundation, pipeline, specs, schema, retrieval baseline |
| Phase 7 | Archived | Evaluation pipeline (offline eval, metrics, CLI) |
| Phase 8 | Archived | Real retrieval upgrade (comparison, fake-vs-real analysis) |
| Phase 9 | **Archived** | Evaluation-driven knowledge coverage optimization. 11 P0 records added, 770 unit/119 integration tests, 85.29% coverage, quality gate PASSED. Post-archive validation repair completed (54 skipped integrations fixed, 8 dimension-mismatch tests fixed). |
| Phase 10 | **Active** | Hybrid Retrieval Ranking Diagnosis — trace-first diagnosis of keyword/vector/RRF ranking pipeline. No tuning, no algorithm changes. |

## 4. Current Working Context

**Phase 10 — Hybrid Retrieval Ranking Diagnosis**

- **Change ID**: `add-hybrid-retrieval-ranking-diagnosis`
- **Current principle**: Trace-first, not tuning-first
- **Provider identity gate**: Every trace report MUST declare embedding provider. Fake provider = pipeline mechanics only (no semantic conclusions). Real provider = required for semantic ranking diagnosis.
- **Immutable baselines**: Phase 7/8/9 reports are read-only. Phase 10 outputs to `reports/retrieval/phase10_*` namespaced paths.

### Completed Sub-Phases

| Sub-Phase | Status | Key Deliverable |
|---|---|---|
| 10.1 Planning | ✅ Done | proposal.md, design.md, tasks.md, 2 spec files |
| 10.2 Trace Audit | ✅ Done | `reports/retrieval/phase10_trace_data_audit.md` — confirmed trace has all runtime data, only export gap |
| 10.3 P0 Trace Export | ✅ Done | `reports/retrieval/phase10_p0_layered_trace_export.md` + layered traces JSON. Vector recall 93.8%, keyword 31.2%, fused top-10 75.0%. |
| 10.4 Bottleneck Classification | ✅ Done | `reports/retrieval/phase10_p0_bottleneck_classification.md` — 75% fused_top10_but_metric_still_wrong, 18.8% recalled_but_fused_low, 6.2% vector_not_recalled |
| 10.5 Recommendation | **Pending** | |
| 10.6 Portfolio Delta | **Pending** | |
| 10.7 Archive | **Pending** | |

### Key Findings So Far

- Vector recall with real provider: **93.8%** — P0 records ARE being retrieved
- Keyword recall: **31.2%** — most P0 records are vector-only → vulnerable to RRF dual-source bias
- Fused top-10 loss: **75.0%** reach final evidence
- **75% of "wrong" cases are a metric granularity problem** (doc_type-level metric, not doc_id-level)
- Primary recommendation: add doc-level golden labels

## 5. Active OpenSpec Change

```
openspec/changes/add-hybrid-retrieval-ranking-diagnosis/
├── proposal.md
├── design.md
├── tasks.md
├── specs/
│   ├── retrieval-evaluation/spec.md
│   └── retrieval-trace/spec.md
```

To validate: `openspec validate add-hybrid-retrieval-ranking-diagnosis --strict`  
Full: `openspec validate --all`

## 6. Current Decisions

| # | Decision | Rationale | Date |
|---|---|---|---|
| D1 | Phase 10 is diagnosis-only — no tuning | Trace-first is more trustworthy than blind optimization | 2026-05-06 |
| D2 | Fake provider = pipeline mechanics only | Fake embeddings are deterministic but semantically meaningless | 2026-05-06 |
| D3 | Real provider (OpenAICompatible) required for semantic conclusions | Real embeddings produce meaningful vector recall | 2026-05-06 |
| D4 | GitHub docs/harness is source of truth for ChatGPT context | Notion is human-facing dashboard, not AI handoff | 2026-05-06 |
| D5 | Internal iteration preferred over micro-confirmations | User requested harness-mode operation, stop only on explicit conditions | 2026-05-06 |
| D6 | Next concrete step: add doc-level golden labels | Primary bottleneck is metric granularity, not retrieval quality | 2026-05-06 |

See `docs/harness/controller_decision_log.md` for full log.

## 7. Next Actions

| Priority | Action | Phase | Type | Status |
|---|---|---|---|---|
| 1 | Add doc-level golden labels (`expected_relevant_doc_ids`) for P0-related cases | 10.5 | Data | Pending |
| 2 | Fusion ranking experiment (lower RRF k or score-based fusion) | 10.5 | Code | Pending |
| 3 | Query expansion audit for case_refu_013 counterfeit policy | 10.5 | Analysis | Pending |
| 4 | Create portfolio delta snapshot | 10.6 | Docs | Pending |
| 5 | Final validation and archive | 10.7 | Validation | Pending |

See `docs/harness/controller_next_actions.md` for full details with allowed/forbidden files and validation commands.

## 8. Stop Conditions

If any of the following trigger, stop and report:

1. Unknown large-scale src/tests/data modifications with no explanation
2. Trace schema found insufficient, requiring core retrieval algorithm changes
3. Need to modify retrieval algorithm, RRF logic, embedding provider, or chunking architecture
4. Need to add or modify knowledge seed data (for Phase 10 diagnosis)
5. Need to modify golden expectations (for Phase 10 diagnosis)
6. Real API key required but unavailable locally — record as skipped, do not ask for key
7. Full quality gate or necessary tests fail after 2 consecutive repair attempts
8. Integration tests skipped count > 0
9. .env / .env.local / API key / token / Authorization header may enter git
10. Risk of overwriting Phase 7/8/9 baseline reports
11. Forbidden claims in reports: production-ready, real enterprise validated, real customer data, real-world benchmark, auto-send, replace human agent, 线上效果, 行业 benchmark

## 9. New ChatGPT Window Boot Prompt

When opening a new ChatGPT window to work on TicketPilot, start with:

```
You are working on TicketPilot, a local deterministic human review workflow for
customer service ticket triage. Read `AGENTS.md` for the project constitution.

Current state:
- Phase 9 cleanly archived (770 unit, 119 integration, 0 skipped, 85.29% coverage)
- Phase 10 active: add-hybrid-retrieval-ranking-diagnosis
- Phase 10.2–10.4 completed: trace audit → P0 export → bottleneck classification
- Phase 10.5–10.7 pending: recommendation, portfolio delta, archive

Key findings so far:
- Vector recall with real provider: 93.8%
- Keyword recall: 31.2%
- 75% of wrong cases = metric granularity problem (doc_type-level vs doc_id-level)
- Primary recommendation: add doc-level golden labels

Read `docs/harness/chatgpt_controller_context.md` for full context.
Read `docs/harness/controller_decision_log.md` for decision history.
Read `docs/harness/controller_next_actions.md` for next batch details.
Read `docs/harness/controller_session_log.md` for recent handoff summaries.

Validate status: git status --short
Active change: openspec validate add-hybrid-retrieval-ranking-diagnosis --strict
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
