# Provider Identity Gate

## Why This Gate Exists

During Phase 9, we discovered that `python-dotenv` was in `pyproject.toml` but `.env.local`
was never loaded into `os.environ`. The system silently fell back to `fake` provider for
all evaluation runs, producing results that were not only inconclusive — they were
**directionally misleading** (Top-1: -5.0% fake vs +2.0% real).

This gate prevents future evaluation runs from being misattributed to the wrong provider.

## Root Cause

```python
# Before (broken): .env.local never loaded
def load_embedding_config_from_env() -> EmbeddingConfig:
    return EmbeddingConfig(
        provider=os.environ.get("EMBEDDING_PROVIDER", "fake"),  # always "fake"
        ...
    )
```

`python-dotenv` was installed but never called. `.env.local` sat on disk with valid
dashscope credentials, but `os.environ` never saw them.

## Fix

`src/ticketpilot/retrieval/embedding_config.py` now loads `.env.local` at module level:

```python
from pathlib import Path
from dotenv import load_dotenv

_env_local = Path(__file__).resolve().parent.parent.parent.parent / ".env.local"
if _env_local.exists():
    load_dotenv(_env_local)  # override=False by default
```

## Priority Chain

```
shell environment  >  .env.local  >  fake fallback
   (os.environ)       (dotenv)      (default)
```

- `load_dotenv(override=False)` — shell env variables are never overwritten
- If no shell env and no `.env.local`: defaults to `fake / sha-256 / 384d`
- If `.env.local` exists and no conflicting shell env: reads from `.env.local`
- If shell env sets `EMBEDDING_PROVIDER=openai_compatible`: wins regardless of `.env.local`

## How to Audit Provider Identity

### 1. Check retrieval row traces

Every retrieval row file contains per-case `retrieval_trace.embedding_provider`:

```bash
uv run python -c "
import json
with open('reports/retrieval/<file>.json', encoding='utf-8') as f:
    data = json.load(f)
providers = set(c['retrieval_trace']['embedding_provider'] for c in data['cases'])
print(providers)  # {'fake'} or {'openai_compatible'}
"
```

### 2. Check DB embedding metadata

```sql
SELECT provider_name, model_name, dimension, source_record_count, built_at
FROM embedding_index_metadata ORDER BY built_at DESC;
```

### 3. Cross-reference

The provider in retrieval traces must match the active DB metadata entry. If traces
say `openai_compatible` but metadata says `fake`, the rows were generated with a
different DB state than what's currently active.

## API Key Safety

- `EmbeddingConfig.__repr__()` redacts `api_key` as `****`
- Error messages in `openai_compatible.py` and `providers/__init__.py` never include the key value
- `.env.local` is gitignored
- Secret scan runs in quality gate (`grep -rP 'sk-[a-zA-Z0-9]{20,}'`)

## Fake vs Real Provider Boundaries

| Context | Use Fake | Use Real |
|---------|---------|---------|
| Unit tests | Always | Never |
| Pipeline mechanics validation | OK | Not needed |
| Retrieval ranking debug | OK for deterministic repro | Use for final measurement |
| Top-K / MRR evaluation | Directional only, can be misleading | Required |
| Wrong case analysis | OK for taxonomy | Required for fix verification |
| Added-record hit audit | Coincidental hits only, not meaningful | Required |
| Knowledge expansion impact | Not valid | Required |
| Portfolio/metrics claims | Never | Always |

A retrieval run with `fake` provider is valid for:
- Verifying the pipeline executes end-to-end
- Checking data schemas and row counts
- Debugging deterministic retrieval behavior

A retrieval run with `fake` provider is NOT valid for:
- Measuring knowledge expansion impact
- Claiming Top-K improvements
- Evaluating semantic relevance of new documents
- Portfolio or interview metrics

## Prevention Checklist

Before claiming evaluation results:

- [ ] Check `retrieval_trace.embedding_provider` in the row file
- [ ] Check `embedding_index_metadata` in the database
- [ ] Verify the two match (both `openai_compatible` or both `fake`)
- [ ] If claiming real-provider results: both must say `openai_compatible`
- [ ] Run `openspec validate` to confirm no config regressions
- [ ] Secret scan: no API key in committed files
