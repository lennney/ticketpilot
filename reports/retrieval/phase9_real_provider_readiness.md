# Phase 9 Real-Provider Evaluation Readiness

*Generated at 2026-05-05*

## Status: SKIPPED — No Real Embedding Provider Configured

| Variable | Status |
|----------|--------|
| `EMBEDDING_PROVIDER` | unset |
| `EMBEDDING_MODEL` | unset |
| `EMBEDDING_DIM` | unset |
| `EMBEDDING_BASE_URL` | unset |
| `EMBEDDING_API_KEY` | not present |

All five required environment variables are unset. No real embedding provider can be
instantiated without them.

## Required Configuration

Set the following in the shell environment or `.env.local` (not committed):

| Variable | Example Value | Purpose |
|----------|--------------|---------|
| `EMBEDDING_PROVIDER` | `openai_compatible` | Provider factory selection |
| `EMBEDDING_BASE_URL` | `https://api.example.com/v1` | API endpoint |
| `EMBEDDING_MODEL` | `text-embedding-v4` | Model identifier |
| `EMBEDDING_DIM` | `1024` | Vector dimension |
| `EMBEDDING_API_KEY` | `sk-...` | Authentication key |

## Execution Steps When Ready

```bash
# 1. Rebuild embeddings with real provider
uv run python scripts/rebuild_embeddings.py --confirm

# 2. Export Phase 9 real-provider retrieval rows
uv run python scripts/run_retrieval_comparison.py export \
    --tickets data/eval/tickets_eval.csv \
    --golden data/eval/golden_expectations.csv \
    --out-rows reports/retrieval/phase9_real_retrieval_rows.json

# 3. Compare Phase 9 real vs Phase 8 real baseline
uv run python scripts/run_retrieval_comparison.py compare \
    --fake-run-json reports/retrieval/real_retrieval_rows.json \
    --real-run-json reports/retrieval/phase9_real_retrieval_rows.json \
    --golden data/eval/golden_expectations.csv \
    --out-json reports/retrieval/phase9_real_evaluation_metrics.json \
    --out-md reports/retrieval/phase9_real_evaluation_rerun.md

# 4. Re-run P0 hit audit on real-provider results
# (check if P0 records surface for their intended queries)
```

## Expected Behavior

Under a real embedding provider, the Phase 9 knowledge expansion (95→106 records) should show:
- **Improved Top-1/3 ranking** within correct cases (semantic matching)
- **P0 records surfacing for related queries** where the content is semantically relevant
- **Minimal wrong-case count reduction** — wrong cases are primarily coverage-driven, not
  embedding-quality-driven

## Phase 8 Real Baseline (for reference)

| Metric | Phase 8 Real (text-embedding-v4, 1024-d) |
|--------|----------------------------------------|
| Top-1 | 42.6% |
| Top-3 | 56.4% |
| Top-5 | 58.4% |
| Top-10 | 59.4% |
| MRR | 0.4913 |
| Wrong cases | 41 |

## Current Phase 9 Conclusion

- **Phase 9 fake-provider evaluation**: inconclusive for semantic impact
  (metric deltas -5% to +1% within noise floor, 0 wrong cases fixed)
- **P0 added-record hit audit**: 3/16 partial hits, 0 wrong cases fixed
  (records exist but fake embeddings cannot leverage semantic content)
- **Real-provider rerun**: pending configuration of `EMBEDDING_*` env vars
