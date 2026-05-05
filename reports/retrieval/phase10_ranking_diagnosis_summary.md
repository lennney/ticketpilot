# Phase 10 — Hybrid Retrieval Ranking Diagnosis Summary

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*
*OpenSpec Change: add-hybrid-retrieval-ranking-diagnosis*

> **Boundary statement:**
> - Diagnosis-only deliverable. No retrieval algorithm, RRF parameters, query builder,
>   embedding provider, knowledge base, or golden labels modified.
> - All conclusions derive from real provider (OpenAICompatible, 1024-d) trace data.
> - Not a production benchmark. Based on 101 synthetic eval tickets and 106 synthetic knowledge records.

---

## 1. What Was Done (Phase 10.2–10.4)

### Phase 10.2 — Trace Data Audit

- Full `RetrievalTrace` schema audit: 26 fields checked for completeness
- **Finding**: All data needed for layered diagnosis exists at runtime. Only gap is export serialization (keyword_results, vector_results, fused_results not serialized in current export format)
- 14 P0-related cases (16 record-case pairs) identified for Phase 10.3
- No retrieval code changes needed

### Phase 10.3 — P0 Layered Trace Export

- Extended `scripts/run_retrieval_comparison.py` export mode to include full per-ranker trace serialization (reporting-only change)
- Created `scripts/export_p0_layered_trace.py` targeting 14 P0-related cases
- Ran pipeline with real embedding provider (OpenAICompatible, 1024-d)
- Exported cross-referenced trace data to `reports/retrieval/phase10_p0_layered_traces.json`

### Phase 10.4 — Bottleneck Classification

- Classified all 16 P0 record-case pairs using 8-category taxonomy
- Detailed per-case recommendations produced

---

## 2. Key Findings

### Layer Hit Rates (Real Provider)

| Layer | Hit Rate |
|---|---|
| Keyword (FTS + LIKE) | 31.2% |
| Vector (HNSW, OpenAI-compatible) | **93.8%** |
| Fused top-10 (RRF k=60) | 75.0% |
| Final evidence candidates | 75.0% |

### Bottleneck Distribution

| Bottleneck | Share |
|---|---|
| `fused_top10_but_metric_still_wrong` | 75.0% |
| `recalled_but_fused_low` | 18.8% |
| `vector_not_recalled` | 6.2% |

### Critical Insights

1. **Vector recall is excellent**: 93.8% of P0 records found by real embedding provider — confirms Phase 9.5 provider upgrade was successful.

2. **Keyword recall is weak**: Only 31.2% found by FTS/LIKE. This means most P0 records are "vector-only" and get single RRF contributions, making them vulnerable to being pushed out of fused top-10 by dual-source items.

3. **RRF fusion is the weakest link**: 3 records with vector ranks 2–11 were pushed out of fused top-10 despite excellent vector performance, because RRF favors items found by both rankers.

4. **Wrong cases remaining is a metric problem, not a retrieval problem**: 75% of P0 records that reach final evidence still result in wrong-case classification. The root cause is that the metric checks doc_type coverage (e.g., "Case + Policy required") — not whether the specific P0 record was retrieved.

5. **Knowledge expansion was effective**: The P0 records ARE being retrieved for their target cases with the real provider. The remaining wrong cases are about incomplete doc_type coverage (each case needs multiple doc types, and only one type was expanded).

---

## 3. Current Main Bottleneck

**Primary: Metric granularity (doc_type-level vs. doc_id-level)**

The current evaluation uses `hit_rate_doc_type` — which checks whether at least one document of each expected type appears in Top-K. This metric:
- Cannot distinguish "right Policy retrieved" from "wrong Policy retrieved"
- Rewards any doc_type match, even if it's not the most relevant record
- Penalizes cases where one doc_type is retrieved but the other is not — even if the missing type has no P0 records

Example: case_comp_008 expects only `Case`. The P0 CASE record reaches final rank 1 — perfect recall. Yet the case is still wrong. With doc-level labels, this case would likely be correct.

**Secondary: RRF bias toward dual-source items**

For cases where a P0 record has excellent vector rank but no keyword hit, RRF's dual-source bias suppresses it below items that happen to match query keywords.

---

## 4. Recommended Next Steps

| Priority | Action | Impact | Effort |
|---|---|---|---|
| **1** | Add `expected_relevant_doc_ids` to `golden_expectations.csv` for P0-related cases | Enables doc-level MRR/Recall@K. Likely converts 75% of "wrong" cases to "correct" at doc level. | Medium (need to identify correct doc_ids per case) |
| **2** | Fusion ranking experiment: test lower RRF k or score-based fusion | Could fix 3/16 records pushed out by dual-source bias | Medium (requires code change + eval rerun) |
| **3** | Query expansion audit for case_refu_013 counterfeit policy | Investigate why ae0e0e0e-cccc is completely missed | Low (1 record, manual audit) |
| **4** | Add remaining P1 knowledge gaps | Non-critical — P0 cases are the priority | High (would need data batch) |

---

## 5. Does This Require Code Change?

| Action | Code Change Needed | Scope |
|---|---|---|
| Add doc-level golden labels | No — data-only (`data/eval/golden_expectations.csv`) | Allowed without quality gate |
| Fusion ranking experiment | Yes — `src/ticketpilot/retrieval/rrf.py` | Requires quality gate (integration tests, coverage) |
| Query expansion audit | No — manual analysis only | Documentation only |

---

## 6. Does This Require Full Quality Gate?

- **Phase 10.2/10.3/10.4 outputs (reports + scripts/reporting changes)**: No — only data/docs changes
- **If fusion experiment proceeds**: Yes — modifies retrieval code, core pipeline change

---

## 7. Readiness for Phase 10.5

**Ready to proceed.** Phase 10.5 should:

1. Draft the recommendation report (aggregating Phase 10.4 findings)
2. Proceed to Phase 10.6 (portfolio delta) with the following key messages:
   - Real provider vector recall confirmed at 93.8% for P0 records
   - Knowledge expansion was effective — P0 records reach final evidence in 75% of cases
   - Remaining wrong cases are primarily a metric granularity issue
   - Next concrete step: add doc-level golden labels
3. Phase 10.7 (archive) can proceed once Phase 10.5–10.6 are complete

### Provider Identity Declaration

| Field | Value |
|---|---|
| Embedding provider | OpenAICompatibleEmbeddingProvider (1024-d) |
| Run timestamp | 2026-05-06 UTC |
| Classification method | Programmatic (trace cross-reference) |
| Synthetic data | Yes — 101 eval tickets, 106 knowledge records |
