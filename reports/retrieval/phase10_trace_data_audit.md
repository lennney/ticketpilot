# Phase 10.2 — Trace Data Audit

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*
*OpenSpec Change: add-hybrid-retrieval-ranking-diagnosis*

> **Boundary statement:**
> - This is an audit-only deliverable. No retrieval algorithm, RRF parameters,
>   query builder, embedding provider, knowledge base, or golden labels modified.
> - No src/ or tests/ files changed.
> - No Phase 7/8/9 baseline reports modified.

---

## 1. Current Trace Schema

### RetrievalTrace (src/ticketpilot/retrieval/traces.py)

| Field | Present? | Source Object/File | Example / Notes | Enough for Phase 10? |
|---|---|---|---|---|
| `keyword_results` | ✅ | `RetrievalTrace.keyword_results: list[KeywordResult]` | chunk_id, doc_id, doc_type, content, score, rank, search_method, fts_rank, like_rank | **Yes** — full per-ranker data |
| `vector_results` | ✅ | `RetrievalTrace.vector_results: list[VectorResult]` | chunk_id, doc_id, doc_type, content, score, rank, embedding_provider | **Yes** — full per-ranker data |
| `fused_results` | ✅ | `RetrievalTrace.fused_results: list[FusedResult]` | chunk_id, doc_id, doc_type, content, rrf_score, keyword_rank, keyword_contribution, vector_rank, vector_contribution, sources | **Yes** — full RBF contribution |
| `final_evidence_ids` | ✅ | `RetrievalTrace.final_evidence_ids: list[UUID]` | Chunk IDs of top-k fused results | **Yes** — needed for "did it reach final candidates" |
| `doc_id` | ✅ | `KeywordResult.doc_id`, `VectorResult.doc_id`, `FusedResult.doc_id` | UUID | **Yes** — needed for P0 record cross-reference |
| `chunk_id` | ✅ | All result types | UUID | **Yes** — primary key for cross-layer lookup |
| `doc_type` | ✅ | All result types | `FAQ`/`POLICY`/`CASE` | **Yes** |
| `source_table` | ❌ | Not in trace | e.g., `knowledge_faq` | **No** — can derive from doc_type or chunk_id |
| `source_id` | ❌ | Not in trace | FK to source table | **No** — `doc_id` serves the same purpose |
| `rank` | ✅ | `KeywordResult.rank`, `VectorResult.rank`, `FusedResult` has keyword_rank/vector_rank | 1-based | **Yes** |
| `score` | ✅ | `KeywordResult.score`, `VectorResult.score` | ts_rank / cosine similarity | **Yes** |
| `keyword_score` | ✅ | `KeywordResult.score` | ts_rank float | **Yes** |
| `vector_score` | ✅ | `VectorResult.score` | cosine similarity in [0,1] | **Yes** |
| `rrf_score` | ✅ | `FusedResult.rrf_score` | Sum of 1/(k+rank) contributions | **Yes** |
| `keyword_contribution` | ✅ | `FusedResult.keyword_contribution` | 1/(60 + keyword_rank) | **Yes** |
| `vector_contribution` | ✅ | `FusedResult.vector_contribution` | 1/(60 + vector_rank) | **Yes** |
| `sources` | ✅ | `FusedResult.sources` | `["keyword"]`, `["vector"]`, or `["keyword", "vector"]` | **Yes** — needed for "which ranker found it?" |
| `embedding_provider` | ✅ | `RetrievalTrace.embedding_provider`, `VectorResult.embedding_provider` | `"fake"` or `"openai_compatible"` | **Yes** |
| `keyword_latency_ms` | ✅ | `RetrievalTrace.keyword_latency_ms` | integer ms | **Yes** |
| `vector_latency_ms` | ✅ | `RetrievalTrace.vector_latency_ms` | integer ms | **Yes** |
| `fusion_latency_ms` | ✅ | `RetrievalTrace.fusion_latency_ms` | integer ms | **Yes** |
| `total_latency_ms` | ✅ | `RetrievalTrace.total_latency_ms` | integer ms | **Yes** |
| `rrf_k` | ✅ | `RetrievalTrace.rrf_k` | default 60 | **Yes** |
| `top_k` | ✅ | `RetrievalTrace.top_k` | default 10 | **Yes** |
| `hnsw_params` | ✅ | `RetrievalTrace.hnsw_params` | `{"m": 16, "ef_construction": 200, "ef_search": 100}` | **Yes** |
| `keyword_search_method` | ✅ | `RetrievalTrace.keyword_search_method` | `"fts"` or `"fts+like"` | **Yes** |
| `content` | ✅ | All result types | Full text content | **Yes** |
| `query_embedding` | ✅ | `RetrievalTrace.query_embedding` | list[float] | — Not needed for diagnosis |

### Current Export Format (scripts/run_retrieval_comparison.py)

The export script at `run_retrieval_comparison.py:269-278` currently captures:

| Export Field | Present? | Details |
|---|---|---|
| `retrieved_docs` (fused final) | ✅ | doc_id, doc_type, rank, score — **fused only, no per-ranker** |
| `retrieval_trace.keyword_count` | ✅ | Integer count only |
| `retrieval_trace.vector_count` | ✅ | Integer count only |
| `retrieval_trace.fused_count` | ✅ | Integer count only |
| `retrieval_trace.total_latency_ms` | ✅ | Integer ms |
| `retrieval_trace.embedding_provider` | ✅ | Provider name |
| `keyword_results` (per-ranker) | ❌ | **Not exported** |
| `vector_results` (per-ranker) | ❌ | **Not exported** |
| `fused_results` (with RRF contributions) | ❌ | **Not exported** |
| `final_evidence_ids` | ❌ | **Not exported** |

---

## 2. Layered Diagnosis Readiness

### Can we answer these questions for Phase 10.3?

| Question | At Runtime? | In Exported Rows? | Phase 10.3 Action |
|---|---|---|---|
| P0 record in keyword results? | ✅ Yes — `trace.keyword_results` | ❌ Currently no | Export keyword_results per case |
| P0 record in vector results? | ✅ Yes — `trace.vector_results` | ❌ Currently no | Export vector_results per case |
| P0 record in fused top-N? | ✅ Yes — `trace.fused_results` | ~ Partial (`retrieved_docs` = fused, but without per-ranker breakout) | Export fused_results with full RRF details |
| P0 record in final evidence? | ✅ Yes — `trace.final_evidence_ids` | ❌ Currently no | Add final_evidence_ids to export |
| If absent from final Top-10, which layer? | ✅ Yes — full trace available | ❌ Currently no | Add layered cross-reference to export |
| Fake vs real provider distinguishable? | ✅ Yes — `trace.embedding_provider` | ✅ Yes — already exported | No change needed |
| P0 record best rank per retriever? | ✅ Computable from trace | ❌ Currently no | Compute from full trace export |

**Key finding: The full trace data exists at runtime but is NOT serialized in the current export.**
The `RetrievalTrace` object passed through to `TicketOutput.retrieval_trace` already contains all
the data needed for layered diagnosis. The limitation is only in the export/query layer.

---

## 3. Trace Gaps

| Missing Field | Why Needed | Required for Phase 10.3? | Proposed Fix |
|---|---|---|---|
| `keyword_results` per case in export | Per-ranker diagnosis — check if P0 record recalled by FTS/LIKE | **Yes** — essential | Add `keyword_results` serialization to export script: each result as dict with chunk_id, doc_id, doc_type, score, rank, search_method |
| `vector_results` per case in export | Per-ranker diagnosis — check if P0 record recalled by HNSW | **Yes** — essential | Add `vector_results` serialization to export script: each result as dict with chunk_id, doc_id, doc_type, score, rank, embedding_provider |
| `fused_results` with RRF contributions per case in export | Per-ranker diagnosis — check if P0 record's fused rank shows both/one ranker contributed | **Yes** — essential | Add `fused_results` serialization to export script: each result with rrf_score, keyword_rank, keyword_contribution, vector_rank, vector_contribution, sources |
| `final_evidence_ids` in export | Verify final evidence selection matches fused top-k | **Yes** — useful | Add to export: list of final UUIDs |
| `chunk_id` in retrieved_docs export | Cross-reference individual P0 chunk_ids across layers | **Yes** | Currently only `doc_id` is in `retrieved_docs`. Add `chunk_id` to each retrieved_doc entry |
| Doc-level golden labels (`expected_relevant_doc_ids`) | Distinguish "right doc, wrong label" from "doc not retrieved" | **No** for Phase 10 trace export; **Yes** for Phase 10.4 bottleneck classification | Add doc_id labels to golden_expectations.csv for P0-related cases |
| `query` in trace | Diagnostic review of whether query expansion matches record content | Not a gap — query is already in trace | Already available |

**Important:** None of these gaps require changes to the retrieval pipeline, RRF, query builder,
or embedding provider. They are **new export/serialization logic only** — a new script or
modification to the existing export mode in `run_retrieval_comparison.py`.

---

## 4. P0 Case Coverage

Based on `reports/retrieval/phase9_p0_knowledge_expansion_summary.md` and
`reports/retrieval/phase9_p0_added_record_hit_audit.md`, the following cases and
P0 records should be included in Phase 10.3 layered trace export.

### P0 Records (11 new in Phase 9.4.1)

| Record ID | Type | Gap ID | Business Domain |
|---|---|---|---|
| `f0f0f0f0-2222-2222-2222-222222222222` | FAQ | KG-FAQ-003 | return_exchange |
| `ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa` | POLICY | KG-POL-001 | refund (escalation) |
| `ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb` | POLICY | KG-POL-003 | account (privacy) |
| `ae0e0e0e-cccc-cccc-cccc-cccccccccccc` | POLICY | KG-POL-002 | refund (counterfeit) |
| `ae0e0e0e-dddd-dddd-dddd-dddddddddddd` | POLICY | KG-POL-005 | refund (legal threat) |
| `ca0a0a0a-5555-5555-5555-555555555555` | CASE | KG-CASE-001 | complaint (agent attitude) |
| `ca0a0a0a-6666-6666-6666-666666666666` | CASE | KG-CASE-002 | complaint (counterfeit) |
| `ca0a0a0a-7777-7777-7777-777777777777` | CASE | KG-CASE-003 | complaint (promotion) |
| `ca0a0a0a-8888-8888-8888-888888888888` | CASE | KG-CASE-006 | complaint (after-sales) |
| `ca0a0a0a-9999-9999-9999-999999999999` | CASE | KG-RISK-001 | complaint (legal threat) |
| `ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa` | CASE | KG-RISK-003 | account (privacy) |

### P0-Related Cases (16 records-case pairs across 15 unique cases)

| Case ID | Added Record ID(s) | Domain | Record Type(s) | Export Trace? |
|---|---|---|---|---|
| `case_retu_004` | `f0f0f0f0-2222-...` | return_exchange | FAQ | ✅ Yes |
| `case_refu_001` | `ae0e0e0e-aaaa-...` | refund | POLICY | ✅ Yes |
| `case_refu_006` | `ae0e0e0e-aaaa-...` | refund | POLICY | ✅ Yes |
| `case_acco_003` | `ae0e0e0e-bbbb-...`, `ca0a0a0a-aaaa-...` | account | POLICY + CASE | ✅ Yes (2 records) |
| `case_acco_006` | `ae0e0e0e-bbbb-...` | account | POLICY | ✅ Yes |
| `case_acco_012` | `ae0e0e0e-bbbb-...` | account | POLICY | ✅ Yes |
| `case_refu_013` | `ae0e0e0e-cccc-...`, `ca0a0a0a-6666-...` | refund | POLICY + CASE | ✅ Yes (2 records) |
| `case_refu_009` | `ae0e0e0e-dddd-...` | refund | POLICY | ✅ Yes |
| `case_comp_001` | `ca0a0a0a-5555-...` | complaint | CASE | ✅ Yes |
| `case_comp_002` | `ca0a0a0a-6666-...` | complaint | CASE | ✅ Yes |
| `case_comp_003` | `ca0a0a0a-7777-...` | complaint | CASE | ✅ Yes |
| `case_comp_008` | `ca0a0a0a-8888-...` | complaint | CASE | ✅ Yes |
| `case_comp_004` | `ca0a0a0a-9999-...` | complaint | CASE | ✅ Yes |
| `case_comp_009` | `ca0a0a0a-9999-...` | complaint | CASE | ✅ Yes |

**Total: 15 unique cases, 16 record-case pairs (2 cases have both P0 POLICY and CASE)**

These cases are a subset of the 41 wrong cases. The export can be limited to these 15 cases
for Phase 10.3, reducing export runtime and analysis scope while covering all P0 records.

---

## 5. Recommendation

### Phase 10.3 Readiness

**✅ Ready to proceed — with minimal export work.**

The `RetrievalTrace` object at runtime already contains all the data needed for layered
diagnosis. The only gap is in serialization: the current export in `run_retrieval_comparison.py`
only exports fused results (without RRF contribution breakouts) and trace metadata counts.

Phase 10.3 should:
1. Extend the export script to serialize full `keyword_results`, `vector_results`,
   `fused_results`, and `final_evidence_ids` per case
2. Add `chunk_id` to the `retrieved_docs` export entries
3. Add a cross-reference that computes per-P0-chunk best rank across all three layers
4. Run the export on the 15 P0-related cases using the real embedding provider
5. Output to `reports/retrieval/phase10_p0_layered_traces.json`

### What Phase 10.3 Does NOT Need
- No changes to retrieval pipeline, RRF, query builder, or embedding provider
- No new golden labels (doc-level labels can be a future read)
- No DB schema changes
- No new tests

### Validation Requirements
- No full quality gate needed if only export script is modified (scoped change)
- Existing tests must still pass
- Secret scan still required (no API keys in export)

---

## 6. Boundary

- **Audit-only**: No retrieval algorithm, RRF, query builder, or embedding provider changes
- **No baseline overwrite**: Phase 10 outputs go to `reports/retrieval/phase10_*`
- **No production benchmark claim**: Diagnosis is based on synthetic/seed data and 101 eval tickets
- **No real customer data**: All traces derived from synthetic eval tickets and synthetic knowledge base
- **Provider identity preserved**: Every export declares the embedding provider used; fake provider
  traces carry a disclaimer that semantic ranking conclusions are invalid
- **Not tuning**: No parameter changes based on diagnosis (recommendations only)
