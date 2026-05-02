# Acceptance Review Prompts

## Overview

This document contains reusable prompt templates for performing acceptance reviews at various stages of the development lifecycle. These reviews validate that a batch or change meets all requirements, passes quality standards, and is ready for commit or archive.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Full Validation Pack

### Purpose

Run a complete validation suite covering unit tests, integration tests, linting, spec validation, and secret scan. This is the comprehensive "everything check" before accepting a batch or change.

### When to Use

- Before committing any batch that includes code changes
- Before archiving an OpenSpec change
- When a quality gate failure needs full re-validation
- When multiple changes have been made and need consolidated validation

### Inputs to Provide

- **Project root**: Where to run the quality gate from
- **Quality gate script path**: Usually `scripts/run_quality_gate.sh`
- **Test directories**: Location of unit and integration tests
- **Spec directories**: Location of OpenSpec specifications

### Forbidden Scope

- Do NOT use `|| true` to bypass any validation step
- Do NOT skip any stage of the validation pack
- Do NOT lower coverage thresholds to pass validation
- Do NOT modify validation scripts to bypass checks

### Prompt Template

```
I need to run the full validation pack for [Change name / Batch name].

**Project**: [Project name]
**Quality gate script**: [scripts/run_quality_gate.sh]

**Required checks**:
1. Ruff linting: `uv run ruff check src tests` — MUST pass with 0 errors
2. Unit tests: `uv run python -m pytest tests/unit/ -v --strict-markers --cov=src/ticketpilot --cov-fail-under=[threshold]`
   — MUST pass, coverage >= [threshold]%
3. Integration tests: `uv run python -m pytest tests/integration/ -v --strict-markers`
   — MUST pass, 0 skipped (skip-count guard enforced)
4. Spec validation: `openspec validate --all` — MUST pass
5. Secret scan: grep for `sk-[a-zA-Z0-9]{20,}` pattern — MUST be clean

Run the following process:

### Step 1: Pre-Check
- [ ] git status --short shows expected files only
- [ ] Database is running (if integration tests need it): `docker compose ps`
- [ ] All dependencies are installed: `uv sync`

### Step 2: Run Full Validation
```bash
bash scripts/run_quality_gate.sh
```

### Step 3: Interpret Results
- Exit 0: ALL CHECKS PASSED — ready for acceptance
- Exit non-zero: FAILURE — identify which stage failed

### Step 4: Handle Failures
For each failure:
1. **Ruff failure**: Run `uv run ruff check src tests --fix`, re-run full gate
2. **Unit test failure**: Fix failing tests or implementation, re-run full gate
3. **Integration test failure**: Check DB status, fix test or implementation, re-run
4. **Skipped integration tests**: Treat as failure. Start DB if needed, re-run
5. **Spec validation failure**: Fix spec or implementation alignment, re-run
6. **Secret scan failure**: Investigate match, update exclusion or remove secret

### Step 5: Report Results
- [ ] Stage 1 (Ruff): [PASS/FAIL] — [error count if fail]
- [ ] Stage 2 (Unit tests): [PASS/FAIL] — [N passed, coverage X%]
- [ ] Stage 3 (Integration tests): [PASS/FAIL] — [N passed, N skipped]
- [ ] Stage 4 (Spec validation): [PASS/FAIL] — [N specs passed]
- [ ] Stage 5 (Secret scan): [PASS/FAIL] — [findings if fail]

Overall: **PASS** / **FAIL**
```

### Expected Output

- A complete validation run with results for all 5 stages
- For each stage: PASS/FAIL status with key metrics (counts, coverage)
- If failed: specific failure details and remediation steps
- Overall PASS/FAIL determination

### Acceptance Checklist

- [ ] Ruff: 0 errors
- [ ] Unit tests: all pass, coverage >= threshold
- [ ] Integration tests: all pass, 0 skipped
- [ ] Spec validation: all pass
- [ ] Secret scan: clean
- [ ] No `|| true` used in any stage
- [ ] No coverage threshold lowered
- [ ] Database was running (no DB-unavailable skips)

### Common Failure Modes

- **Skipping checks**: Running only unit tests but not integration tests or linting. All checks must run.
- **DB not running**: Integration tests skip silently. Always verify DB is running before running the gate.
- **Ignoring the skip count**: Even if integration tests "pass," skipped tests are failures. Check the skip count explicitly.
- **Partial re-validation**: After fixing one failure, re-running only that stage instead of the full gate. The full gate must run every time.
- **Using || true**: If the quality gate script has `|| true`, it will always exit 0 even when stages fail. Search for `|| true` in the script.

---

## 2. Unit / Integration / Ruff / OpenSpec / Quality Gate Review

### Purpose

Run each quality gate stage individually for focused debugging, while maintaining the same standards as the full gate. This is useful when a specific stage is failing and needs isolated attention.

### When to Use

- When a specific quality gate stage is failing and needs focused debugging
- When iterating on a fix for a linting error or test failure
- When the full gate is too slow for rapid iteration on a single issue
- When verifying the fix before running the full gate

### Inputs to Provide

- **Failing stage**: Which stage is failing (ruff, unit, integration, spec, secret)
- **Error output**: The specific error message or failure details
- **Changed files**: Recent changes that may be causing the failure

### Forbidden Scope

- Do NOT use individual stage runs as a substitute for the full quality gate
- Do NOT lower thresholds or add bypasses for individual stages
- Do NOT skip the full gate after fixing individual stage failures
- Do NOT use `|| true` on individual stages

### Prompt Template

```
I need to diagnose and fix a quality gate stage failure.

**Change/Batch**: [Change name / Batch name]
**Failing stage**: [ruff / unit tests / integration tests / spec validation / secret scan]

**Failure details**:
```
[paste error output]
```

**Recent changes** (may be causing the failure):
- [File 1]: [change summary]
- [File 2]: [change summary]

Diagnose and fix:

### Step 1: Identify Root Cause
- What specific error is being reported?
- Is it in new code or existing code?
- Is it a logic error, style issue, or configuration problem?

### Step 2: Apply Fix
- For Ruff: `uv run ruff check src tests --fix`
- For unit tests: fix the failing assertion or implementation
- For integration tests: fix the test or check DB availability
- For spec validation: align spec with implementation or vice versa
- For secret scan: remove secret or update exclusion pattern

### Step 3: Verify Individual Stage
Run the specific stage to verify the fix:

```bash
# For Ruff:
uv run ruff check src tests

# For Unit tests:
uv run python -m pytest tests/unit/ -v --strict-markers --cov=src/ticketpilot --cov-fail-under=[threshold]

# For Integration tests:
uv run python -m pytest tests/integration/ -v --strict-markers

# For Spec validation:
openspec validate --all

# For Secret scan:
grep -rP 'sk-[a-zA-Z0-9]{20,}' . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.venv_broken --exclude=.env.example
```

### Step 4: Run Full Quality Gate
After the individual fix is verified, run the full quality gate:
```bash
bash scripts/run_quality_gate.sh
```

The full gate MUST pass before proceeding.
```

### Expected Output

- Root cause diagnosis of the failing stage
- Specific fix applied to address the failure
- Individual stage verification (the failing stage now passes)
- Full quality gate pass confirmation

### Acceptance Checklist

- [ ] Root cause is identified (not just the symptom)
- [ ] Fix addresses the root cause (not a workaround)
- [ ] Individual stage passes after fix
- [ ] Full quality gate passes after fix
- [ ] No thresholds lowered or bypasses added
- [ ] No `|| true` used

### Common Failure Modes

- **Fixing symptoms, not root cause**: Adding a `# noqa` comment instead of fixing the linting violation, or adding `@pytest.mark.skip` instead of fixing the test.
- **Skipping full gate after individual fix**: "The unit test passes now, so the full gate will pass too." Always run the full gate — other stages may have regressed.
- **Ignoring integration test skips**: "The DB isn't running, so I'll just run unit tests." Integration tests must pass with 0 skips in the full gate.
- **Blind auto-fix**: Running `ruff --fix` without reviewing the changes can introduce incorrect formatting or logic changes. Review auto-fix output.
- **Using || true as a "temporary" fix**: Bypassing a stage with `|| true` because "I'll fix it later." Fix it now.

---

## 3. Test Gap Review

### Purpose

Review the test suite for gaps in coverage, missing scenarios, or insufficient assertions. This identifies untested code paths before they reach production.

### When to Use

- After implementing a new module or function
- Before committing a batch with significant new code
- When coverage drops or stagnates
- When reviewing test quality (not just quantity)
- Before archiving an OpenSpec change

### Inputs to Provide

- **Coverage report**: The detailed coverage report showing per-module coverage
- **Test files**: The test files for the new code
- **Source files**: The implementation files being tested
- **Quality gate output**: Showing pass/fail and coverage percentage

### Forbidden Scope

- Do NOT suggest removing existing tests to improve coverage percentage
- Do NOT suggest adding tests for code paths that are explicitly out of scope
- Do NOT suggest testing implementation details instead of behavior
- Do NOT claim acceptable coverage without verifying the quality of assertions

### Prompt Template

```
I need to review the test suite for gaps in coverage.

**Change/Batch**: [Change name / Batch name]

**Coverage report summary**:
- Overall coverage: [percentage]
- Coverage for new module: [percentage]
- Coverage threshold: [percentage]

**New source files**:
- [File 1]: [description, key functions]
- [File 2]: [description, key functions]

**Test files**:
- [Test file 1]: [test count, areas covered]
- [Test file 2]: [test count, areas covered]

Review the following:

### 1. Coverage Analysis
- Which functions or classes have low or no coverage in the new module?
- Which code paths (if/else branches, try/except blocks) are untested?
- Are there any entire modules or files with no tests?

### 2. Test Quality Assessment
- For each test: does it assert on meaningful behavior, not just "no crash"?
- Are there tests that pass but don't verify the output is correct?
- Are edge cases (empty input, None, invalid data) tested?
- Are error handling paths tested?

### 3. Missing Scenario Identification
- Are there requirements from the spec that lack corresponding tests?
- Are there pipeline integration scenarios not covered?
- Are there safety-critical behaviors not verified (no auto-send, human review triggers)?

### 4. Mocking Appropriateness
- Are mocks used for actual external dependencies (DB, network)?
- Are mocks used where real behavior should be tested?
- Is over-mocking hiding integration issues?

### 5. Regression Prevention
- Are there tests that would catch regressions in the new code?
- Would a change to the implementation cause tests to fail appropriately?
- Are there any "brittle" tests that might fail due to unrelated changes?

Provide:
- Coverage gaps identified (module, function, line)
- Test quality issues (weak assertions, missing scenarios)
- Recommendations for filling gaps
- Overall assessment: ADEQUATE / MINOR GAPS / MAJOR GAPS
```

### Expected Output

- Identified coverage gaps with module, function, and line-level detail
- Test quality assessment (assertions, edge cases, error paths)
- Missing scenario identification mapped to spec requirements
- Overall assessment: ADEQUATE, MINOR GAPS, or MAJOR GAPS

### Acceptance Checklist

- [ ] Coverage for new module meets or exceeds project threshold
- [ ] All functions/classes have at least basic coverage
- [ ] All branches (if/else, try/except) have coverage
- [ ] Tests assert on meaningful output, not just pass/fail
- [ ] Edge cases (empty, None, invalid) have dedicated tests
- [ ] Safety-critical behaviors are tested
- [ ] Mocks are appropriate (external deps mocked, real behavior tested)
- [ ] Regressions in new code would be caught by existing tests

### Common Failure Modes

- **Counting tests instead of evaluating quality**: 100 tests that all test the same happy path give false confidence. Evaluate what each test actually verifies.
- **Missing error path tests**: Functions with try/except blocks only test the try path. Each except block should have a dedicated test.
- **Asserting on the wrong thing**: Testing that a function "returns a value" without asserting the value is correct. Assert on specific outputs.
- **Over-mocking critical paths**: Mocking a database call in a test that should verify database interaction. Integration tests exist for this reason.
- **Brittle assertion patterns**: Asserting on string representations, order of dictionary keys, or other implementation details that may change. Test behavior, not implementation.

---

## 4. Production-Code Untouched Verification

### Purpose

Verify that a batch or change did not modify any production code (src/) files when it should not have. This is critical for documentation-only batches, test-only batches, and batches with strict forbidden scope.

### When to Use

- After any batch with a forbidden scope that includes production code
- Before committing documentation-only or test-only batches
- When auditing scope compliance across multiple batches
- When a batch claims to be "docs only" or "tests only"

### Inputs to Provide

- **Batch scope**: Allowed and forbidden scope for this batch
- **Git diff**: The changes made in this batch
- **Changed files list**: From git diff --name-only

### Forbidden Scope

- Do NOT approve a batch that modified production code when the scope forbade it
- Do NOT accept "it was just a small fix" exceptions for production code changes in a docs-only batch
- Do NOT allow import changes to production code files in a docs-only batch

### Prompt Template

```
I need to verify that production code was not modified in this batch.

**Batch**: [Batch name]
**Batch type**: [docs-only / test-only / scope-restricted]

**Allowed scope**: [What files this batch was allowed to touch]
**Forbidden scope**: [What files this batch was NOT allowed to touch]

**Changed files** (from git diff --name-only):
```
[full list of changed files]
```

Verification process:

### 1. Classify Each Changed File

| File | Category | Scope Status |
|------|----------|-------------|
| [file1.py] | src/ (production) / tests/ / docs/ / config/ | ALLOWED / FORBIDDEN / N/A |
| [file2.py] | src/ (production) / tests/ / docs/ / config/ | ALLOWED / FORBIDDEN / N/A |

### 2. Check Each Category

**Production code (src/)**:
- [ ] If batch is docs-only or test-only: NO src/ files should be modified
- [ ] If batch has forbidden scope on src/: NO src/ files in forbidden scope should be modified
- [ ] Any modifications must be within the explicit allowed scope

**Test code (tests/)**:
- [ ] Test modifications are within the batch's allowed test scope
- [ ] Tests only exercise functionality within the batch's scope

**Documentation (docs/)**:
- [ ] Documentation changes are accurate and truthful
- [ ] No code snippets that claim capabilities that don't exist

**Configuration**:
- [ ] No configuration files (pyproject.toml, .env.example, docker-compose.yml) were modified unless explicitly allowed

### 3. Report
- [ ] CLEAN: All changes are within scope, no forbidden modifications
- [ ] VIOLATION: [list each violation with file and reason]
```

### Expected Output

- A classification of each changed file by category (src, tests, docs, config)
- Scope compliance status for each file
- Overall: CLEAN (all within scope) or VIOLATION (at least one forbidden modification)
- For violations: specific file and reason

### Acceptance Checklist

- [ ] No src/ files modified in docs-only or test-only batches
- [ ] No files in forbidden scope were modified
- [ ] Test files only test functionality within the batch scope
- [ ] Configuration files were not modified (unless explicitly allowed)
- [ ] No import changes to production code outside allowed scope

### Common Failure Modes

- **Unnoticed production code change**: A documentation batch that accidentally adds a docstring to a production code file. This is still a modification and may not be desired.
- **Import-only change**: Adding an import to a production file "just to make the tests work" is still modifying production code.
- **Config file modification**: Changing pyproject.toml or docker-compose.yml in a docs batch. Config changes should be explicitly scoped.
- **Test imports from out-of-scope modules**: A test file that imports production modules outside the batch's scope. Tests should only test in-scope functionality.
- **Assuming "no change" without verification**: "I didn't touch any production code" without checking git diff. Always verify programmatically.

---

## 5. Commit Readiness Report

### Purpose

Generate a comprehensive report on whether a batch or change is ready to commit, covering all acceptance criteria, quality gate results, scope compliance, and documentation status.

### When to Use

- Before every commit (after quality gate passes)
- Before archiving an OpenSpec change
- When merging a feature branch
- When multiple reviewers need a summary of readiness status

### Inputs to Provide

- **Quality gate output**: Full output from the most recent run
- **Git status**: Current working tree state
- **Scope documentation**: Allowed and forbidden scope for the batch
- **Changelog**: Whether changelog has been updated
- **Tasks**: Whether tasks.md has been updated

### Forbidden Scope

- Do NOT mark as ready if quality gate failed
- Do NOT mark as ready if there are uncommitted changes unrelated to the batch
- Do NOT mark as ready if scope violations are present
- Do NOT mark as ready if tests are missing for new code

### Prompt Template

```
I need a commit readiness report for this batch.

**Change**: [Change name]
**Batch**: [Batch name]

**Quality gate result**: [PASS / FAIL]
**Quality gate output** (summary):
```
- Ruff: [PASS/FAIL]
- Unit tests: [PASS/FAIL] — N passed, coverage X%
- Integration tests: [PASS/FAIL] — N passed, N skipped
- Spec validation: [PASS/FAIL] — N specs
- Secret scan: [PASS/FAIL]
```

**Git status**:
```
[git status --short output]
```

**Scope compliance**: [CLEAN / VIOLATION]
**Documentation updated**: [changelog.md: YES/NO] [tasks.md: YES/NO]

Commit readiness checklist:

### Blocker Checks (MUST all pass)
- [ ] Quality gate exits 0
- [ ] Ruff: 0 errors
- [ ] Unit tests: all pass, coverage >= [threshold]%
- [ ] Integration tests: all pass, 0 skipped
- [ ] Spec validation: all pass
- [ ] Secret scan: clean
- [ ] No scope violations
- [ ] No uncommitted files outside the batch scope
- [ ] No `|| true` used
- [ ] No coverage threshold lowered

### Non-Blocker Checks (should verify)
- [ ] New code has corresponding tests
- [ ] Commit message follows project conventions
- [ ] Staged files are specific (not `git add -A`)
- [ ] changelog.md updated (if this batch completes a phase)
- [ ] tasks.md updated (if this completes any tasks)

### Summary
- **READY TO COMMIT**: All blocker checks pass
- **NOT READY**: [list specific blocker failures]

**Recommended commit message**: [type: description]

**Post-commit verification**:
- [ ] git status --short shows clean working tree
- [ ] Only expected files are committed
```

### Expected Output

- A structured readiness report with blocker and non-blocker checks
- Overall READY TO COMMIT or NOT READY status
- If NOT READY: specific blocker failures with remediation guidance
- Recommended commit message
- Post-commit verification steps

### Acceptance Checklist

- [ ] All blocker checks pass (quality gate, scope, git status)
- [ ] New code has corresponding tests
- [ ] Commit message is informative and follows project conventions
- [ ] changelog.md is updated if needed
- [ ] tasks.md is updated if needed
- [ ] Post-commit verification steps are documented

### Common Failure Modes

- **Forgetting the "last mile"**: Quality gate passes but changelog or tasks are not updated. Include documentation updates in the checklist.
- **Commit message too vague**: "Fix issues" or "Update code" are not informative. Include what was changed and why in the commit message.
- **Staging too many files**: `git add -A` stages files that shouldn't be in the commit. Stage specific files only.
- **Not verifying post-commit**: Assuming the commit was successful without checking `git status`. Always verify clean tree after commit.
- **Overlooking skipped tests**: Quality gate output shows "passed" but 3 integration tests were skipped. Check skip counts even when the gate exits 0.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Full Validation Pack | Run complete validation suite | Pre-commit, pre-archive |
| Individual Stage Review | Diagnose and fix specific stage failure | Stage failure debugging |
| Test Gap Review | Identify untested code paths and weak tests | Post-implementation, pre-commit |
| Production-Code Untouched | Verify src/ files not modified | Docs-only, test-only batches |
| Commit Readiness Report | Comprehensive pre-commit readiness check | Before every commit, pre-archive |
