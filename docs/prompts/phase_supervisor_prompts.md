# Phase Supervisor Prompts

## Overview

This document contains reusable prompt templates for the **Phase Supervisor** role in an OpenSpec-driven development workflow. The Phase Supervisor is responsible for gatekeeping — ensuring that each phase or batch is ready to proceed before work continues. This includes implementation-readiness reviews, batch acceptance, forbidden-scope audits, task status audits, and final phase acceptance.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Implementation-Readiness Review

### Purpose

Verify that a batch or phase is ready for implementation before any code is written. This includes checking that the design is approved, the spec is complete, the tasks are defined, and all prerequisites are met.

### When to Use

- Before starting implementation of any batch or phase
- When a design document has been created and needs sign-off to proceed
- When resuming work after a pause or interruption
- When a new team member is about to start implementation

### Inputs to Provide

- **Design document**: The approved design.md for the change
- **Spec document**: The spec.md with requirements and test strategy
- **Tasks document**: The tasks.md with batch breakdown
- **Current phase status**: What has been completed so far
- **Prerequisites**: Any dependencies that must be satisfied before starting

### Forbidden Scope

- Do NOT review implementation code (no code has been written yet)
- Do NOT review test details (test strategy is sufficient at this stage)
- Do NOT skip the review even for "trivial" batches
- Do NOT approve implementation if design or spec has unresolved issues

### Prompt Template

```
I need to verify implementation readiness for this batch.

**Change**: [Change name]
**Batch**: [Batch number and name]

**Design document**: [path/to/design.md] — [APPROVED / PENDING REVIEW]
**Spec document**: [path/to/spec.md] — [COMPLETE / PENDING]
**Tasks document**: [path/to/tasks.md] — [Current batch: [status]]

**Prerequisites**:
- [Prerequisite 1]: [MET / NOT MET]
- [Prerequisite 2]: [MET / NOT MET]

Review readiness across these dimensions:

### 1. Design Readiness
- Is the design document approved by all reviewer roles?
- Are all design decisions documented with rationale?
- Are there any open questions or unresolved design issues?
- Does the design clearly state what is in scope and what is out of scope?

### 2. Specification Readiness
- Are requirements documented with concrete acceptance criteria?
- Is the test strategy defined?
- Are there Gherkin-style scenarios (WHEN/THEN) for each requirement?
- Are acceptance thresholds specified with numbers (not vague language)?

### 3. Task Readiness
- Is the current batch clearly defined with allowed and forbidden scope?
- Are the files or modules to be changed listed?
- Is the batch sized appropriately (not too large, not too small)?
- Are dependencies on other batches identified?

### 4. Environment Readiness
- Is the development environment set up (dependencies installed, DB running)?
- Are there any toolchain issues (missing CLI, broken scripts)?
- Is the quality gate script working?

### 5. Prerequisite Verification
- Are all prerequisites met?
- Are any prerequisites that could be skipped without risk?
- Are there blocking prerequisites that should delay implementation?

Provide:
- **READY** / **NOT READY** / **READY WITH CONDITIONS** status
- Specific readiness gaps (if any)
- Conditions to be satisfied before implementation begins
```

### Expected Output

- A clear status: READY, NOT READY, or READY WITH CONDITIONS
- If NOT READY: specific gaps with remediation steps
- If READY WITH CONDITIONS: explicit conditions that must be satisfied before or during implementation
- Confirmation that design, spec, and tasks are in a consistent state

### Acceptance Checklist

- [ ] Design document is approved by all reviewer roles
- [ ] Spec document has concrete acceptance criteria, not vague statements
- [ ] Current batch has allowed and forbidden scope defined
- [ ] All prerequisites are verified (MET or documented exception)
- [ ] Environment is ready for implementation
- [ ] No unresolved design issues or open questions
- [ ] Batch scope is appropriate (not too large, not too small)

### Common Failure Modes

- **Approving without reading**: Skimming the design and spec without checking details. Every acceptance criterion and design decision should be reviewed.
- **Ignoring unresolved design issues**: "We'll figure that out during implementation" transfers design risk to the coding phase. Resolve before starting.
- **Ambiguous batch scope**: "Implement the feature" without specific allowed/forbidden scope creates ambiguity. Each batch must have clear boundaries.
- **Skipping environment readiness**: Finding out the DB isn't running or dependencies are missing after implementation starts wastes time. Verify before starting.
- **Overlooking prerequisites**: Assuming a prerequisite is met without verification. Each prerequisite should be explicitly checked off.

---

## 2. Batch Acceptance Review

### Purpose

Review a completed batch to determine whether it meets the acceptance criteria and is ready to be committed. This is the gate between implementation and the next batch.

### When to Use

- After each implementation batch is complete and quality gate passes
- Before committing a batch to the repository
- When a batch has changes that need acceptance sign-off
- Before marking a batch as complete in tasks.md

### Inputs to Provide

- **Batch scope**: The allowed and forbidden scope for the batch
- **Quality gate output**: Full output from the most recent quality gate run
- **Changed files**: List of files modified in this batch
- **Implementation summary**: Brief description of what was implemented
- **Test results**: Specific test counts and coverage numbers

### Forbidden Scope

- Do NOT approve a batch with a failing quality gate
- Do NOT approve a batch with skipped integration tests
- Do NOT approve a batch that modifies files outside the allowed scope
- Do NOT approve a batch that violates its forbidden scope
- Do NOT use `|| true` or bypass mechanisms in quality gate review

### Prompt Template

```
I need to perform batch acceptance review for a completed batch.

**Change**: [Change name]
**Batch**: [Batch number and name]

**Allowed scope for this batch**: [What the batch was allowed to touch]
**Forbidden scope for this batch**: [What the batch was NOT allowed to touch]

**Implementation summary**:
[Brief description of what was implemented]

**Changed files**:
- [File 1] — [Modification type: added/modified/deleted]
- [File 2] — [Modification type]
- [File 3] — [Modification type]

**Quality gate output**:
```
[paste full output]
```

Acceptance criteria:

### 1. Quality Gate Passes (BLOCKER)
- [ ] `bash scripts/run_quality_gate.sh` exits 0
- [ ] Ruff: 0 errors
- [ ] Unit tests: all pass, coverage >= [threshold]%
- [ ] Integration tests: all pass, 0 skipped
- [ ] Spec validation: all pass
- [ ] Secret scan: clean

### 2. Scope Compliance (BLOCKER)
- [ ] All changed files are within the allowed scope
- [ ] No files in the forbidden scope were modified
- [ ] No new functionality outside the batch scope was added

### 3. Test Completeness
- [ ] New code has corresponding tests
- [ ] Tests follow existing patterns (naming, structure, fixtures)
- [ ] No tests are skipped (unless documented and approved)

### 4. Commit Readiness
- [ ] Changed files are staged (not git add -A)
- [ ] Commit message follows project conventions
- [ ] git status --short shows expected files only

### 5. Documentation Updates
- [ ] tasks.md updated to mark this batch complete (if applicable)
- [ ] changelog.md updated (if this is the last batch of a phase)

Provide:
- **ACCEPTED** / **REJECTED** status
- For REJECTED: specific blocking issues with fix guidance
- For ACCEPTED: confirmation of all acceptance criteria
- Summary of test counts and coverage for the batch
```

### Expected Output

- A clear ACCEPTED or REJECTED status
- If REJECTED: specific BLOCKER items with remediation steps; non-blocker warnings
- If ACCEPTED: confirmation that all acceptance criteria are met; summary of test counts and coverage
- Confirmation that scope boundaries were respected

### Acceptance Checklist

- [ ] Quality gate passes (exit 0) — this is a BLOCKER
- [ ] All changed files are within the allowed scope
- [ ] No files in the forbidden scope were modified
- [ ] New code has corresponding tests
- [ ] No skipped integration tests
- [ ] No `|| true` or bypass mechanisms used
- [ ] Commit is ready with appropriate message format
- [ ] tasks.md is updated if this is a task-completing batch

### Common Failure Modes

- **Approving despite quality gate warnings**: "It's just a linting warning" or "the coverage is close enough." Quality gate must pass 100% — no exceptions.
- **Scope boundary violations**: A file outside the allowed scope was modified. Even a one-line change in a forbidden file is a violation.
- **Hidden new functionality**: A batch that implements more than its scope, hiding the extra work in existing files. Review diffs carefully for undocumented behavior.
- **Skipped tests not detected**: The quality gate shows all tests pass but doesn't highlight skipped tests. Always check the skip count explicitly.
- **Batch too large to review**: If the batch has too many changed files to review comfortably, it was too large. Note for future batch planning.

---

## 3. Forbidden-Scope Audit

### Purpose

Audit all changes in a batch to ensure no file outside the allowed scope was modified, and no change violates the batch's forbidden scope. This is a critical gate for maintaining clean module boundaries.

### When to Use

- After every implementation batch, before acceptance
- When investigating unexpected side effects of a change
- When a change involves multiple teams or modules
- Before merging a feature branch that may have scope issues

### Inputs to Provide

- **Allowed scope**: The explicit list of files, modules, or directories the batch can touch
- **Forbidden scope**: The explicit list of files, modules, or directories the batch must NOT touch
- **Changed files**: The actual list of files modified in the batch (from git diff or git status)
- **Product boundary**: Overall product scope constraints (if applicable)

### Forbidden Scope

- Do NOT approve violations based on "it was necessary" — scope changes must go through design revision
- Do NOT accept one-line changes to forbidden files as acceptable
- Do NOT overlook changes in test files that test forbidden behavior
- Do NOT allow adding new files outside the allowed scope without documented approval

### Prompt Template

```
I need to perform a forbidden-scope audit on this batch.

**Change**: [Change name]
**Batch**: [Batch number and name]

**Allowed scope**:
- [Directory or file pattern 1]
- [Directory or file pattern 2]

**Forbidden scope**:
- [Directory or file pattern 1] — MUST NOT be modified
- [Module 1] — MUST NOT be imported or called
- [Functionality 1] — MUST NOT be added or changed

**Changed files** (from git diff --name-only or git status):
```
[list of changed files]
```

Audit process:

### 1. Check Allowed Scope
- For each changed file: is it within the allowed scope?
- For each new file: is it within the allowed scope?
- List any file that is NOT within the allowed scope.

### 2. Check Forbidden Scope
- For each changed file: is it explicitly in the forbidden scope?
- For each change: does it import, call, or depend on anything in the forbidden scope?
- Does the change introduce any capability that was explicitly forbidden in the batch scope?

### 3. Check Product Boundary
- Does the change introduce functionality that violates the product boundary?
- Does it bypass any architectural constraint (e.g., human review, no auto-send)?
- Does it claim capabilities that don't exist?

### 4. Check Hidden Scope
- Does the change add configuration, dependencies, or infrastructure outside the scope?
- Does the change modify tests in ways that test unimplemented or out-of-scope behavior?
- Does the change add documentation that describes out-of-scope functionality?

### 5. Check Test File Scope
- Are test files within the allowed test scope for this batch?
- Do test changes only test the batch's allowed functionality?
- Do tests avoid importing or testing modules from other scope boundaries?

Provide:
- **CLEAN** / **VIOLATION FOUND** status
- For VIOLATION FOUND: each violation with file path, line reference, and scope rule violated
- For each violation: recommended action (revert, move to different batch, or get scope revision approval)
- Summary of compliance percentage (files in scope vs. total changed)
```

### Expected Output

- A CLEAN or VIOLATION FOUND status
- If VIOLATION FOUND: detailed list of each violation with file, scope rule, and recommended action
- For non-trivial violations: whether the change should be reverted, moved to a different batch, or needs scope revision
- Summary statistics: files in scope vs. total

### Acceptance Checklist

- [ ] Every changed file is verified against the allowed scope
- [ ] Every changed file is verified against the forbidden scope
- [ ] No imports or calls to forbidden modules were added
- [ ] No product boundary violations are present
- [ ] No hidden scope additions (config, dependencies, test of out-of-scope behavior)
- [ ] Test file changes are within the test scope for this batch

### Common Failure Modes

- **One-line exception**: "It's just one line in a forbidden file." A scope violation is a scope violation regardless of size. Either move the change to a different batch or get scope approval.
- **Import creep**: Adding an import from a module in the forbidden scope, even if the actual code path is never exercised in this batch. Imports create coupling and should be within scope.
- **Test scope mismatch**: Tests for the batch's functionality should be in the batch's test directory. Adding tests to a different test directory creates confusion.
- **Config file modification**: Modifying pyproject.toml, docker-compose.yml, or other config files outside the allowed scope can have wide-ranging effects. Config changes should be explicitly scoped.
- **Missing new file permissions**: A new file added to the allowed directory but not mentioned in the batch scope. Any new file should be documented in the scope.

---

## 4. Task Status Audit

### Purpose

Audit the tasks.md file to verify that all completed tasks have actually been implemented, tested, and quality-gated. This prevents tasks from being marked complete prematurely.

### When to Use

- Before archiving an OpenSpec change (full task audit)
- After each batch, before marking batch tasks as complete
- When tasks.md has not been updated in a while and needs reconciliation
- When investigating scope or quality issues that may have been hidden by premature task completion

### Inputs to Provide

- **Tasks file**: The tasks.md for the current OpenSpec change
- **Quality gate results**: The most recent quality gate output for each batch
- **Implementation evidence**: Links to implemented code and tests for each task
- **Change scope**: The approved design and spec for the change

### Forbidden Scope

- Do NOT mark tasks as complete without verifying implementation
- Do NOT skip the quality gate for any task involving code changes
- Do NOT mark documentation-only tasks as complete without verifying the docs exist
- Do NOT modify task scope without corresponding design revision

### Prompt Template

```
I need to audit the task status for this OpenSpec change.

**Change**: [Change name]
**Tasks file**: [path/to/tasks.md]

**Task breakdown by phase**:
- Phase 1: [name] — [N] tasks, [M] complete
- Phase 2: [name] — [N] tasks, [M] complete
- Phase 3: [name] — [N] tasks, [M] complete

Audit process:

### 1. Verify Completeness Claims
For each task marked [x] (complete):
- Is there evidence of implementation? (files created, code committed)
- If code task: was the quality gate run for this task?
- If docs task: does the document exist at the specified path?
- If test task: do the tests exist and pass?

For each task marked [ ] (incomplete):
- Is there a reason it's not yet complete?
- Is it blocked by another task or external dependency?
- Is it still relevant, or should it be deferred or removed?

### 2. Verify Sequencing
- Are tasks in the correct dependency order?
- Does any later task depend on an incomplete earlier task?
- Are there tasks that should be split into smaller subtasks?

### 3. Verify Accuracy
- Are task descriptions still accurate, or did the scope change during implementation?
- Do test counts mentioned in tasks match actual quality gate results?
- Are allowed/forbidden scope descriptions still correct?

### 4. Identify Gaps
- Are there implementation tasks that were completed but never added to tasks.md?
- Are there test tasks needed but not documented?
- Are there documentation or cleanup tasks that are easily forgotten?

Provide:
- **CLEAN** / **ISSUES FOUND** status
- For ISSUES FOUND: each issue with task reference and recommended fix
- Summary: total tasks, complete, incomplete, with verification evidence
- Any tasks that should be re-opened or split
```

### Expected Output

- A CLEAN or ISSUES FOUND status
- If ISSUES FOUND: list of tasks with discrepancies (claimed complete but not verified, incomplete without reason, incorrect sequencing)
- Summary statistics: total vs. complete vs. incomplete, with verification evidence
- Recommendations for re-opening, splitting, or reordering tasks

### Acceptance Checklist

- [ ] Every task marked complete has verifiable evidence of implementation
- [ ] Every code task has corresponding quality gate evidence
- [ ] Task descriptions are accurate and reflect actual implementation
- [ ] Task ordering respects dependencies
- [ ] No gaps (implemented work not tracked in tasks)
- [ ] Incomplete tasks have documented reasons and paths to completion

### Common Failure Modes

- **Premature completion marking**: A task marked complete because "the code was written" but tests weren't written or quality gate wasn't run. Verify both.
- **Drifted task descriptions**: The task says one thing but the implementation does something different. Either update the task or fix the implementation.
- **Orphaned tasks**: Tasks that were completed in the code but never updated in tasks.md. Keep tasks.md in sync with actual work.
- **Hidden dependencies**: Task B is blocked on Task A, but Task A is marked complete when it shouldn't be. Review dependency chains carefully.
- **Missing cleanup tasks**: Tasks for changelog update, phase status update, or archive preparation are easily forgotten. Include them explicitly.

---

## 5. Final Phase Acceptance

### Purpose

Perform the final acceptance review for an entire OpenSpec change, verifying that all batches are complete, all tasks are done, the quality gate passes, and the change is ready for archive. This is the last gate before archival.

### When to Use

- When all batches of an OpenSpec change are complete
- Before running the archive procedure
- When a change needs final sign-off from all reviewer roles
- Before promoting specs to the main specs directory

### Inputs to Provide

- **Completed change**: The full OpenSpec change directory
- **All batch results**: Quality gate outputs for every batch
- **Final quality gate output**: Most recent full quality gate run
- **Changelog**: The updated changelog.md with change entries
- **Phase status**: The updated phase_status.md
- **All reviewer sign-offs**: Evidence of review from each role

### Forbidden Scope

- Do NOT approve a change with incomplete tasks
- Do NOT approve a change with failing quality gate
- Do NOT approve a change with uncommitted changes
- Do NOT approve a change that has not been reviewed by all required roles
- Do NOT approve a change with skipped integration tests

### Prompt Template

```
I need to perform final phase acceptance for an OpenSpec change.

**Change**: [Change name]
**Change directory**: [path/to/change]

**Batch completion status**:
- Batch 1: [COMPLETE / INCOMPLETE] — Quality gate: [PASS/FAIL]
- Batch 2: [COMPLETE / INCOMPLETE] — Quality gate: [PASS/FAIL]
- Batch N: [COMPLETE / INCOMPLETE] — Quality gate: [PASS/FAIL]

**Final quality gate output**:
```
[paste full output]
```

**Reviewer sign-offs**:
- Project Director: [APPROVED / PENDING]
- System Architect: [APPROVED / PENDING]
- QA Evaluator: [APPROVED / PENDING]
- Phase Supervisor: [APPROVED / PENDING]

Final acceptance criteria:

### 1. All Tasks Complete (BLOCKER)
- [ ] All tasks in tasks.md are marked [x] (complete)
- [ ] Verified: each completed task has implementation evidence

### 2. All Batches Quality-Gated (BLOCKER)
- [ ] Every batch passed its quality gate
- [ ] Most recent quality gate passes (all stages)
- [ ] Integration tests: 0 skipped
- [ ] Coverage >= threshold

### 3. All Reviewer Sign-Offs Obtained (BLOCKER)
- [ ] Project Director: scope is correct, product boundary respected
- [ ] System Architect: architecture sound, data contracts consistent
- [ ] QA Evaluator: test strategy followed, coverage adequate
- [ ] Phase Supervisor: all gates passed, task completion verified

### 4. Documentation Complete
- [ ] changelog.md updated with change summary for all batches
- [ ] phase_status.md updated with acceptance status
- [ ] Spec validation passes (openspec validate --all)

### 5. Working Tree Clean
- [ ] git status --short shows no unexpected dirty files
- [ ] All change-related files are committed
- [ ] No partially implemented features remain in the codebase

### 6. Archive Readiness
- [ ] Archive command is understood and available
- [ ] Post-archive validation steps are documented
- [ ] No blocking issues that would prevent clean archive

Provide:
- **ACCEPTED** / **REJECTED** status
- For REJECTED: specific blocking issues with remediation steps
- For ACCEPTED: final summary with key metrics (test counts, coverage, batches)
- Go/no-go recommendation for archive
```

### Expected Output

- A clear ACCEPTED or REJECTED status
- If REJECTED: specific blocking issues categorized by the six criteria
- If ACCEPTED: summary of key metrics (total test counts, coverage, batches, files changed)
- Go/no-go recommendation for archive with supporting rationale
- Remaining non-blocking warnings (if any)

### Acceptance Checklist

- [ ] All tasks are complete and verified
- [ ] All batches passed quality gate (most recent pass confirmed)
- [ ] All four reviewer roles have approved
- [ ] changelog.md and phase_status.md are updated
- [ ] openspec validate --all passes
- [ ] Working tree is clean (no unexpected dirty files)
- [ ] No skipped integration tests
- [ ] No scope boundary violations across all batches
- [ ] Change is ready for archive

### Common Failure Modes

- **Rushing final acceptance**: Temptation to skip the final quality gate because "all batches passed individually." Always run the full gate one last time.
- **Missing reviewer sign-off**: One role didn't formally approve but it was "understood." Get explicit sign-off from each role.
- **Changelog incomplete**: Some batches have changelog entries while others don't. The changelog must cover every batch in the change.
- **Phase status not updated**: The phase_status.md still shows "IN PROGRESS" instead of "ACCEPTED." This creates confusion about project status.
- **Assuming archive is automatic**: Archive steps (validate, commit, archive command) are not automatic. Verify each step is understood and ready.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Implementation-Readiness Review | Verify batch readiness before coding | Pre-implementation gate |
| Batch Acceptance Review | Review completed batch for acceptance | Post-implementation, pre-commit |
| Forbidden-Scope Audit | Audit changes against scope boundaries | Every batch, pre-acceptance |
| Task Status Audit | Verify task completeness accuracy | Pre-archive, periodic reconciliation |
| Final Phase Acceptance | Final acceptance for whole change | Pre-archive, all batches complete |
