# Quality Gate Acceptance Skill

## Purpose

Run and interpret the quality gate script to determine whether a batch or change is ready for acceptance and commit. The quality gate enforces code quality, test coverage, integration test completeness, specification compliance, and secret detection. Skipped integration tests are treated as failures.

## When to Use

- After every implementation batch before committing
- Before merging a feature branch into the main branch
- Before archiving an OpenSpec change
- When investigating CI or test failures
- Do NOT use for documentation-only changes that have no Python code impact (though it should still pass)

## Required Inputs

- Quality gate script at `scripts/run_quality_gate.sh`
- Live PostgreSQL + pgvector database (for integration tests) or `TICKETPILOT_SKIP_DB_TESTS=1` bypass
- Python environment with `uv` and all dependencies installed
- All source and test files in a consistent state
- OpenSpec CLI installed (optional but recommended)

## Allowed Scope

- Running `bash scripts/run_quality_gate.sh`
- Running individual stages manually: ruff, unit tests, integration tests, OpenSpec validate, secret scan
- Using `TICKETPILOT_SKIP_DB_TESTS=1` to bypass skip-count guard when database is intentionally unavailable
- Fixing code or tests that fail the quality gate
- Running `git status --short` to verify clean state before and after

## Forbidden Scope

- Do NOT use `|| true` to bypass any quality gate stage
- Do NOT lower the coverage threshold (--cov-fail-under=70)
- Do NOT skip integration test verification
- Do NOT modify quality gate scripts to hide failures
- Do NOT skip the quality gate on the basis that "it will pass later"
- Do NOT use `TICKETPILOT_SKIP_DB_TESTS=1` as a routine bypass -- it is for intentional offline development only

## Step-by-Step Procedure

1. **Check git status**
   - `git status --short` should show only the files you intend to commit
   - No unexpected dirty files

2. **Run the quality gate**
   - `bash scripts/run_quality_gate.sh`
   - The script runs 5 stages sequentially:
     1. **Ruff linting**: `uv run ruff check src tests` -- static analysis, must be clean
     2. **Unit tests**: `uv run python -m pytest tests/unit/ -v --strict-markers --cov=src/ticketpilot --cov-fail-under=70` -- all tests pass, coverage >= 70%
     3. **Integration tests**: `uv run python -m pytest tests/integration/ -v --strict-markers` -- all pass, 0 skipped (skip-count guard enforced)
     4. **OpenSpec validation**: `openspec validate --all` -- all specs pass
     5. **Secret scan**: `grep -rP 'sk-[a-zA-Z0-9]{20,}'` with exclusions -- no secrets detected

3. **Interpret results**
   - Exit code 0: All stages passed. Acceptance ready.
   - Exit code non-zero: At least one stage failed. Read the output to identify which stage.

4. **Handle failures per stage**

   | Stage | Failure | Action |
   |-------|---------|--------|
   | Ruff | Linting errors | Run `uv run ruff check src tests --fix` to auto-fix, review remaining issues |
   | Unit tests | Test failures or coverage < 70% | Fix failing tests or add missing coverage |
   | Integration tests | Failures or skips | If skip: check DB is running (`docker ps`), re-run. If still skip without DB: use `TICKETPILOT_SKIP_DB_TESTS=1` only when intentional |
   | OpenSpec validate | Spec violation | Fix the spec or the implementation to align |
   | Secret scan | Potential secret found | Investigate the match; if false positive, update the exclusion pattern |

5. **Re-run after fixing**
   - Fix the issue and re-run the full quality gate
   - Do not re-run only the failing stage -- the full gate ensures no regressions

6. **Proceed to commit**
   - Only after quality gate exits 0

## Acceptance Checklist

- [ ] `bash scripts/run_quality_gate.sh` exits 0
- [ ] Ruff: all checks pass (0 errors)
- [ ] Unit tests: all pass, coverage >= 70%
- [ ] Integration tests: all pass, 0 skipped (or explicit bypass documented)
- [ ] OpenSpec validate --all: all pass
- [ ] Secret scan: clean (no secrets detected)
- [ ] No `|| true` used anywhere in quality gate output or scripts
- [ ] No coverage threshold lowered
- [ ] `git status --short` clean before commit

## Common Failure Modes

- **Integration tests skip because DB is not running**: Run `docker compose up -d` to start PostgreSQL + pgvector, wait for readiness, then re-run. Do not suppress the skip count.
- **WSL coverage SQLite lock failure**: The quality gate exports `COVERAGE_FILE=/tmp/.coverage` to work around WSL cross-filesystem locking issues. If this fails, ensure `/tmp/` is writable and not on a Windows filesystem.
- **Missing dependencies cause import errors**: Run `uv sync` before the quality gate to ensure all dependencies are installed.
- **OpenSpec CLI not installed**: The gate produces a warning for this case and continues. Install via `npm install -g @anthropic-ai/cli-code` or equivalent.
- **False positive in secret scan**: API keys in test fixtures or documentation may trigger the secret pattern. Add an exclusion pattern or annotate the false positive.
- **Coverage just below threshold**: If adding new code drops coverage below 70%, either write tests for the uncovered code or increase coverage elsewhere.
- **Accidental `|| true`**: When modifying the quality gate script, ensure no `|| true` is added. The pipe operator `|` is not `||`. Search for `|| true` patterns across all shell scripts.

## Reusable Claude Code Prompt Template

```
I need to run the quality gate for the current batch. Follow this process:

1. First, check git status: `git status --short`
2. Run the full quality gate: `bash scripts/run_quality_gate.sh`
3. If it passes (exit 0), proceed to commit.
4. If it fails:
   a. Identify which stage failed (Ruff, unit tests, integration tests, OpenSpec validate, or secret scan)
   b. Fix the specific issue
   c. Re-run the full quality gate
   d. Repeat until it passes

Critical rules:
- Do NOT use `|| true` to suppress failures
- Do NOT lower the coverage threshold (70%)
- Do NOT skip integration test verification
- Skipped integration tests ARE failures (unless TICKETPILOT_SKIP_DB_TESTS=1 is set intentionally)
- If integration tests skip because DB is unavailable: start DB with `docker compose up -d`, wait, re-run
```

## TicketPilot Example

During the audit remediation (Stage 04), the quality gate was fundamentally broken: every check used `|| true`, making it impossible to detect failures. 26 skipped integration tests were invisible. The fix involved:

1. **Removing `|| true`** from ruff, pytest, and openspec validate lines in `scripts/run_quality_gate.sh`
2. **Adding two-phase pytest**: Unit tests (must pass, coverage >= 70%) and integration tests (must pass, 0 skipped)
3. **Adding skip-count guard**: If `pytest` reports any skipped tests and `TICKETPILOT_SKIP_DB_TESTS` is not set, the gate fails
4. **Adding coverage threshold**: `--cov=src/ticketpilot --cov-fail-under=70` to prevent untested code from being added
5. **Adding `--strict-markers`**: Unknown pytest markers cause failure

After the fix, the quality gate detected:
- 7 golden case test failures from missing `retrieve_evidence` mocks (fixed with proper `@patch`)
- 33 skipped integration tests from missing `psycopg-pool` dependency (restored to `pyproject.toml`)
- Coverage at 68.97% (below 70% threshold) -- coverage restored to 80.25%

The gate went from a no-op (always exit 0) to a meaningful gate that actually enforces quality.
