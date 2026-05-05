# Phase 9 Wrong Case Comparison — Phase 8 vs Phase 9

*Generated at 2026-05-05*

## Summary

| Metric | Phase 8 (95 records) | Phase 9 (106 records) | Change |
|--------|---------------------|----------------------|--------|
| Wrong cases | 41 of 101 (40.6%) | 41 of 101 (40.6%) | **0** |
| Failure mode | `missing_doc_type` | `missing_doc_type` | — |
| Unique wrong cases | 41 | 41 | — |
| Fixed | — | 0 | — |
| Regressed | — | 0 | — |

## Key Finding

The 11 P0 knowledge records added in Phase 9.4.1 **did not fix any wrong case** and **did not
introduce any new wrong case**. The wrong case set is identical between phases.

### Why no fix?

The added P0 records fill specific knowledge gaps identified in the gap analysis (see
`phase9_knowledge_gap_map.md` and `phase9_wrong_case_taxonomy.md`). However, the fake embedding
provider (deterministic random) cannot leverage the semantic content of new documents — it
generates embeddings independent of document meaning. The new records simply shift the vector
space without improving the relevance of retrieved results.

### Impact of real embeddings

The wrong case count (41) is driven by knowledge base coverage gaps, not embedding quality.
A real embedding provider would improve ranking (Top-1, MRR) within correct cases but would not
eliminate wrong cases until the knowledge base specifically covers the missing scenarios.

## Detailed Case Analysis

All 41 wrong cases are identical between Phase 8 and Phase 9. See `reports/retrieval/wrong_cases.md`
for the full categorized analysis.

### Intent Distribution (unchanged)

| Intent | Wrong Cases | Total | % Wrong |
|--------|-------------|-------|---------|
| complaint | 10 | 13 | 77% |
| refund | 8 | 16 | 50% |
| return | 5 | 11 | 45% |
| account | 5 | 15 | 33% |
| logistics | 4 | 11 | 36% |
| other | 4 | 13 | 31% |
| edge | 5 | 5 | 100% |

### Failure Categories (unchanged)

1. **Empty retrieval**: 4 cases (edge_002–005) — same in both phases
2. **Missing expected doc types**: 37 cases — same in both phases
3. **Below top 10**: 0 cases — same in both phases

## Next Steps

1. **Real embedding provider evaluation** — repeat this comparison with a production embedding
   provider (e.g., text-embedding-v4) to measure the actual impact of knowledge expansion.
2. **Pipeline-level triage for edge cases** — the 4 empty-retrieval cases are pipeline issues,
   not knowledge coverage issues.
3. **Doc-level golden labels** — enable doc_id Recall@K to differentiate "missing doc type" from
   "wrong specific document."
