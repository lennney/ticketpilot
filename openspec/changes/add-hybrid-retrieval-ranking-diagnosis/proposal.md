# Proposal: Hybrid Retrieval Ranking Diagnosis (Phase 10)

## Executive Summary

Phase 9 proved that real embedding (DashScope text-embedding-v4, 1024-d) can leverage
added knowledge records: P0 added-record hit rate improved from 18.8% (fake) to 75.0%
(real), Top-1 hit rate rose +2.0%. However, **wrong cases remained 41** — zero net
reduction despite the P0 records reaching the retrieval candidate pool.

This means the bottleneck has shifted from **knowledge coverage** (Phase 9's target)
to **ranking/fusion**: the added records are recalled by one or both retrievers but
either (a) don't reach the fused Top-10, or (b) reach Top-10 but don't satisfy the
current metric's doc_type-level matching criteria.

Phase 10 opens a **trace-first diagnosis** of the hybrid retrieval ranking pipeline,
without changing any retrieval algorithm, RRF parameters, or embedding provider.
The goal is to classify every P0-related wrong case into exactly which layer of the
pipeline is failing:

- keyword recall
- vector recall
- RRF fusion ranking
- final evidence candidate selection
- doc_type vs doc_id label granularity
- query expansion

Only after diagnosis will we decide whether the next step is doc-level labels,
query expansion tuning, RRF parameter adjustment, reranker introduction, or
acceptance of remaining wrong cases as a limitation.

No Phase 7/8/9 baseline reports modified. No retrieval algorithm changes in
diagnosis phase. No knowledge records added.

## Baseline (Current State after Phase 9)

### Phase 9 Real Provider Results
| Metric | Phase 8 (95) | Phase 9 (106) | Delta |
|---:|---:|---:|---:|
| Top-1 hit rate | 42.6% | 44.6% | +2.0% |
| Top-3 hit rate | 56.4% | 55.4% | -1.0% |
| Top-5 hit rate | 58.4% | 59.4% | +1.0% |
| Top-10 hit rate | 59.4% | 59.4% | 0.0% |
| MRR | 0.4913 | 0.4995 | +0.0082 |
| Wrong cases | 41 | 41 | 0 |

### P0 Added-Record Hit Audit (Real Provider)
- **12/16 (75.0%)** P0 records appeared in at least one retrieval query
- 4/16 missed entirely

### Key Insight
P0 records are recalled at 75% under real embeddings, but 41 wrong cases persist.
**The remaining bottleneck is ranking/fusion, not knowledge coverage.**

## Problem

Phase 9 real provider evaluation revealed a structural bottleneck shift:

1. **Knowledge coverage was not the ceiling for 75% of P0 cases.** Added records
   are recalled, but wrong cases still don't improve.

2. **Current trace infrastructure is rich but unused for diagnosis.** The
   `RetrievalTrace` already captures keyword/vector/fused per-ranker results
   with ranks and RRF contributions, but no diagnostic report systematically
   inspects them per wrong case.

3. **No per-case layered inspection exists.** Current reports show aggregate
   metrics (Top-K hit rate, MRR) and final wrong-case classification, but
   cannot answer: "For case X, did the P0 record show up in keyword results?
   Vector results? Did it get fused but rank 11-20? Or was it absent from both?"

4. **Root cause of remaining 41 wrong cases is unknown.** They could be:
   - Keyword recall failures (query doesn't match the content)
   - Vector recall failures (embedding doesn't capture relevance)
   - RRF fusion ranking failures (recalled but ranked below Top-10)
   - Metric granularity failures (right doc type, right content, but labeled wrong)
   - Doc-level label absence (can't distinguish right doc from wrong doc of same type)

## Goal

1. **Per-case layered trace diagnosis**: For every P0-related wrong case, inspect
   keyword results, vector results, fused rankings, and final candidates.

2. **P0 added-record rank tracking**: For each P0 record (11 new in Phase 9),
   determine its best rank across keyword, vector, and fused results for every
   related case.

3. **Bottleneck classification**: Classify each P0 case into a fixed taxonomy:
   `keyword_not_recalled`, `vector_not_recalled`, `recalled_but_fused_low`,
   `fused_top10_but_metric_still_wrong`, `doc_level_label_missing`,
   `query_expansion_gap`, `empty_retrieval`, `provider_identity_issue`.

4. **Recommendation report**: Based on diagnosis, recommend whether the next step
   should be:
   - Add doc-level golden labels
   - Adjust query expansion
   - Tune RRF k / fusion weights
   - Add reranker
   - Leave as limitation

5. **No retrieval algorithm changes**: Diagnosis only. Implementation of any
   recommendation is deferred to a future phase.

## Non-Goals

- ❌ Not building a production-ready system
- ❌ Not using real enterprise customer data
- ❌ Not running online A/B tests
- ❌ Not auto-sending customer replies
- ❌ Not replacing human agents with AI
- ❌ Not tuning RRF k or keyword/vector weights
- ❌ Not adding knowledge records
- ❌ Not changing golden labels
- ❌ Not rebuilding embeddings
- ❌ Not changing the embedding model
- ❌ Not restructuring chunking architecture
- ❌ Not modifying Phase 7/8/9 baseline reports
- ❌ Not implementing a reranker
- ❌ Not changing the retrieval pipeline code

## Scope

### In Scope
- Trace schema review and gap identification
- Per-case P0 layered trace export (keyword / vector / fused / final)
- P0 added-record per-case rank tracking
- Bottleneck classification for each P0-related wrong case
- Provider-aware trace reports (distinguish fake vs real diagnosis)
- Recommendation report for next-step direction
- Portfolio delta (compact, after diagnosis findings)

### Out of Scope
- Retrieval algorithm changes
- RRF parameter tuning
- Query expansion changes
- Golden label additions
- Knowledge base expansion
- Embedding provider changes
- Embedding rebuilds
- New evaluation metrics

## Success Criteria

1. Every P0-related case has a layered trace report showing keyword/vector/fused/final
   candidate status for expected evidence
2. Every P0 added record has best-rank status across keyword/vector/fused per relevant case
3. Each P0 case is classified into exactly one bottleneck category from the fixed taxonomy
4. No baseline report overwritten
5. No retrieval algorithm changed during diagnosis
6. OpenSpec scoped validation passes
7. If later implementation touches retrieval/evaluation code, full quality gate required
8. Integration skipped must remain 0 for archive/pre-push

## Risks

| Risk | Mitigation |
|---|---|
| Diagnosis reveals issues that can't be fixed without major refactor | Categorize as `limitation`; document clearly |
| Fake provider can't diagnose semantic ranking | Require real provider for ranking conclusions; fake only for pipeline mechanics |
| Trace data voluminous for 101 cases × multiple P0 records | Focus on P0-related cases only (~16 cases); automate via script |
| Recommendation pressure to "just fix it" | Explicitly defer all implementation to future phase; diagnosis-only scope |
| Accidentally modifying Phase 8/9 baseline | Phase 8/9 reports are immutable; Phase 10 creates new namespaced outputs |

## Validation Plan

| Stage | Validation | Notes |
|---|---|---|
| Planning (current batch) | `openspec validate add-hybrid-retrieval-ranking-diagnosis --strict` | Scoped |
| Diagnosis implementation | Module-level tests for any new trace analysis code | No retrieval algorithm changes |
| Pre-output | Verify no Phase 7/8/9 reports modified; reports namespaced |
| Pre-archive | Full quality gate + integration 0 skip |
