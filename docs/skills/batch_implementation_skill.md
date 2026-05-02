# Batch Implementation Skill

## Purpose

Split a feature or change into independently testable, mergable batches with clearly defined allowed and forbidden scope. This ensures every batch can be implemented, tested, quality-gated, and committed without depending on future batches, reducing integration risk and review complexity.

## When to Use

- Starting implementation of an OpenSpec change that has been designed and specified
- Refactoring or migrating a large codebase change
- Any change that would require more than 3-5 files or touch multiple architectural layers
- Coordinating parallel work streams that must not conflict

## Required Inputs

- Approved design.md from the OpenSpec change
- Completed spec.md with requirements and scenarios
- Understanding of the existing module boundaries, data contracts, and dependency graph
- Quality gate script at `scripts/run_quality_gate.sh`

## Allowed Scope

- Grouping implementation into sequential batches
- Defining allowed scope (what each batch CAN touch)
- Defining forbidden scope (what each batch MUST NOT touch)
- Running quality gate after each batch
- Committing each batch independently
- Updating tasks.md as batches progress

## Forbidden Scope

- Do NOT implement code from a later batch in an earlier batch
- Do NOT create batches that depend on uncommitted future batches for correctness
- Do NOT modify code from a previous batch's scope in a later batch (unless explicitly a refactoring batch)
- Do NOT skip the quality gate between batches
- Do NOT merge a batch with failing tests or skipped integration tests
- Do NOT use `|| true` in quality gate invocations

## Step-by-Step Procedure

1. **Review the task breakdown**
   - Read `tasks.md` from the OpenSpec change
   - Verify each batch has clear allowed and forbidden scope
   - Check that no batch depends on uncommitted work from another batch

2. **Order batches by dependency**
   - Foundation first (schemas, interfaces, abstract classes)
   - Implementation second (concrete classes, business logic)
   - Integration and tests third (wiring, end-to-end flows)
   - Documentation and finalization last (changelog, phase status, archive)
   - If batch A needs batch B's output, batch B should come first

3. **For each batch, verify the scope boundary**
   - List every file or module the batch would modify
   - Compare against the batch's forbidden scope
   - If a file is in the forbidden scope, either move it to a different batch or get design approval for scope change

4. **Implement the batch**
   - Focus strictly on allowed scope
   - Write tests for the new code
   - Do not modify code outside the batch's scope
   - Do not "prep" for future batches by adding unused interfaces or hooks

5. **Run quality gate**
   - `bash scripts/run_quality_gate.sh`
   - Must pass with: Ruff clean, all unit tests pass (>=70% coverage), integration tests pass with 0 skips, OpenSpec validate passes, no secrets detected
   - If the quality gate fails, fix the issue before committing

6. **Commit the batch**
   - `git add <files>` (specific files only, not `git add -A`)
   - `git commit -m "type: batch description"`
   - Verify `git status --short` shows only expected files

7. **Update tasks.md** in the OpenSpec change directory to mark the batch as complete

8. **Repeat** for the next batch

## Acceptance Checklist

- [ ] Each batch has documented allowed and forbidden scope
- [ ] No batch depends on uncommitted future work
- [ ] All changes in a batch are within its allowed scope
- [ ] No changes in a batch violate its forbidden scope
- [ ] Quality gate passes after every batch
- [ ] 0 skipped integration tests (or explicit TICKETPILOT_SKIP_DB_TESTS=1 bypass noted)
- [ ] Each batch is committed independently with a descriptive message
- [ ] tasks.md updated to reflect batch completion

## Common Failure Modes

- **Creeping scope**: "While I'm here, I'll fix this too." Fixes outside the batch scope should either be deferred to a dedicated batch or explicitly approved. Unplanned scope creep is the #1 cause of unreviewable batches.
- **Hidden cross-batch dependencies**: Batch A adds a column that Batch B needs, but Batch A is committed before Batch B. Ensure batches are ordered so dependencies flow forward.
- **Quality gate skipped between batches**: "It's just a small change, I'll run the gate before the final merge." Small changes accumulate into large ones. Run the gate after every batch.
- **Overly large batches**: A batch touching 10+ files across 4+ modules is too large. Split it into smaller batches. A batch should take hours, not days, to implement and review.
- **Batch modifies previous batch's code**: If Batch 2 modifies code written in Batch 1, either Batch 1's scope was wrong or Batch 2's scope is too broad. Revisit the task breakdown.
- **Using `|| true` to bypass quality gate failures**: This hides real failures. If a stage fails, fix the underlying issue. Do not bypass.

## Reusable Claude Code Prompt Template

```
I am implementing [change name] from the approved OpenSpec change at `openspec/changes/<change-name>/`.

Here is the task breakdown:
[Paste tasks.md content relevant to the current batch]

For this batch (Batch N):
- **Allowed scope**: [list modules/files I can touch]
- **Forbidden scope**: [list modules/files I must NOT touch]

Implement this batch. Follow these rules:
1. Touch only files within the allowed scope
2. Do NOT touch any file in the forbidden scope
3. Write tests for any new code
4. After implementation, run `bash scripts/run_quality_gate.sh`
5. If quality gate fails, fix the issue
6. Do NOT use `|| true` to bypass quality gate stages
7. Do NOT lower coverage thresholds
8. Do NOT use `git add -A` — stage specific files only
9. Commit with message format: `type: <batch description>`
10. Update tasks.md to mark this batch complete
```

## TicketPilot Example

The connect-retrieval-to-intake-risk-pipeline change was split into 4 batches:

**Batch 1** (Schema + Evidence Mapper):
- Allowed scope: `src/ticketpilot/schema/evidence.py`, `src/ticketpilot/retrieval/evidence_mapper.py`, tests
- Forbidden scope: `pipeline.py`, `retrieval/pipeline.py`, DB migrations, any existing modules
- Tests: 20 new unit tests (11 evidence schema + 9 evidence mapper)
- Quality gate: 170 unit tests passed, 49 integration tests passed, 0 skipped

**Batch 2** (Query Builder + retrieve_evidence Wrapper):
- Allowed scope: `src/ticketpilot/retrieval/query_builder.py`, `src/ticketpilot/retrieval/retrieve_evidence.py`, tests
- Forbidden scope: `pipeline.py`, existing retrieval modules
- Tests: 22 new unit tests (13 query builder + 9 retrieve_evidence)
- Quality gate: 192 unit tests passed, 49 integration tests passed, 0 skipped

**Batch 3** (Pipeline Integration):
- Allowed scope: `src/ticketpilot/pipeline.py`, `tests/unit/test_pipeline_retrieval.py`
- Forbidden scope: Retrieval engine internals, classification, risk, intake
- Tests: 10 new unit tests (pipeline retrieval)
- Quality gate: 202 unit tests passed, 49 integration tests passed, 0 skipped

**Batch 4** (C.4 Export Cleanup + Integration Tests + Quality Gate):
- Allowed scope: `src/ticketpilot/retrieval/__init__.py`, `tests/unit/test_pipeline.py` (mock retrofit), `tests/integration/test_pipeline_retrieval_integration.py`
- Forbidden scope: Production code outside retrieval exports, existing integration test structure
- Tests: 6 new integration tests
- Quality gate: 202 unit + 55 integration = 257 passed, 0 skipped
