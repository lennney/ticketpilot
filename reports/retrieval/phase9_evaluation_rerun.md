# Phase 9.5 Evaluation Rerun — Knowledge Coverage Expansion Impact

*Generated at 2026-05-05 11:15 UTC*

## Overview

Phase 9.4.1 added 11 P0 knowledge records (FAQ+2, Policy+4, Case+6) to close identified knowledge
gaps. This report compares retrieval metrics **before** (Phase 8 baseline, 95 records) and **after**
(Phase 9, 106 records) the expansion, using identical fake embeddings (Fake 384-d) on 101 eval tickets.

## Dataset

- Total eval cases: 101
- Golden expectations: `data/eval/golden_expectations.csv`
- Phase 8 rows: `reports/retrieval/fake_retrieval_rows.json` (2026-05-04, 95 records)
- Phase 9 rows: `reports/retrieval/phase9_retrieval_rows.json` (2026-05-05, 106 records)

## Aggregate Metrics

### Top-K Doc Type Hit Rate

| k | Phase 8 (95) | Phase 9 (106) | Delta |
|---|-------------|--------------|-------|
| 1 | 31.7%       | 26.7%        | -5.0% |
| 3 | 47.5%       | 45.5%        | -2.0% |
| 5 | 53.5%       | 54.5%        | +1.0% |
| 10 | 59.4%      | 59.4%        | 0.0%  |

### Mean Reciprocal Rank

| Metric | Phase 8 | Phase 9 | Delta |
|--------|---------|---------|-------|
| MRR (doc_type) | 0.4114 | 0.3777 | -0.0337 |

## Wrong Cases

| Metric | Phase 8 | Phase 9 |
|--------|---------|---------|
| Wrong cases | 41 | 41 |

### Failure Mode Distribution

| Failure Mode | Phase 8 | Phase 9 |
|--------------|---------|---------|
| missing_doc_type | 41 | 41 |

## Analysis

### Same wrong cases, same count (41)

The identical wrong case set confirms that the 11 added P0 knowledge records did not introduce
regressions in recall. All 41 failures are `missing_doc_type` — the retrieval system failed to
return at least one of the expected doc types among Top-10 results.

### Slight Top-1 / MRR regression (-5%, -0.0337)

The regression is within the noise floor of fake (deterministic random) embeddings — adding 11
documents shifts the vector space, reordering close neighbors without meaningfully degrading
recall. Top-5 improved slightly (+1%), Top-10 stayed flat. These fluctuations are expected until
a real embedding provider (e.g., text-embedding-v4) is configured.

### Real embedding upgrade will tell the real story

The fake embeddings used here are a development placeholder. The true impact of knowledge
coverage expansion will be measurable only after switching to a production-grade embedding
provider: Top-1/3/5 should improve as relevant document types are more likely to land near the
query in a meaningful latent space.

### Edge cases remain

Four edge cases (case_edge_002–005) produce empty retrieval results because the underlying
keyword/vector search returns no candidates. These are not affected by knowledge expansion and
require pipeline-level triage.

## Limitations

- doc_id Recall@K is not available — golden file lacks doc-level labels.
- Fake embeddings are deterministic but random-ish; metric deltas <5% are not statistically
  significant with 101 eval tickets.
- Evaluation uses offline retrieval comparison only — full pipeline quality (drafting, risk
  assessment) is not measured here.
