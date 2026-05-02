# Quality Gate

## Overview

The quality gate is a bash script (`scripts/run_quality_gate.sh`) that enforces code quality, test coverage, and specification compliance before each commit or batch. It is the final acceptance gate for every change.

**Script:** `scripts/run_quality_gate.sh`

## Stages

The quality gate runs 5 stages sequentially. If any stage fails, the script exits with code 1.

### 1. Ruff Linting

**Command:** `uv run ruff check src tests`

- Runs Ruff static analysis on all source and test files
- Exits non-zero if any linting errors are found
- Must pass cleanly — no `|| true` bypass

### 2. Unit Tests

**Command:** `uv run python -m pytest tests/unit/ -v --strict-markers --cov=src/ticketpilot --cov-fail-under=70`

- Runs all unit tests in `tests/unit/`
- `--strict-markers`: Unknown pytest markers cause failure
- `--cov=src/ticketpilot --cov-fail-under=70`: Line coverage must be >= 70%
- Coverage file is written to `/tmp/` (via `COVERAGE_FILE` environment variable) to avoid SQLite lock issues on WSL cross-filesystem paths
- Exit non-zero if any tests fail or coverage threshold is not met

### 3. Integration Tests (with Skip-Count Guard)

**Command:** `uv run python -m pytest tests/integration/ -v --strict-markers`

- Runs all integration tests in `tests/integration/`
- **Skip-count guard**: If any tests are skipped AND `TICKETPILOT_SKIP_DB_TESTS` is not set to `1`, the gate fails
- Integration tests require a live PostgreSQL + pgvector database
- To temporarily bypass when DB is unavailable: `TICKETPILOT_SKIP_DB_TESTS=1 bash scripts/run_quality_gate.sh`

**Why skip-count guard exists:**
- Integration tests conditionally skip when the database is unavailable
- Prior to audit remediation (Stage 04), these skipped tests were invisible because the quality gate used `|| true` on every check
- The skip-count guard ensures that accidental DB unavailability is detected rather than silently ignored

### 4. OpenSpec Validation

**Command:** `openspec validate --all`

- Validates all OpenSpec specifications against the current implementation
- Exits non-zero if any spec fails validation
- If the `openspec` CLI is not installed, the stage produces a warning and continues (non-blocking)

### 5. Secret Scan

**Command:** `grep -rP 'sk-[a-zA-Z0-9]{20,}' . (with exclusions)`

- Scans the repository for potential OpenAI-style secrets (`sk-` prefix + 20+ alphanumeric characters)
- Excludes `.git`, `.venv`, `.venv_broken` directories, and `.env.example`
- Exits non-zero if any potential secret is detected

## Thresholds

| Check | Threshold | Notes |
|-------|-----------|-------|
| Ruff | 0 errors | All checks must pass |
| Unit test count | All pass | 0 test failures |
| Unit test coverage | >= 70% | Line coverage (`--cov-fail-under=70`) |
| Integration test count | All pass, 0 skipped | Skip-count guard enforced |
| OpenSpec validate | All pass | All specs validated |
| Secret scan | 0 secrets | No false positives expected |

## Current Results (as of Batch 3, Stage 1D)

| Metric | Value |
|--------|-------|
| Unit tests passed | 325 |
| Integration tests passed | 74 (0 skipped) |
| Coverage | 80.25% (above 70% threshold) |
| Ruff | All checks passed |
| OpenSpec validate --all | 11/11 passed |
| Secret scan | Clean |

## Design Principles

1. **No `|| true` hidden failures**: Every stage reports actual success/failure. Prior to Stage 04 audit remediation, the gate was a no-op because every command used `|| true`.
2. **Skipped integration tests are failure**: The skip-count guard catches accidental DB unavailability. The `TICKETPILOT_SKIP_DB_TESTS=1` bypass requires explicit opt-in.
3. **Two-phase pytest**: Unit tests and integration tests are separate phases with separate guarantees. Unit tests must always pass. Integration tests must pass with 0 skips (unless bypassed).
4. **Coverage threshold protects against regressions**: New code that lowers coverage below 70% will fail the gate. This threshold was preserved during the audit remediation.
5. **Fast feedback**: Ruff runs first (fastest), then unit tests, then integration tests (slowest). Failures are reported as early as possible.
