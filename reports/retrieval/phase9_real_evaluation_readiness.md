# Phase 9 Real-Provider Evaluation Readiness

*Generated at 2026-05-05*

## Status: SKIPPED — No Real Embedding Provider Configured

The Phase 9 real-provider evaluation rerun was not executed because no real embedding
provider environment variables are configured on this machine.

### Required Environment

To run the real-provider evaluation, set the following environment variables or add them
to `.env.local`:

| Variable | Purpose |
|----------|---------|
| `EMBEDDING_PROVIDER` | e.g., `openai`, `openai_compatible`, `azure` |
| `EMBEDDING_BASE_URL` | API endpoint URL |
| `EMBEDDING_MODEL` | e.g., `text-embedding-v4` |
| `EMBEDDING_DIM` | Vector dimension for the model (e.g., `1024`) |
| `EMBEDDING_API_KEY` | API key (do not commit) |

### Steps When Ready

```bash
# 1. Configure env
export EMBEDDING_PROVIDER=openai_compatible
export EMBEDDING_BASE_URL=https://...
export EMBEDDING_MODEL=text-embedding-v4
export EMBEDDING_DIM=1024
export EMBEDDING_API_KEY=sk-...

# 2. Rebuild embeddings with real provider
uv run python scripts/rebuild_embeddings.py --confirm

# 3. Export Phase 9 retrieval rows
uv run python scripts/run_retrieval_comparison.py export \
    --tickets data/eval/tickets_eval.csv \
    --golden data/eval/golden_expectations.csv \
    --out-rows reports/retrieval/phase9_real_retrieval_rows.json

# 4. Compare Phase 9 real vs Phase 8 real baseline
uv run python scripts/run_retrieval_comparison.py compare \
    --fake-run-json reports/retrieval/real_retrieval_rows.json \
    --real-run-json reports/retrieval/phase9_real_retrieval_rows.json \
    --golden data/eval/golden_expectations.csv \
    --out-json reports/retrieval/phase9_real_evaluation_metrics.json \
    --out-md reports/retrieval/phase9_real_evaluation_rerun.md
```

### What Would Be Measured

The Phase 9 real-provider evaluation would measure whether the 11 added P0 knowledge
records improve retrieval metrics under a production-grade embedding model:

- **Hypothesis**: Real embeddings can leverage the semantic content of new Case, Policy,
  and FAQ records, improving Top-K hit rates and potentially reducing wrong case count.
- **Baseline**: Phase 8 real-provider metrics (text-embedding-v4, 1024-d):
  Top-1=42.6%, Top-3=56.4%, Top-5=58.4%, Top-10=59.4%, MRR=0.4913, Wrong cases=41
- **Expected**: Minimal wrong case reduction (gaps are coverage-driven, not embedding-driven)
  but potential improvement in Top-1/Top-3 ranking within found types.

### Current Phase 9 Conclusion

The Phase 9 fake-provider evaluation is **inconclusive for semantic impact**:
- Fake embeddings are deterministic random; adding documents shifts vector space
  without improving relevance
- Metric deltas (-5% to +1%) are within noise floor for 101 eval tickets
- Wrong case set identical (41 → 41) — expected with fake embeddings
- A real-provider rerun is required to measure the true impact of knowledge expansion
