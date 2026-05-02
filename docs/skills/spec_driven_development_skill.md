# Spec-Driven Development Skill

## Purpose

Ensure every non-trivial feature or change starts with an OpenSpec change before any implementation code is written. This prevents uncontrolled code generation, requirement drift, and untestable outcomes by enforcing a structured lifecycle: proposal, design, spec, tasks, implementation, quality gate, and archive.

## When to Use

- Starting a new feature or non-trivial enhancement
- Making any change that could affect more than one module or introduce new data contracts
- Adding a new pipeline stage, provider, or integration point
- Any change requiring acceptance criteria beyond "works on my machine"
- Do NOT use for trivial bug fixes, typo corrections, or documentation-only changes that have no spec impact

## Required Inputs

- A clear problem statement or feature request
- Understanding of the existing system architecture, data contracts, and quality gate constraints
- Access to the OpenSpec CLI (`openspec`)

## Allowed Scope

- Creating OpenSpec proposals, designs, specs, and tasks
- Defining acceptance criteria before implementation
- Iterating on design documents within the change directory
- Updating tasks.md as batches are completed
- Archiving completed changes (see openspec_archive_skill.md)

## Forbidden Scope

- Do NOT write implementation code before spec approval
- Do NOT skip the proposal or design phase for changes that affect multiple modules
- Do NOT modify promoted specs in `openspec/specs/` without a corresponding change in progress
- Do NOT use `|| true` in quality gate scripts to hide failures
- Do NOT skip the quality gate before archive

## Step-by-Step Procedure

1. **Explore and clarify requirements**
   - Use `openspec explore` to investigate the problem space, existing constraints, and potential approaches
   - Identify all modules that would be affected by the change
   - Review related OpenSpec changes in `openspec/changes/archive/` for patterns and deferred items

2. **Propose the change**
   - Use `openspec propose` to generate the change directory with proposal, design, and initial tasks
   - The proposal should state: what problem is being solved, what approach is taken, what is explicitly out of scope

3. **Review the design**
   - Review `design.md` with system architect, QA evaluator, and phase supervisor agents
   - Verify the design addresses all constraints in the existing system (quality gate, data contracts, product boundary)
   - Update the design with review feedback before proceeding

4. **Create the specification**
   - Create `spec.md` in `openspec/changes/<change-name>/specs/<component>/spec.md`
   - Each requirement should have a corresponding scenario (Gherkin-style: WHEN/THEN)
   - Include a test strategy section specifying what to test and what NOT to test
   - Reference concrete thresholds and acceptance numbers, not aspirational targets

5. **Break down into tasks**
   - Populate `tasks.md` with phases and batches
   - Each batch should be independently testable and mergable
   - Define allowed and forbidden scope per batch
   - Order batches so foundation work comes before dependent work

6. **Implement in batches**
   - For each batch: implement -> test -> quality gate -> commit
   - Update tasks.md as each batch completes
   - Run the quality gate after every batch

7. **Finalize and archive**
   - Run final quality gate (ruff, unit tests, integration tests with 0 skips, OpenSpec validate --all, secret scan)
   - Update changelog.md and phase_status.md
   - Archive the change using `openspec archive` (see openspec_archive_skill.md)

## Acceptance Checklist

- [ ] Change directory exists at `openspec/changes/<change-name>/` with proposal, design, spec, and tasks
- [ ] design.md reviewed by project-director, system-architect, qa-evaluator, phase-supervisor
- [ ] spec.md has requirements with Gherkin scenarios and test strategy
- [ ] tasks.md defines batches with allowed/forbidden scope
- [ ] Every batch was implemented independently and passed quality gate
- [ ] changelog.md updated with all batch summaries
- [ ] phase_status.md updated
- [ ] `openspec validate --all` passes
- [ ] Change archived cleanly with `git status --short` showing no dirty files

## Common Failure Modes

- **Skipping the design phase**: Proceeding directly from idea to implementation leads to requirement drift and rework. The design document is the cheapest place to catch mistakes.
- **Vague acceptance criteria**: "Works correctly" is not testable. Each criterion must have a concrete, measurable pass condition.
- **Over-scoping a single batch**: Batches that touch too many modules are hard to review and harder to merge. If a batch needs more than 3-5 files changed, consider splitting it.
- **Spec and implementation diverging**: When the spec says one thing and the code does another, neither is trustworthy. Keep specs in sync during implementation, not after.
- **Delaying quality gate to the end**: Running quality gate only before archive means finding failures late. Run it after every batch.

## Reusable Claude Code Prompt Template

```
I need to implement [describe feature or change]. Use spec-driven development:

1. First, help me clarify the requirements by exploring the problem space.
   - What modules would this affect?
   - What constraints from the existing architecture apply?
   - What is explicitly out of scope?

2. Create an OpenSpec change called `<change-name>` with:
   - A proposal describing the problem and approach
   - A design document covering architecture, data flow, and key decisions
   - A spec with requirements and Gherkin scenarios
   - A task breakdown into independently testable batches

3. After spec approval, implement each batch one at a time:
   - Implement code
   - Write tests
   - Run quality gate
   - Commit

4. Finalize with changelog update, phase status update, and archive.

Do write: proposal -> design -> spec -> tasks -> batch 1 -> test -> gate -> commit -> batch 2 -> ...
Do NOT write: implementation code before the spec is approved.
```

## TicketPilot Example

When implementing the human review console (Stage 1D), the process was:

1. **Explore**: Identified that review schemas, a persistence store, and a console UI were needed. Reviewed the existing pipeline output types and drafting schemas to understand the data contracts.

2. **Propose**: Created `openspec/changes/add-human-review-console/` with a proposal describing the review workflow, audit trail requirements, and the "no auto-send" constraint.

3. **Design**: The design covered ReviewAction enum (APPROVE/EDIT/ESCALATE/REJECT), ReviewDecision Pydantic model with 15+ audit fields, ReviewStore with append-only JSONL, and Streamlit console as MVP. Reviewed and approved by all four agents.

4. **Spec**: Created `spec.md` with requirements for each schema field, store operations, and console behavior. Included scenarios for each review action, no-auto-send verification, and skip-count guard behavior.

5. **Tasks**: Three batches:
   - Batch 1: Schema + store (22 unit tests)
   - Batch 2: Streamlit console (40 unit tests for pure helper functions)
   - Batch 3: Integration tests + documentation + quality gate (9 integration tests)

6. **Implementation**: Each batch was implemented, tested, and quality-gated independently. No batch modified code from previous batches or existing modules (pipeline.py, drafting, retrieval, risk, intake, classification, database).

7. **Finalization**: 325 unit tests passed, 74 integration tests with 0 skipped, Ruff clean, OpenSpec validate 11/11 passed, quality gate PASSED. Archived with clean working tree.
