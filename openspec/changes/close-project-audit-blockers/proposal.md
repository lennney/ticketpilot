# Proposal: Close Project Audit Blockers

## Executive Summary

The 2026-04-29 project plan audit (`docs/audits/project_plan_audit_2026-04-29.md`) identified 5 blocking issues that must be resolved before proceeding to any new product features. This remediation change addresses those blockers and key non-blocking documentation/infrastructure gaps. **No new product features are included in scope.**

## Problem Statement

The audit found:

1. **BLOCK-1**: The quality gate is a no-op (`|| true` on every check), making it impossible for CI to detect failures. 26 skipped integration tests are invisible to the gate.
2. **BLOCK-2**: The OpenSpec design requires FAQ/Policy/Case physical separation (3 source tables), but implementation uses a single `knowledge_chunks` table with a `doc_type` discriminator. Spec and implementation disagree.
3. **BLOCK-3**: The retrieval module is disconnected from the main pipeline. `pipeline.py` stops at risk assessment; `hybrid_retrieval` exists but is never called. This blocks the next product workflow (evidence-grounded draft reply).
4. **BLOCK-4**: 26 integration tests are conditionally skipped and have never been verified against a real PostgreSQL+pgvector instance. Zero end-to-end verification exists.
5. **BLOCK-5**: README describes an 11-stage Copilot product; only ~3 of 8 planned stages have code. No mention of gaps, fake embeddings, or DB status.

## What This Change Fixes

| Blocker | Fix |
|---------|-----|
| BLOCK-1 | Remove `|| true` from quality gate checks, add `--strict-markers` to pytest, add skip-count gate |
| BLOCK-2 | Add 3 physical source tables (`knowledge_faq`, `knowledge_policy`, `knowledge_case`) while keeping `knowledge_chunks` as a unified chunk table. Amend spec to clarify the two-layer design. |
| BLOCK-3 | Document as blocking for next feature. Create future change placeholder. **Not implemented here.** |
| BLOCK-4 | Create Docker-based integration test runner, write migration scripts, verify all 26 integration tests pass against real pgvector |
| BLOCK-5 | Add "Current Status" section to README with phase status, gaps, and limitations |

Plus targeted non-blocking fixes:
- GAP-9: Sync `docs/technical_decisions.md` contradictions (ef_construction, fake dim, FTS config)
- GAP-8: Delete duplicate `docs/acceptance_report_batch1.md`
- GAP-10: Fix `docker-compose.yml` volume path
- GAP-12: Add note to `002_seed_knowledge_chunks.sql` explaining Python seeding
- GAP-13: Label fake embedding as "pipeline verification only"

## What This Change Explicitly Does NOT Touch

- Reply generation / evidence draft
- Streamlit UI
- LangGraph workflow
- Real embedding provider (beyond fake)
- Reranker
- Langfuse / Ragas integration
- Any new product feature
- BLOCK-3 wiring (deferred to future change `connect-retrieval-to-intake-risk-pipeline`)
- Non-blocking gaps GAP-1 through GAP-7, GAP-11 (tracked but deferred)

## Success Criteria

1. `scripts/run_quality_gate.sh` fails when tests fail or integration tests are skipped
2. 3 physical source tables exist in database: `knowledge_faq`, `knowledge_policy`, `knowledge_case`
3. `knowledge_chunks` table retains `doc_type` discriminator and adds `source_table`/`source_id` columns
4. Docker Compose starts PostgreSQL+pgvector, runs migrations, seeds data, and all 26 integration tests pass with 0 skips
5. README accurately reflects current project state with "Current Status" section
6. `docs/technical_decisions.md` is internally consistent with actual code values
7. OpenSpec knowledge-schema spec reflects the two-layer design (source tables + chunk table)

## Impact

- Modified: `scripts/run_quality_gate.sh`, `README.md`, `docs/technical_decisions.md`, `docker-compose.yml`
- Added: `db/migrations/003_create_source_tables.sql`, new integration test runner script
- Modified spec: `openspec/changes/add-layered-knowledge-retrieval-foundation/specs/knowledge-schema/spec.md`
- Modified design: `openspec/changes/add-layered-knowledge-retrieval-foundation/design.md`
- Deleted: `docs/acceptance_report_batch1.md`
- Added annotation: `db/migrations/002_seed_knowledge_chunks.sql`, `src/ticketpilot/retrieval/providers/fake_embedding.py`
