# Phase 9 Real-Provider Evaluation Readiness

*Generated at 2026-05-05*
*Updated 2026-05-05 — `.env.local` auto-load fixed*

## Status: READY — Real Embedding Provider Configured via `.env.local`

| Variable | Status |
|----------|--------|
| `EMBEDDING_PROVIDER` | `openai_compatible` |
| `EMBEDDING_MODEL` | `text-embedding-v4` |
| `EMBEDDING_DIM` | `1024` |
| `EMBEDDING_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `EMBEDDING_API_KEY` | present (`.env.local`, gitignored) |
| `EMBEDDING_BATCH_SIZE` | `10` |

All five required environment variables are configured in `.env.local` and
auto-loaded via `load_dotenv()` in `embedding_config.py`.

## Recent Fix

`src/ticketpilot/retrieval/embedding_config.py` now calls `load_dotenv()` on
import to load `.env.local` from the project root. Previously, the config
only read from `os.environ` directly, ignoring the `.env.local` file even
though `python-dotenv` was already a dependency.

## Execution Steps

```bash
# 1. Rebuild embeddings with real provider (will call dashscope API)
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
- **Real-provider rerun**: now executable — `.env.local` is auto-loaded by `embedding_config.py`
