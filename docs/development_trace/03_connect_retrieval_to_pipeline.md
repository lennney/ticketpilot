# Stage 3: Connect Retrieval to Intake-Risk Pipeline

## Stage Goal

Wire the independently-built retrieval engine (Stage 1B) into the main intake-risk pipeline (Stage 1A) as Stage 4, creating a 4-stage pipeline: intake -> classify -> assess risk -> retrieve evidence. This adds query construction from ticket state and evidence mapping to the pipeline output.

## Business Problem Addressed

After risk triage, the system has a classified and risk-assessed ticket but no relevant knowledge. Adding retrieval as Stage 4 means the pipeline output includes evidence candidates from the knowledge base, enabling downstream consumers (draft generation, human review) to ground their decisions in retrieved knowledge.

Without this stage, the pipeline produces a risk assessment with no context — it knows the ticket is about a refund with compensation risk, but has no policy or case information to inform a response.

## Key Design Decisions

### 1. EvidenceCandidate as boundary schema (not reusing FusedResult)
- **Decision**: Create a new `EvidenceCandidate` Pydantic model as the boundary type between retrieval and pipeline, rather than reusing the retrieval module's `FusedResult`.
- **Rationale**: `FusedResult` carries retrieval-internal fields (keyword_rank, vector_rank, per-ranker contributions) not needed by downstream consumers. `EvidenceCandidate` includes `source_table` (needed for source document lookup) which is not on `FusedResult`. A clean boundary keeps the API surface minimal and focused.
- **Alternatives**: Reusing `FusedResult` directly (rejected — leaks retrieval internals to pipeline consumers).

### 2. TicketOutput extension (not subclassing)
- **Decision**: Add optional `evidence_candidates: list[EvidenceCandidate]` and `retrieval_trace: RetrievalTrace | None` fields to the existing `TicketOutput` model.
- **Rationale**: Backward compatible — existing constructors work without modification, callers that do not care about evidence ignore the new fields. A subclass would require `isinstance()` checks throughout the codebase.

### 3. Query construction from ticket state
- **Decision**: `build_retrieval_query()` in `src/ticketpilot/retrieval/query_builder.py` combines normalized ticket text + intent-derived Chinese business terms + risk-flag-derived Chinese business terms into a single query string.
- **Rationale**: Intent-derived terms improve recall (e.g., appending "退款 退货 政策" for a refund ticket). Risk-flag terms broaden recall when specific risks are identified.
- **Design choice**: Risk flags are mapped to business terms (e.g., COMPENSATION_RISK -> "赔偿 补偿 金额"), not appended to the query as qualifiers. Meta flags (LOW_CONFIDENCE, INSUFFICIENT_EVIDENCE) are excluded from query expansion.

### 4. Immutable flag handling in pipeline
- **Decision**: A `_with_added_risk_flag()` helper creates a new `RiskAssessment` with an added flag, never mutating the original `flags` set.
- **Rationale**: Prevents subtle bugs from in-place set mutation across pipeline stages. Each stage's output is a new object.

### 5. Graceful degradation for Stage 4
- **Decision**: Stage 4 is isolated in its own try/except block. Failures in retrieval never break the pipeline output. If retrieval fails, empty evidence is returned and `INSUFFICIENT_EVIDENCE` is added to risk flags.
- **Rationale**: A retrieval failure (DB connection error, timeout) should not prevent the system from returning a risk assessment. The ticket can still be triaged for human review.

### 6. `retrieve_evidence()` thin wrapper
- **Decision**: A thin wrapper function in `src/ticketpilot/retrieval/retrieve_evidence.py` composes `build_retrieval_query` -> `hybrid_retrieval` -> `map_fused_to_evidence`, keeping `pipeline.py` decoupled from retrieval internals.
- **Rationale**: Simple composition without modifying the retrieval module's internal pipeline. The wrapper is independently testable.

## Implementation Scope

### Batch A: Schema Extension
- Created `src/ticketpilot/schema/evidence.py` with `EvidenceCandidate` model (9 fields: chunk_id, doc_id, doc_type, source_id, source_table, content, score, rank, title)
- Extended `TicketOutput` with `evidence_candidates` and `retrieval_trace` fields
- Added 11 unit tests for EvidenceCandidate and TicketOutput defaults

### Batch B: Query Construction
- Created `src/ticketpilot/retrieval/query_builder.py` with `build_retrieval_query()`
- Implemented intent-to-business-term mapping for all 8 intents
- Implemented risk-flag-to-business-term mapping for 5 substantive risk flags
- Term deduplication preserving insertion order
- Added 13 unit tests for query builder

### Batch C: Pipeline Integration
- Created `src/ticketpilot/retrieval/evidence_mapper.py` with `map_fused_to_evidence()` adapter
- Created `src/ticketpilot/retrieval/retrieve_evidence.py` with `retrieve_evidence()` wrapper
- Wired `retrieve_evidence()` into `intake_risk_pipeline()` as Stage 4 after risk assessment
- Added `_with_added_risk_flag()` helper for immutable flag handling
- Empty evidence adds `INSUFFICIENT_EVIDENCE` flag and sets `must_human_review=True`
- Added 10 unit tests for pipeline retrieval integration

### Batch D: Export Cleanup + Integration Tests + Quality Gate
- Added lazy `__getattr__` exports for `build_retrieval_query`, `map_fused_to_evidence`, `retrieve_evidence` (avoids circular imports)
- Retrofitted 7 existing pipeline tests to mock `retrieve_evidence` (eliminating live DB dependency)
- Added 6 integration tests for the full 4-stage pipeline against live DB

## Forbidden Scope

- No pipeline.py modifications from Batch D onward
- No retrieval engine internals modified (zero changes to `src/ticketpilot/retrieval/pipeline.py`)
- No reply generation (handled in Stage 1C)
- No `map_intent_to_doc_types` implementation (deferred from design)
- No `RetrievalTrace` naming collision fix (deferred cleanup)
- No `enable_retrieval` flag from design.md (simplification)
- No integration tests added in Batch C (added in Batch D)

## Tests and Quality Gate Result

| Metric | Value |
|--------|-------|
| Unit tests (Batch A) | 11 new (evidence schema + mapper) |
| Unit tests (Batch B) | 13 new (query builder) |
| Unit tests (Batch C) | 10 new (pipeline retrieval) |
| Unit tests (Batch D) | 7 retrofitted with mocks |
| Integration tests (Batch D) | 6 new (full pipeline against live DB) |
| Total unit tests | 202 passed |
| Total integration tests | 55 passed, 0 skipped |
| Ruff | All checks passed |
| OpenSpec validate --changes | 4/4 passed |
| Quality gate | PASSED |

## Major Risks

| Risk | Handling |
|------|----------|
| **source_id = doc_id is a seed-only assumption** | Current seed data has single-chunk documents where doc_id equals the source table PK. Must be replaced by DB lookup when multi-chunk documents are supported. |
| **Schema layer imports RetrievalTrace and DocType from retrieval modules** | Acceptable for MVP; creates a one-way dependency (schema depends on retrieval). Possible future clean-up if circular imports emerge. |
| **Empty-evidence from retrieval may conflict with existing risk flags** | `INSUFFICIENT_EVIDENCE` can be set by both the risk assessor (ticket-level evidence) and retrieval (knowledge-base evidence). Both can coexist — handled by immutable flag helper. |
| **Unit-level pipeline tests depend on live DB** | Batch D retrofitted 7 tests with mocks to eliminate this dependency. |

## Deferred Items

- `map_intent_to_doc_types` — Intent-to-doc-type filtering was designed but not required by spec; deferred from design.md
- `RetrievalTrace` naming collision — Duplicate `RetrievalTrace` name exists in retrieval module; deferred cleanup
- `enable_retrieval` flag on `intake_risk_pipeline()` — Design.md feature not implemented; simplification for MVP
- Evidence scoring threshold tuning — RRF scores have no absolute meaning; threshold tuning deferred until evaluation data exists

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| (Batch A-D commits on feature branch, merged into master) | 2026-04-30 | |
| `9738f37` | 2026-04-30 | Merge branch 'fix/audit-blockers' (pipeline integration was on this branch) |

*Note: The pipeline integration commits were on the `fix/audit-blockers` branch and are included in the merge commit. The changelog documents four batches (A-D) implemented as part of this change.*

## Reusable Patterns

1. **EvidenceCandidate boundary schema** — A clean boundary type between retrieval and pipeline consumers, hiding internal ranking details while exposing needed context (source_table, score, rank). Reusable for any RAG system that needs to separate retrieval internals from downstream use.
2. **Query builder with intent/risk expansion** — Intent-derived and risk-derived business term expansion improves recall without requiring a query rewriter. The pattern of appending domain-specific terms to the query is reusable.
3. **`retrieve_evidence()` thin wrapper** — A composition wrapper that chains query -> retrieval -> mapping without modifying any component. Demonstrates how to integrate an independently tested subsystem without coupling.
4. **Immutable flag propagation** — The `_with_added_risk_flag()` pattern prevents subtle bugs from set mutation. Reusable in any pipeline where multiple stages may add flags to a shared set.
5. **Graceful degradation in isolation** — Each pipeline stage wrapped in its own try/except. Stage failures are isolated and produce degraded output rather than crashing the pipeline.
