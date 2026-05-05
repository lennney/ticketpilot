# Phase 9.7.1 — Post-Archive Validation Repair Report

**Date:** 2026-05-05  
**Trigger:** 54 integration tests skipped with "Database not available" after Phase 9.7 archive  
**Target:** skipped = 0, quality gate PASSED

## Root Cause Investigation

### Symptom
After Phase 9.7 archive, the quality gate reported zero integration test failures, but only because 54 tests were silently skipped with `pytest.skip("Database not available")`.

### Root Causes (3-layer)

**Layer 1 — Missing psycopg-binary package.** `pyproject.toml` declares `psycopg[binary]>=3.3.3`, but `psycopg-binary` was not actually installed in the venv. Running `uv sync` did not pull it in (likely due to `--no-binary` or locked resolution). Fixed by `uv pip install psycopg-binary`.

**Layer 2 — WSL UNC path breaks native DLL loading on Windows.** The WSL-mounted project lives at `\\wsl.localhost\Ubuntu\...`, which Windows expands to `\\?\UNC\wsl.localhost\Ubuntu\...`. The `os.add_dll_directory()` API does not accept UNC paths (returns `FileNotFoundError`). Fixed by copying psycopg DLLs (libpq.dll, libcrypto.dll, libssl.dll) from the UNC-path venv to a local temp directory (`C:\Users\len\AppData\Local\Temp\ticketpilot_dlls`) and adding that directory to the DLL search path.

**Layer 3 — `uv run pytest` vs `python -m pytest`.** These use different entry points; the `uv run pytest` form was not correctly triggering the DLL setup in some cases. The quality gate already uses `python -m pytest`, which works. Both entry points now work after the fix.

### 8 Dimension-Mismatch Failures (secondary)
After fixing Layer 1–3, 8 tests failed (not skipped) with `AssertionError` because tests hardcoded `384` for embedding dimension, but the database has `vector(1024)`. Fixed by:
- Using `_detect_embedding_dim()` to read dimension from DB at runtime
- Using `FAKE_EMBEDDING_DIM` constant instead of hardcoded `384`
- Passing `expected_dim` fixture through test classes

## Files Modified

| File | Change |
|---|---|
| `src/ticketpilot/retrieval/db/connection.py` | Copy psycopg DLLs to local Windows temp dir when running on WSL |
| `tests/conftest.py` | Same DLL copy logic for pytest bootstrap |
| `tests/integration/test_vector_retrieval.py` | Dimension-aware: use `_detect_embedding_dim()` and `FAKE_EMBEDDING_DIM` |
| `tests/integration/test_retrieval_pipeline.py` | Dimension-aware assertion on `query_embedding` length |
| `tests/integration/test_retrieval_trace.py` | Dimension-aware assertion on `query_embedding` length |

## Files Removed

| File | Reason |
|---|---|
| `tests/_debug_add_dll.py` | Debug artifact from DLL investigation (ruff syntax error) |
| `tests/debug_dll_paths.py` | Debug artifact from DLL investigation (ruff E401) |

## Verification Results

### Integration Tests (Post-Repair)
```
119 passed, 0 failed, 0 skipped, 0 errors
```

### Full Quality Gate
```
Ruff:          All checks passed
Unit Tests:    770 passed, 0 failed
Coverage:      85.29% (threshold: 70%)
Integration:   119 passed, 0 skipped
OpenSpec:      15 passed, 0 failed
Secret Scan:   No secrets found
RESULT:        PASSED
```

## What Was NOT Changed
- No knowledge records added
- No Phase 7/8/DIMENSION baseline reports modified
- No portfolio metrics manipulated
- No coverage thresholds lowered
- No `|| true` or other suppression added
- No `.env` / API keys committed
