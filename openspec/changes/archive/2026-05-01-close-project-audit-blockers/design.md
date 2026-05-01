## Context

The 2026-04-29 project plan audit identified 5 blocking issues. This design document provides the architectural decisions for each blocker, with special attention to BLOCK-2 (physical DB separation) which requires an architect decision before implementation.

**Reference audit**: docs/audits/project_plan_audit_2026-04-29.md
**Current branch**: audit/project-plan-review
**Parent change**: add-layered-knowledge-retrieval-foundation (Stage 1B)

## Goals / Non-Goals

**Goals:**
- Fix quality gate so it can actually detect failures
- Resolve physical DB separation ambiguity (spec vs implementation)
- Document retrieval-pipeline disconnection with future change plan
- Verify all integration tests against real PostgreSQL+pgvector
- Correct README to accurately reflect project maturity

**Non-Goals:**
- Wire retrieval into the main pipeline (future change)
- Add any new product features
- Add real embedding provider, reranker, Langfuse/Ragas
- Fix all 17 non-blocking gaps (only highest-priority documentation gaps)

---

## BLOCK-1 Design: Quality Gate Fix

### Current State

The quality gate script uses || true on every check, making it impossible to fail. 26 skipped integration tests are invisible because || true absorbs the skipped count. The set -e at the top has no effect since every command uses || true.

### Decision

Replace the no-op gate with a gate that actually fails when problems exist.

### Changes

1. **Remove || true** from ruff, pytest, and openspec lines.

2. **Add --strict-markers to pytest** to catch typos in marker names.

3. **Add integration test skip-count guard**:
   - Run pytest for unit tests (always pass).
   - Run a separate pytest invocation for integration tests that checks skip count.
   - If SKIPPED > 0 in integration test output, fail with a clear message.
   - Allow env var TICKETPILOT_SKIP_DB_TESTS=1 to bypass.

4. **Add a minimum coverage threshold** (70%) to catch dead code.

### Acceptance Criteria

- Running the gate without a DB fails with a clear message about skipped integration tests.
- Running the gate with a running DB and all tests passing exits 0.
- Running the gate with a failing unit test exits non-zero.

---

## BLOCK-2 Design: Physical DB Separation (ARCHITECT DECISION)

### Current State

**Spec says**: FAQ, Policy, and Case MUST be physically separated (3 distinct tables). FORBIDDEN: mixing into one table.

**Implementation has**: One knowledge_chunks table with a doc_type discriminator. Zero source tables exist. Migration 001 creates only chunks. Migration 002 is a no-op placeholder.

### Architect Decision: Two-Layer Design

**Decision**: Implement a two-layer database design:
- **Source layer**: 3 physical tables (knowledge_faq, knowledge_policy, knowledge_case) with distinct schemas.
- **Chunk layer**: 1 unified knowledge_chunks table with source_table and source_id columns.

### Rationale

1. **Satisfies spec physical separation**: Each doc type has its own source table with type-specific columns (intent_tags, policy_code, risk_level, compensation_amount).
2. **Preserves retrieval efficiency**: All retrieval operates on knowledge_chunks. Three chunk tables would require union queries.
3. **Matches original rationale**: Separation reasons (update frequencies, access patterns, retention, metadata) are source-layer concerns.
4. **Document-centric workflow**: source doc -> chunking -> knowledge_chunks with back-references. Standard ETL pattern.
5. **Minimal migration impact**: Only 2 new columns on existing knowledge_chunks.

### Spec Amendment

Before: The system SHALL store FAQ, Policy, and Case documents in physically separate database tables.
After: The system SHALL store FAQ, Policy, and Case **source documents** in physically separate database tables (knowledge_faq, knowledge_policy, knowledge_case), each with type-specific columns. All document types SHALL share a unified knowledge_chunks table for retrieval, with source_table and source_id columns tracing each chunk back to its source document.

### Source Table Schemas

knowledge_faq: id, business_domain, title, content, intent_tags[], created_at, updated_at
knowledge_policy: id, business_domain, policy_code, title, content, effective_date, created_at, updated_at
knowledge_case: id, business_domain, case_id, issue_summary, resolution, risk_level, compensation_amount, created_at, updated_at

### knowledge_chunks additions
- source_table VARCHAR(20) NOT NULL
- source_id UUID NOT NULL
- doc_type retained as denormalized convenience

### Alternatives Considered

**A: Amend spec only, accept single-table-with-discriminator.** Zero work but violates spec rationale about different schemas. Loses referential integrity.
**B: Three chunk tables.** Maximum separation but complicates retrieval with union queries.
**Selected: Two-layer (3 source + 1 chunk).** Standard pattern used by LangChain, LlamaIndex, production RAG.

---

## BLOCK-3 Design: Retrieval Disconnected from Main Pipeline

### Current State

pipeline.py stops at risk assessment. hybrid_retrieval exists but is never called.

### Decision: Defer to a Separate Change

**This remediation does NOT wire retrieval into the pipeline.**

### Rationale

BLOCK-3 is blocking for the next product workflow, not a defect in Batch 2 scope. Batch 2 was scoped as "retrieval foundation" without pipeline integration.

Wiring requires design decisions (IntentClass-to-BusinessDomain mapping, retrieval parameters, error handling, schema changes) that belong in their own OpenSpec change.

### Future Change: connect-retrieval-to-intake-risk-pipeline

Will add: intent-to-domain mapping, retrieval stage in pipeline.py, extended TicketOutput.

### Acceptance Criteria

- This design document clearly states the deferral.
- No pipeline.py changes in this remediation.

---

## BLOCK-4 Design: Integration Test DB Verification

### Current State

26 integration tests conditionally skipped. Zero end-to-end verification.

### Decision: Docker-Based Runner

Script that:
1. Starts PostgreSQL+pgvector via Docker Compose
2. Waits for healthy DB
3. Runs all migrations
4. Seeds data
5. Runs integration suite with pytest tests/integration/ -v
6. Asserts 0 skipped
7. Teardown (with --keep-db option)

### Implementation Notes

- Fix docker-compose.yml volume path: ./db/seed -> ./db/migrations
- Add scripts/run_integration_tests.sh
- Fix test_embedding_dimension_validation to not require DB import
- Use conftest.py for shared DB fixtures

### Acceptance Criteria

- All 26 integration tests run against real pgvector
- At least 25 of 26 pass
- Skipped count = 0 (or explicitly justified)

---

## BLOCK-5 Design: README Accuracy

### Current State

README describes 11-stage Copilot. Only ~3 stages exist. No gap disclosure.

### Decision

Add "Current Status" section:
1. Implemented phases with status (ACCEPTED, ACCEPTED_WITH_DB_GAP)
2. Planned phases as "not started"
3. Key limitations (fake embeddings, DB gap, no LLM, no UI)
4. Link to docs/phase_status.md

### Acceptance Criteria

- Current Status section exists
- Accurate phase listing
- Limitation disclosure
- Link to phase_status.md

---

## Non-Blocking Fixes

### GAP-8: Delete docs/acceptance_report_batch1.md (duplicate of qa_evaluation_batch1.md)
### GAP-9: Sync technical_decisions.md (ef_construction 200, fake dim 384, FTS config simple)
### GAP-10: Fix docker-compose.yml volume path (db/seed -> db/migrations)
### GAP-12: Annotate 002_seed_knowledge_chunks.sql as no-op marker
### GAP-13: Label fake_embedding.py as "PIPELINE VERIFICATION ONLY"
