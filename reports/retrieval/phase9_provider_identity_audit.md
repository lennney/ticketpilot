# Phase 9 Provider Identity Audit

*Generated at 2026-05-05*

## Summary

| Report | Provider | Model | Dim | Records | Verdict |
|--------|----------|-------|-----|---------|---------|
| `fake_retrieval_rows.json` | `fake` | sha-256 | 384 | 95 | ✅ CONFIRMED FAKE |
| `real_retrieval_rows.json` | `openai_compatible` | text-embedding-v4 | 1024 | 95 | ✅ CONFIRMED REAL |
| `phase9_retrieval_rows.json` | `fake` | sha-256 | 384 | 106 | ✅ CONFIRMED FAKE |
| `phase9_evaluation_metrics.json` | comparison_type=`knowledge_expansion_fake_vs_fake` | — | — | — | ✅ CORRECTLY LABELED |

## DB Metadata (`embedding_index_metadata`)

| id | provider | model | dim | records | built_at |
|----|----------|-------|-----|---------|----------|
| `c18cfa0a...` | fake | sha-256 | 384 | 95 | 2026-05-04 15:29 |
| `6403e5d1...` | openai_compatible | text-embedding-v4 | 1024 | 95 | 2026-05-04 17:02 |
| `fdbfa201...` | fake | sha-256 | 384 | 95 | 2026-05-04 17:14 |

The DB metadata confirms three historical rebuilds. The `openai_compatible` entry at 17:02 on May 4
proves that Phase 8 real used the dashscope API with `text-embedding-v4` at 1024 dimensions.

## Audit Per File

### `fake_retrieval_rows.json`
- Provider: `fake` (all 101 cases)
- Generated: 2026-05-04 16:37 UTC
- Verdict: **CONFIRMED FAKE** — correctly labeled

### `real_retrieval_rows.json`
- Provider: `openai_compatible` (all 101 cases)
- Generated: 2026-05-04 17:12 UTC
- Verdict: **CONFIRMED REAL** — correctly labeled
- This run used the dashscope API. The `.env.local` loading bug did not block this run;
  the user likely had the vars exported in the shell environment at that time.

### `phase9_retrieval_rows.json`
- Provider: `fake` (all 101 cases)
- Generated: 2026-05-05 11:15 UTC
- Verdict: **CONFIRMED FAKE** — correctly labeled

### `phase9_evaluation_metrics.json`
- comparison_type: `knowledge_expansion_fake_vs_fake`
- Both phase8 and phase9 labels explicitly state "Fake 384-d"
- Verdict: **CORRECTLY LABELED** — no misleading "real" claim

## Key Conclusions

1. **Phase 8 real baseline is trustworthy** — it genuinely used `openai_compatible / text-embedding-v4 / 1024d` from dashscope.
2. **Phase 9 has never been evaluated with a real provider** — only fake 384-d embeddings were used.
3. **No report was mislabeled as "real" when it was actually fake** — the previous semantics fix (Phase 9.5.1 Round 2) correctly renamed misleading "fake"/"real" labels to "phase8"/"phase9".
4. **The `.env.local` auto-load bug** (`c7d3c3a`) explains why Phase 9 couldn't use the real provider — `.env.local` was never loaded into `os.environ`, so the config always fell back to `fake`.

## Action Required

- **Phase 9 real evaluation** — needs to be run now that `.env.local` is auto-loaded
- Phase 8 real baseline does NOT need to be re-run — its provider identity is confirmed
