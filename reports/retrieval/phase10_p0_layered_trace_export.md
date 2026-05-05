# Phase 10.3 — P0 Layered Trace Export

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*
*OpenSpec Change: add-hybrid-retrieval-ranking-diagnosis*

> **Boundary statement:**
> - Export-only deliverable. No retrieval algorithm, RRF parameters, query builder,
>   embedding provider, knowledge base, or golden labels modified.
> - Export script change: added full `keyword_results`, `vector_results`, `fused_results`,
>   `final_evidence_ids` serialization to `scripts/run_retrieval_comparison.py` — minimal
>   reporting field addition, no pipeline behavior changes.
> - Dedicated P0 export script: `scripts/export_p0_layered_trace.py` — processes 14 P0-related
>   cases only, cross-references P0 record doc_ids against each trace layer.
> - Real provider used: `OpenAICompatibleEmbeddingProvider` (1024-d) — semantic ranking
>   conclusions are valid. See Limitations section for scope caveats.

---

## 1. Scope

Phase 10.3 performs a **layered trace export** for the 14 P0-related wrong cases (16 record-case pairs) from Phase 9.4.1 knowledge expansion. For each case, the pipeline was re-run with the real embedding provider and full `RetrievalTrace` was serialized per case.

**What was NOT done:**
- No retrieval algorithm changes
- No RRF parameter tuning
- No query expansion changes
- No knowledge base additions
- No golden label modifications
- No embedding provider changes

**What was added:**
- `scripts/run_retrieval_comparison.py`: export mode now includes `chunk_id` in `retrieved_docs`, plus full `keyword_results`, `vector_results`, `fused_results`, `final_evidence_ids` in trace output
- `scripts/export_p0_layered_trace.py`: new script targeting 14 P0-related cases with layered cross-reference
- `reports/retrieval/phase10_p0_layered_traces.json`: structured trace export (14 cases, 16 P0 record-case pairs)

---

## 2. P0 Case Trace Table

| Case ID | Related Added Record(s) | Expected Doc Types | Keyword Hit? | Vector Hit? | Fused Hit? | Final Top-10 Hit? | Best Layer | Best Rank | Notes |
|---|---|---|---|---|---|---|---|---|---|
| case_retu_004 | f0f0f0f0-2222 (FAQ) | Policy, Case | N | Y | Y | Y | vector | 1 | FAQ record vector rank 1, fused rank 5 |
| case_refu_001 | ae0e0e0e-aaaa (POLICY) | Policy, Case | Y(9) | Y(2) | Y(3) | Y(3) | vector | 2 | Keyword also hit at rank 9 |
| case_refu_006 | ae0e0e0e-aaaa (POLICY) | Policy, Case | Y(9) | Y(2) | Y(3) | Y(3) | vector | 2 | Same record as refu_001, similar pattern |
| case_acco_003 | ae0e0e0e-bbbb (POLICY) | Policy, Case | N | Y(5) | Y(5) | Y(5) | vector | 5 | Privacy policy in fused top-5 |
| case_acco_003 | ca0a0a0a-aaaa (CASE) | Policy, Case | N | Y(2) | Y(2) | Y(2) | vector | 2 | Privacy case even better |
| case_acco_006 | ae0e0e0e-bbbb (POLICY) | Policy, Case | N | Y(11) | N | N | vector | 11 | Vector rank 11 too low for fused top-10 |
| case_acco_012 | ae0e0e0e-bbbb (POLICY) | Policy, Case | N | Y(4) | Y(4) | Y(4) | vector | 4 | Privacy policy at rank 4 |
| case_refu_013 | ae0e0e0e-cccc (POLICY) | Policy, Case | N | N | N | N | — | — | **Complete miss** — counterfeit policy not recalled by either ranker |
| case_refu_013 | ca0a0a0a-6666 (CASE) | Policy, Case | Y(5) | Y(3) | Y(2) | Y(2) | vector | 2 | Counterfeit case reaches rank 2, but Policy missing |
| case_refu_009 | ae0e0e0e-dddd (POLICY) | Policy, Case | Y(1) | Y(3) | Y(1) | Y(1) | keyword | 1 | Policy found by both rankers, fused rank 1 |
| case_comp_001 | ca0a0a0a-5555 (CASE) | Case | N | Y(3) | N | N | vector | 3 | Vector rank 3 but **pushed out of fused top-10** by dual-contribution items |
| case_comp_002 | ca0a0a0a-6666 (CASE) | Policy, Case | N | Y(2) | N | N | vector | 2 | Vector rank 2 but **pushed out of fused top-10** |
| case_comp_003 | ca0a0a0a-7777 (CASE) | Policy, Case | N | Y(2) | Y(2) | Y(2) | vector | 2 | Promotion case at fused rank 2 |
| case_comp_008 | ca0a0a0a-8888 (CASE) | Case | N | Y(1) | Y(1) | Y(1) | vector | 1 | After-sales case vector rank 1 — **perfect recall** |
| case_comp_004 | ca0a0a0a-9999 (CASE) | Policy, Case | Y(6) | Y(5) | Y(4) | Y(4) | vector | 4 | Keyword also contributed |
| case_comp_009 | ca0a0a0a-9999 (CASE) | Policy, Case | N | Y(3) | Y(5) | Y(5) | vector | 3 | Same record as comp_004, different query |

### Layer Hit Summary (16 pairs)

| Layer | Hits | Hit Rate |
|---|---|---|
| Keyword (FTS + LIKE) | 5/16 | 31.2% |
| Vector (HNSW, OpenAI-compatible) | 15/16 | 93.8% |
| Fused top-10 (RRF k=60) | 12/16 | 75.0% |
| Final evidence candidates | 12/16 | 75.0% |

**Key finding:** Vector recall is excellent (93.8%) with the real provider. The main loss happens between vector recall and fused top-10 (93.8% → 75.0%), caused by P0 records being recalled by vector only, losing RRF competition to items found by both rankers.

---

## 3. Added Record Layer Table

| Added Record ID | Doc Type | Related Cases | Keyword Best Rank | Vector Best Rank | Fused Best Rank | Final Evidence Rank | Interpretation |
|---|---|---|---|---|---|---|---|
| f0f0f0f0-2222-2222-2222-222222222222 | FAQ | retu_004 | — | 1 | 5 | 5 | Strong vector recall; fused rank 5 is adequate |
| ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa | POLICY | refu_001, refu_006 | 9 | 2 | 3 | 3 | Good cross-ranker recall; reaches final for both cases |
| ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb | POLICY | acco_003, acco_006, acco_012 | — | 4–11 | 4–5 (miss in acco_006) | 4–5 | **Mixed**: good for 2/3 cases, fails for acco_006 (vector rank 11) |
| ae0e0e0e-cccc-cccc-cccc-cccccccccccc | POLICY | refu_013 | — | — | — | — | **Complete miss** by both rankers |
| ae0e0e0e-dddd-dddd-dddd-dddddddddddd | POLICY | refu_009 | 1 | 3 | 1 | 1 | Excellent recall by both rankers |
| ca0a0a0a-5555-5555-5555-555555555555 | CASE | comp_001 | — | 3 | — | — | Vector rank 3 but **fused loss** — pushed out by dual-contribution items |
| ca0a0a0a-6666-6666-6666-666666666666 | CASE | comp_002, refu_013 | 5 | 2–3 | 2 (refu_013 only) | 2 | **Mixed**: reaches final for refu_013, fused loss for comp_002 |
| ca0a0a0a-7777-7777-7777-777777777777 | CASE | comp_003 | — | 2 | 2 | 2 | Good vector recall and fusion |
| ca0a0a0a-8888-8888-8888-888888888888 | CASE | comp_008 | — | 1 | 1 | 1 | **Perfect recall** — best case |
| ca0a0a0a-9999-9999-9999-999999999999 | CASE | comp_004, comp_009 | 6 | 3–5 | 4–5 | 4–5 | Good recall by both rankers; reaches final for both |
| ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa | CASE | acco_003 | — | 2 | 2 | 2 | Good vector recall and fusion |

---

## 4. Layer-Level Findings

### 4.1 Are P0 records mainly recalled by vector?

**Yes.** 15/16 (93.8%) of P0 record-case pairs are recalled by vector search with the real embedding provider. This confirms:
- The real provider (OpenAI-compatible, 1024-d) produces semantically meaningful embeddings that match P0 record content to their target queries
- Vector search (pgvector HNSW) works as expected

### 4.2 Is keyword contribution insufficient?

**Yes, this is a major finding.** Only 5/16 (31.2%) of P0 records are found by keyword search (PostgreSQL FTS + LIKE). This means:
- P0 records that only exist in vector results get a single RRF contribution of `1/(60 + vector_rank)`
- Items found by both keyword and vector get `1/(60 + keyword_rank) + 1/(60 + vector_rank)` — roughly double the score
- This creates an RRF bias toward items that match query keywords, even if semantically less relevant

**Impact on P0 cases:** 3 records (ca0a0a0a-5555 in comp_001, ca0a0a0a-6666 in comp_002, ae0e0e0e-bbbb in acco_006) had good vector ranks (2–11) but were pushed out of fused top-10 because they lacked keyword contributions. These are **recalled_but_fused_low** cases.

### 4.3 Does fused ranking suppress P0 records?

**Yes, for 3/16 cases (18.8%).** The RRF fusion with k=60:
- Favors "dual-source" items (found by both keyword and vector)
- Penalizes "vector-only" items, even when vector rank is excellent (e.g., vector rank 2 in comp_002)
- This is a known RRF property — it prefers broad agreement over single-ranker depth

### 4.4 Do final evidence candidates lose fused results?

**No.** In all 12 cases where a P0 record reached fused top-10, it also reached final evidence candidates. The final evidence selection faithfully preserves the fused top-10 ranking.

### 4.5 Why do wrong cases remain despite P0 records in final evidence?

**This is the most important finding.** 12/16 (75%) of record-case pairs that reached final evidence still result in a "wrong case" classification. Why?

Because the **evaluation metric checks doc_type-level coverage**, not doc_id-level. Each case expects specific doc types (e.g., `Case + Policy`). Adding one P0 record only addresses ONE of the expected types. The case remains wrong because the other expected doc type is still absent from retrieved docs.

**Example:** case_refu_009 expects both `Policy` and `Case`. The P0 record `ae0e0e0e-dddd` (POLICY) reaches final rank 1 — perfect. But no `Case` doc type is in the Top-10, so the case is still wrong.

This means: **wrong cases remaining after Phase 9 is not primarily a retrieval quality problem — it's a metric granularity problem.** The doc_type-level hit rate cannot distinguish between "right doc retrieved" and "right doc_type, wrong doc retrieved."

---

## 5. Limitations

- **No doc-level golden labels**: The current golden file (`golden_expectations.csv`) only specifies `expected_evidence_doc_types` (e.g., "Policy;Case"). There are no `expected_relevant_doc_ids` for these P0 cases, so we cannot compute doc-level MRR or recall@K for P0 records.
- **RRF contribution field available**: The `FusedResult` schema does include `keyword_contribution` and `vector_contribution` fields, confirming RRF score breakdowns are available.
- **Single provider only**: Results reflect the OpenAI-compatible embedding provider (1024-d). Different providers may produce different recall patterns.
- **101 eval tickets only**: All conclusions are limited to the 101 synthetic eval tickets and 106 synthetic knowledge records. Not a production benchmark.
- **No query expansion analysis**: Manual review of query vs. record content gaps (query_expansion_gap) was not performed in this phase.
- **Case still wrong ≠ P0 record ineffective**: A case remaining wrong does not mean the P0 record was useless — it means the expected doc_type coverage is incomplete.

---

## 6. Raw Export Data

Structured trace data (14 cases, 16 record-case pairs) with keyword_results, vector_results, fused_results, final_evidence_ids, and P0 cross-references:

`reports/retrieval/phase10_p0_layered_traces.json`
