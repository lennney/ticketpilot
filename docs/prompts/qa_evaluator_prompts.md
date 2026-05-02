# QA Evaluator Prompts

## Overview

This document contains reusable prompt templates for the **QA Evaluator** role in an OpenSpec-driven development workflow. The QA Evaluator is responsible for ensuring test quality, coverage completeness, quality gate integrity, and regression prevention. These prompts help structure QA reviews at key decision points.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Test Strategy Design

### Purpose

Design a test strategy for a proposed change, defining what to test, how to test it, what the coverage targets are, and what explicitly will NOT be tested. This ensures test effort is focused on the most important behaviors.

### When to Use

- When a new OpenSpec change is being designed and spec.md needs a test strategy section
- When adding a new module or pipeline stage that needs test coverage
- When the existing test strategy needs review or expansion

### Inputs to Provide

- **Change design**: Link to the design document
- **Specification**: Requirements and scenarios from the spec
- **Existing test strategy**: Current testing approach documentation
- **Quality gate thresholds**: Current coverage requirements and test pass criteria
- **Architecture context**: Module boundaries and dependency direction

### Forbidden Scope

- Do NOT write test code (this is a strategy document, not test implementation)
- Do NOT lower existing coverage thresholds
- Do NOT suggest skipping tests for critical paths
- Do NOT suggest using `|| true` or other bypass mechanisms in test scripts

### Prompt Template

```
I need to design a test strategy for this proposed change.

**Change**: [Change name]
**Design document**: [path/to/design.md]
**Spec**: [path/to/spec.md]

**Existing test context**:
- Current unit test count: [count]
- Current integration test count: [count]
- Current coverage: [percentage]
- Quality gate thresholds: >= 70% coverage, 0 skipped integration tests

**Module being tested**: [Module name and location]

Design a test strategy covering:

### 1. Unit Test Plan
- What new unit tests are needed for this module?
- What is the test count estimate?
- Which functions or classes need the most thorough testing?
- What mocking strategy is needed (what external dependencies to mock)?

**Guidelines**:
- Pure functions should have exhaustive input/output testing
- Functions with external dependencies (DB, network, filesystem) should be mocked
- Edge cases (empty inputs, None values, boundary conditions) should always be tested

### 2. Integration Test Plan
- What integration tests are needed?
- What scenarios require a live database or external service?
- How will the test verify end-to-end behavior?
- What is the integration test count estimate?

**Guidelines**:
- Integration tests should cover real database interactions
- Each integration test should verify a specific pipeline scenario
- Golden cases (representative end-to-end scenarios) should be defined

### 3. Test Boundaries
- What is the boundary between unit and integration tests?
- Which tests MUST run in every quality gate (unit tests)?
- Which tests require special setup (integration tests)?
- What is explicitly NOT tested?

### 4. Mocking Strategy
- What external dependencies need to be mocked?
- What mock objects or helpers already exist?
- What new test fixtures or factories are needed?

### 5. Coverage Targets
- What is the expected coverage contribution of this module?
- Will the change maintain or improve the overall coverage?
- Any coverage gaps that are acceptable (with documented rationale)?

Provide a structured strategy with:
- Estimated test counts (unit and integration)
- Key test scenarios mapped to requirements
- Mocking approach
- Explicit list of what is NOT tested and why
```

### Expected Output

- A test strategy with estimated unit and integration test counts
- Key test scenarios mapped to specific requirements from the spec
- Mocking approach with existing and needed test helpers
- Explicit test boundaries and exclusions with rationale
- Coverage impact assessment

### Acceptance Checklist

- [ ] Unit test plan covers pure functions exhaustively
- [ ] Integration test plan covers end-to-end pipeline scenarios
- [ ] Mocking strategy is clear and leverages existing helpers where possible
- [ ] Test boundaries between unit and integration are clearly defined
- [ ] Coverage targets are realistic and maintain the >= 70% threshold
- [ ] Untested scenarios are explicitly documented with rationale
- [ ] No suggestion to bypass quality gate or lower thresholds

### Common Failure Modes

- **Testing only the happy path**: The most common testing gap. Every function should have tests for edge cases (empty, None, invalid, boundary values).
- **Over-mocking**: Mocking everything makes tests fast but meaningless. Integration tests should verify real interactions; unit tests should mock only external dependencies.
- **Ignoring existing test patterns**: New tests should follow the same patterns (fixtures, naming conventions, directory structure) as existing tests.
- **Skipping integration tests**: "Too hard to set up" is not an acceptable reason. Integration tests with 0 skips is a quality gate requirement.
- **No edge case coverage**: Functions that accept user input, file paths, or external data must be tested with unexpected inputs.

---

## 2. Golden Case Planning

### Purpose

Define golden test cases that represent the most important end-to-end scenarios for the system. Golden cases serve as regression benchmarks and manual smoke test scenarios.

### When to Use

- When a new pipeline stage or processing path is added
- When defining acceptance criteria for a change
- When creating manual test scenarios for demos or reviews
- When expanding test coverage for new scenarios

### Inputs to Provide

- **Pipeline stages**: The processing steps the golden case should exercise
- **Known risk scenarios**: Edge cases, error paths, and security-relevant scenarios
- **Domain scenarios**: Typical and atypical use cases from the product domain
- **Existing golden cases**: Current golden case definitions (if any)

### Forbidden Scope

- Do NOT claim golden cases replace automated testing (they supplement it)
- Do NOT design golden cases that require unavailable capabilities
- Do NOT suggest golden cases that violate the product boundary
- Do NOT claim that passing golden cases proves production readiness

### Prompt Template

```
I need to define golden test cases for this system.

**System**: [Project name and brief description]
**Pipeline stages**: [List of processing stages]

**Existing golden cases** (if any):
- [GC1: description]
- [GC2: description]

**Domain scenarios to cover**:
- [Scenario type 1]: [Description]
- [Scenario type 2]: [Description]

**Risk scenarios to cover**:
- [Risk scenario 1]: [Description]
- [Risk scenario 2]: [Description]

Design golden cases following these principles:

1. **Cover core paths**: Each major pipeline path should have at least one golden case.
2. **Cover risk scenarios**: High-risk, error, and edge case paths should have golden cases.
3. **Each case is independent**: No golden case depends on another.
4. **Clear expected output**: Each case has a documented expected result.
5. **Reproducible**: Each case uses seed data or documented test fixtures.

For each golden case, include:
- **ID**: GC[N]
- **Scenario**: What is being tested
- **Input**: The test input (ticket text, configuration, etc.)
- **Expected pipeline stages exercised**: Which stages must be triggered
- **Expected output**: What the system should produce
- **Key assertions**: The most important things to verify
- **Risk indicators**: What risk flags or safety mechanisms should trigger

Provide:
- Table of golden cases with ID, scenario, intent, and key risk flag
- For each case: input, expected output, key assertions
- Coverage matrix showing which requirements each case covers
```

### Expected Output

- A set of golden case definitions (typically 6-10 cases)
- For each case: ID, scenario, input, expected output, key assertions, risk indicators
- A coverage matrix mapping golden cases to requirements
- Guidance on manual vs. automated execution for each case

### Acceptance Checklist

- [ ] Golden cases cover all major pipeline paths
- [ ] High-risk and error scenarios have dedicated golden cases
- [ ] Each case has clear, verifiable expected output
- [ ] Each case is reproducible with documented test fixtures or seed data
- [ ] No golden case depends on another
- [ ] Coverage matrix shows which requirements are covered
- [ ] No claim that golden cases replace automated testing

### Common Failure Modes

- **Only happy path cases**: If all golden cases expect successful processing, risk and error paths are untested. Include failure scenarios.
- **Cases too similar**: Multiple cases testing the same pipeline path with slightly different inputs add little value. Ensure diversity.
- **Expected output too vague**: "System should respond appropriately" is not verifiable. Expected output must be specific and testable.
- **Ignoring existing golden cases**: New golden cases should complement, not duplicate, existing ones. Review the full set for overlap.
- **No edge case coverage**: Empty input, malformed data, and boundary conditions should have dedicated golden cases.

---

## 3. Quality Gate Hardening

### Purpose

Review and strengthen the quality gate script to ensure it enforces meaningful quality standards, detects regressions, and cannot be silently bypassed.

### When to Use

- When the quality gate script needs review for gaps or bypass mechanisms
- When adding new stages to the quality gate (e.g., new linters, new test types)
- When investigating CI failures caused by quality gate bypass
- After discovering `|| true` patterns or other bypass mechanisms in the gate

### Inputs to Provide

- **Quality gate script**: Path to the current quality gate script
- **Current stages**: What the quality gate currently checks
- **Known bypasses**: Any `|| true`, skipped tests, or other bypass mechanisms
- **Quality requirements**: Mandatory checks (ruff, coverage threshold, skip-count guard)

### Forbidden Scope

- Do NOT add `|| true` or any other bypass mechanism
- Do NOT lower existing thresholds (coverage, linting, test pass rate)
- Do NOT remove stages from the quality gate
- Do NOT skip integration test verification

### Prompt Template

```
I need to harden the quality gate for this project.

**Quality gate script**: [path/to/script.sh]

**Current stages**:
1. [Stage 1]: [command and threshold]
2. [Stage 2]: [command and threshold]
3. [Stage 3]: [command and threshold]

**Known bypasses or gaps**:
- [Bypass/gap 1]
- [Bypass/gap 2]

**Required quality checks**:
- [Check 1]: [e.g., "Ruff linting, 0 errors"]
- [Check 2]: [e.g., "Unit tests, all pass, >= 70% coverage"]
- [Check 3]: [e.g., "Integration tests, all pass, 0 skipped"]
- [Check 4]: [e.g., "Spec validation, all pass"]
- [Check 5]: [e.g., "Secret scan, 0 secrets"]

Review and recommend hardening:

### 1. Bypass Detection
- Scan the script for `|| true`, `|| exit 0`, or any pattern that suppresses failures
- Check each stage: does a failure actually cause the script to exit non-zero?
- Are there any conditionals that could skip stages unintentionally?

### 2. Stage Completeness
- Are all required quality checks present?
- Are the checks in the right order (fastest first, so failures surface quickly)?
- Are any checks redundant or unnecessary?

### 3. Threshold Rigor
- Are coverage thresholds set and enforced?
- Are skipped tests treated as failures?
- Are linting errors treated as failures?
- Are any thresholds too low to be meaningful?

### 4. Feedback Quality
- Does each stage provide clear output when it passes or fails?
- Is it obvious which stage failed and why?
- Are error messages actionable?

### 5. Bypass Prevention
- Is there a documented bypass mechanism (e.g., environment variable for "no DB")?
- Is the bypass mechanism explicit and intentional (not accidentally triggered)?
- Is the bypass mechanism documented with its risks?

For each finding, provide:
- Severity (BLOCKER, WARNING, SUGGESTION)
- Specific issue (with line reference)
- Recommended fix
```

### Expected Output

- A review of the quality gate script with findings grouped by severity
- For each BLOCKER: specific bypass or gap with line reference and fix
- For each WARNING: potential issue that could become a problem
- For each SUGGESTION: improvement that would add value
- Recommended action plan prioritized by severity

### Acceptance Checklist

- [ ] All `|| true` patterns are identified and flagged
- [ ] Each stage is verified to properly report failure (non-zero exit on failure)
- [ ] Coverage threshold is verified to be set and enforced
- [ ] Skipped integration tests are verified to be treated as failures
- [ ] Bypass mechanisms (if any) are explicit and intentional
- [ ] Stage ordering puts fastest checks first
- [ ] Feedback from each stage is clear and actionable

### Common Failure Modes

- **Hidden `|| true`**: The pipe operator `|` is not `||`. Search specifically for `|| true` and `|| exit 0` patterns. Also check for `|| :` (colon is a no-op in bash).
- **Skipped tests invisible**: Without a skip-count guard, integration tests that skip silently are indistinguishable from passing tests. Always check skip counts.
- **Coverage threshold too low**: If coverage is 95% and threshold is 70%, a 25% drop could go undetected. Consider higher thresholds as the project matures.
- **Stage order wrong**: Placing slow checks (integration tests) before fast checks (linting) delays feedback. Fastest checks should run first.
- **Bypass env var becomes default**: An environment variable intended for intentional bypass becomes routine practice. Document its purpose and risks clearly.

---

## 4. Skipped Integration Test Detection

### Purpose

Detect and remediate skipped integration tests. Skipped integration tests must be treated as failures — not as acceptable omissions — because they hide gaps in end-to-end verification.

### When to Use

- When reviewing quality gate output that shows skipped integration tests
- When investigating why integration tests are conditionally skipped
- When auditing the integration test suite for uncovered scenarios
- Before archiving an OpenSpec change

### Inputs to Provide

- **Integration test directory**: Path to the integration tests
- **Quality gate output**: Recent quality gate run showing test results
- **Database status**: Whether the test database is running
- **Skip conditions**: The conditions under which tests skip (e.g., DB unavailable)

### Forbidden Scope

- Do NOT add `unittest.skip` or `pytest.mark.skip` without documented, approved rationale
- Do NOT suggest lowering the skip-count guard threshold
- Do NOT convert skipped tests to passing tests by reducing their coverage
- Do NOT use `|| true` to bypass the skip-count guard

### Prompt Template

```
I need to detect and remediate skipped integration tests.

**Integration test directory**: [path/to/tests/integration/]

**Recent quality gate output** (relevant section):
```
[paste quality gate output showing skipped tests]
```

**Skip conditions**: [When and why tests are skipped]

**Database status**: [Is the test DB running?]

Perform the following:

### 1. Identify Skipped Tests
- Run `uv run python -m pytest tests/integration/ -v --strict-markers`
- Collect the list of skipped tests and skip reasons
- Count total skipped vs. total integration tests

### 2. Classify Each Skip

| Category | Description | Action |
|----------|-------------|--------|
| DB unavailable | Tests skip because database is not running | Start DB, re-run |
| Missing dependency | Tests skip because a required package is missing | Install dependency |
| Intentional skip | Tests marked with @pytest.mark.skip or skipif | Evaluate whether intentional |
| Pending implementation | Tests for code not yet written | Either write the code or remove the test |
| Environmental | Tests skip due to OS, filesystem, or permission issues | Fix environment or make test robust |

### 3. Remediate
- For DB-unavailable skips: start the database and re-run
- For missing dependencies: install and re-run
- For intentional skips: evaluate whether the skip is justified
  - Approved rationale? (e.g., feature not yet implemented, documented as deferred)
  - If not approved: remove skip, fix the test or implementation
- For pending implementation: either complete the implementation or remove the placeholder test

### 4. Report
- Final count: N integration tests, 0 skipped (or N skipped with documented bypass)
- List any remaining skips with approved bypass and rationale
- Confirm skip-count guard in quality gate is working
```

### Expected Output

- A complete list of all integration tests with pass/fail/skip status
- For each skipped test: category, reason, and remediation action
- Final status: all passing with 0 skipped, or documented exceptions
- Confirmation that the skip-count guard is functioning

### Acceptance Checklist

- [ ] All skipped integration tests are identified and categorized
- [ ] Each skip has a documented, approved rationale or is remediated
- [ ] DB-unavailable skips are eliminated (DB must be running)
- [ ] No intentional skips without approved rationale
- [ ] No pending-implementation placeholder tests remain
- [ ] Skip-count guard in quality gate is verified to detect skips

### Common Failure Modes

- **DB not running**: The most common cause of integration test skips. Always check `docker compose ps` before investigating other causes.
- **Skip condition too broad**: A `skipif` condition like `True` or an environment variable check that's always true. Each skip condition should be narrow and intentional.
- **Intentional skip without documentation**: Every intentionally skipped test should have a comment explaining why and when the skip will be removed.
- **Placeholder tests**: Tests added during planning that skip because the implementation doesn't exist yet. Either implement or remove. Do not leave as ignored placeholders.
- **Missing dependency that was once present**: A dependency removed from pyproject.toml that integration tests still need. Check pyproject.toml for completeness.

---

## 5. Coverage and Regression Review

### Purpose

Review test coverage metrics and detect regressions in coverage, test counts, or quality gate results. Ensure that new code does not reduce coverage and that all existing tests continue to pass.

### When to Use

- After every implementation batch before committing
- Before archiving an OpenSpec change
- When investigating coverage declines
- When adding new modules that need test coverage
- When reviewing quality gate history for trend analysis

### Inputs to Provide

- **Current quality gate output**: The full output of the most recent quality gate run
- **Previous quality gate output**: The output from the prior batch or baseline
- **Changed files**: Which files were modified in this batch
- **Coverage report**: Detailed coverage breakdown per module

### Forbidden Scope

- Do NOT lower coverage thresholds to make the gate pass
- Do NOT exclude new modules from coverage requirements
- Do NOT use `|| true` or other bypass mechanisms
- Do NOT claim coverage improvements that come from excluding previously covered code

### Prompt Template

```
I need to review coverage and regression for this batch.

**Change**: [Change name]
**Batch**: [Batch description]

**Current quality gate output**:
```
[paste full output]
```

**Previous quality gate output** (prior batch):
```
[paste prior output]
```

**Changed files**:
- [File 1]: [Summary of changes]
- [File 2]: [Summary of changes]
- [File 3]: [Summary of changes]

Review the following:

### 1. Test Count Regression
- Compare unit test counts: current vs. previous
- Compare integration test counts: current vs. previous
- Any tests that were removed or stopped passing?
- Any tests that were modified and might have reduced coverage?

### 2. Coverage Regression
- Current coverage: [percentage]
- Previous coverage: [percentage]
- Delta: [+/- percentage]
- If coverage decreased: identify which modules lost coverage
- Is the decrease in a module that was modified, or elsewhere?

### 3. Skipped Integration Tests
- Current skipped count: [count]
- Previous skipped count: [count]
- Any new skips? Any skips resolved?
- Are existing skips still justified?

### 4. New Code Coverage
- Which new files or functions were added?
- Do they have corresponding unit tests?
- Is the coverage for new code at least as high as the project average?

### 5. Trend Assessment
- Is coverage trending up, down, or stable over the last 3+ batches?
- Are test counts keeping pace with code additions?
- Are there systemic patterns of low coverage in certain module areas?

Provide:
- Coverage and test count delta summary
- Specific regressions (if any) with affected modules
- Recommendations for improving coverage or preventing future regression
- Blocker flag if coverage drops below threshold
```

### Expected Output

- Delta summary: unit tests (+N), integration tests (+N), coverage (+/-X%)
- List of any regressions with affected modules and severity
- Coverage breakdown by module for changed files
- Trend assessment (up/down/stable over last 3+ batches)
- Blocker flag if coverage below threshold or tests decreased

### Acceptance Checklist

- [ ] Test counts are compared against previous batch baseline
- [ ] Coverage delta is calculated and evaluated
- [ ] Any coverage decrease is identified at the module level
- [ ] Skipped integration tests are tracked and justified
- [ ] New code has adequate test coverage
- [ ] Trend is assessed over multiple batches
- [ ] No coverage threshold violations

### Common Failure Modes

- **Comparing to wrong baseline**: Comparing against a merge commit instead of the previous batch produces misleading deltas. Always compare batch-to-batch.
- **Missing module-level analysis**: Overall coverage may stay the same while a critical module drops significantly. Analyze at module level.
- **Not removing old tests**: When code is refactored, old tests for removed functionality still count in the total but may give a false sense of coverage.
- **Ignoring test quality**: A test that passes but makes no meaningful assertions adds to the count but not to coverage quality. Review test assertions, not just counts.
- **Coverage threshold barely met**: If coverage is 70.1% and the threshold is 70%, any small change could drop below. Consider creating a buffer above the minimum.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Test Strategy Design | Design test approach for a proposed change | Change design with spec |
| Golden Case Planning | Define end-to-end benchmark scenarios | New pipeline stage, acceptance criteria |
| Quality Gate Hardening | Review and strengthen quality gate script | Gate script review, bypass investigation |
| Skipped Integration Test Detection | Find and fix skipped integration tests | Quality gate review, pre-archive audit |
| Coverage and Regression Review | Review test coverage trends and regressions | Batch completion, pre-archive |
