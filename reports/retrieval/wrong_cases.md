# Wrong Case Analysis — Fake vs Real Embedding Provider

*Generated at 2026-05-04 UTC*

## Overview

Both fake and real embedding providers produce the same 41 wrong cases (40.6% of 101 total). All failures are classified as `missing_doc_type` — at least one expected document type is absent from the top 10 results.

## Key Finding

The real provider (text-embedding-v4, 1024-d) **does not reduce wrong case count** because the failures are driven by knowledge base content gaps, not embedding quality. Both providers search the same knowledge base; if the right document type isn't in the top 10 for a query, better embeddings can't fix it.

What the real provider *does* improve: ranking quality within the correct cases. Top-1 hit rate rises from 31.7% to 42.6% (+10.9%), and MRR from 0.4114 to 0.4913 (+0.0799).

## Distribution by Intent

| Intent | Wrong Cases | Total Cases | % of Intent |
|--------|-------------|-------------|-------------|
| complaint | 10 | 13 | 77% |
| refund | 8 | 16 | 50% |
| return | 5 | 11 | 45% |
| account | 5 | 15 | 33% |
| logistics | 4 | 11 | 36% |
| other | 4 | 13 | 31% |
| edge | 5 | 5 | 100% |

## Failure Categories

### 1. Empty Retrieval (4 cases)

These cases return zero retrieved documents — the query produced no results at all.

| Case ID | Expected Doc Types | Notes |
|---------|-------------------|-------|
| case_edge_002 | [Case, Policy] | Empty retrieval from DB |
| case_edge_003 | [] | Empty expected + empty retrieval |
| case_edge_004 | [] | Empty expected + empty retrieval |
| case_edge_005 | [] | Empty expected + empty retrieval |

Three of these (edge_003, edge_004, edge_005) have empty expected doc types in the golden file, so the "failure" is a data artifact rather than a retrieval problem.

### 2. Missing Expected Doc Types (37 cases)

These cases retrieve some documents but miss at least one expected type. Despite better ranking from the real provider, the same set of expected types is absent — the ranking improvements are within the doc types that *are* found.

Typical pattern: a case expects `[Case, Policy]` but the top 10 results contain only one of these (e.g., Policy but no Case), or contains the right types but with the wrong specific documents.

### 3. No `below_top_10` Failures

No case falls into the "right doc type found but below rank 10" category. This means: when the right doc type is found, it's always within the top 10.

## Why the Real Provider Doesn't Fix These

The real embedding provider improves query-document semantic matching, which helps rank relevant documents higher. However:

1. **Knowledge base coverage**: If the knowledge base has no Case documents resembling "account locked after 3 failed attempts", no embedding provider can produce one.
2. **Query-document gap**: The retrieval query is built from normalized text + intent + risk flags. Some queries may be poorly constructed (e.g., too short, missing keywords), and embeddings alone can't bridge a semantic gap that large.
3. **RRF fusion ceiling**: Hybrid retrieval (keyword + vector + RRF) caps at top 10. If the relevant document isn't in either the keyword or vector top-N lists, RRF can't fuse it in.

## Improvement Paths

1. **Knowledge base enrichment**: Add more Case and Policy documents covering the 41 failure scenarios.
2. **Query optimization**: Review `build_retrieval_query()` output for these 41 cases — are the queries underspecified?
3. **Golden data review**: The 4 edge cases with empty expected doc types suggest some golden labels may be incomplete.
4. **Doc-level labels**: Add `expected_relevant_doc_ids` to golden expectations to enable doc-level recall metrics, which would differentiate "missing doc type" from "wrong specific doc."
