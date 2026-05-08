# Skill: Phase Loop Workflow

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_workflow_phase_loop` |
| **Version** | 1.0.0 |
| **Created** | 2026-05-08 |
| **Last Updated** | 2026-05-08 |
| **Author** | Controller (auto-generated) |
| **Status** | `active` |

## Classification

| Field | Value |
|-------|-------|
| **Domain** | `workflow` |
| **Pattern Type** | `best_practice` |
| **Complexity** | `complex` (7 steps) |

## Problem Statement

**Trigger Condition**: When executing a phase from tasks.md, the Controller must orchestrate a 7-step workflow to ensure quality and systematic failure handling.

**Context**: Each phase (logical unit of work from tasks.md) requires: planning, requirements analysis, implementation, review, doc review, experience consolidation, and coordination. Code review failures must enter Fix Phase before retry.

## Solution Pattern

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | **PLANNER**: Create/modify step-by-step plan with acceptance criteria | Ensures clear execution path before starting |
| 2 | **REQUIREMENTS ANALYSIS**: Convert plan to concrete requirements with field definitions | Eliminates ambiguity for implementation |
| 3 | **IMPLEMENTATION**: Execute based on requirements (ALWAYS delegate [CODE] tasks) | Proper role separation |
| 4 | **REVIEW**: Verify implementation against requirements | Quality gate before proceeding |
| 5 | **DOC REVIEW**: Verify documentation accuracy and completeness | Ensures docs match implementation |
| 6 | **EXPERIENCE CONSOLIDATION**: Extract learnings, codify patterns | Continuous improvement |
| 7 | **CONTROLLER COORDINATION**: Orchestrate handoffs, decide next action | Final decision point |

### Phase Loop Diagram

```
+-----------------------------------------------------------------------+
|                         PHASE LOOP (7 steps)                          |
+-----------------------------------------------------------------------+
|  [1] PLANNER -> [2] REQUIREMENTS -> [3] IMPLEMENTATION              |
|       -> [4] REVIEW -> [5] DOC REVIEW -> [6] EXPERIENCE -> [7] CTRL  |
+-----------------------------------------------------------------------+

    Loop back: Review/Doc fails -> Fix Phase (F1-F5) -> back to [3]
    Phase done: All steps pass -> commit + push -> next phase
```

### Fix Phase (Review/Doc Failure)

When Review [4] or Doc Review [5] fails:

| Sub-step | Action | Output |
|----------|--------|--------|
| F1 | Issue Documentation | Record findings with evidence |
| F2 | Root Cause Analysis | Determine WHY failure occurred |
| F3 | Skill Codification | Create/update skill if new pattern |
| F4 | Fix Plan | Create specific fix guidance |
| F5 | Retry Decision | Loop back (max 3) or escalate |

**Max Retries**: 3 total per phase
**Escalation Trigger**: After 3rd retry failure

### Code Examples

#### Before (Anti-Pattern - Controller implements directly)

```python
# Controller does implementation for [CODE] task
def execute_phase(phase_id):
    controller = Controller()
    plan = controller.create_plan()
    # Controller writes code directly - VIOLATION
    code = controller.implement(plan)  # WRONG
    controller.review(code)
```

#### After (Solution - Proper delegation)

```python
# Controller orchestrates, subagent implements
def execute_phase(phase_id):
    controller = Controller()
    plan = controller.create_plan()      # Step 1: Planner

    # Step 2: Requirements Analysis (dispatched to subagent)
    requirements = dispatch_to_subagent("requirements_analysis", plan)

    # Step 3: Implementation (NEVER Controller - always backend-engineer)
    result = dispatch_to_subagent("backend_engineer", requirements)

    # Step 4-5: Review (code-reviewer), Doc Review
    review_result = dispatch_to_subagent("code_reviewer", result)
    doc_result = controller.doc_review(result)

    # Step 6-7: Experience, Coordination
    controller.experience_consolidation(result, review_result)
    controller.coordinate_and_decide()  # commit or Fix Phase
```

### Decision Tree

```
                    [Phase loaded from tasks.md]
                                 |
                    [Check task TYPE marker]
                                 |
            +--------------------+--------------------+
            |                     |                    |
       [CODE]                [DOC]                [DATA/TEST/AUTO]
            |                     |                    |
    Dispatch to            Controller does        Dispatch appropriately
    backend-engineer       (no code changes)         |
            |                     |                    |
            v                     v                    v
      [3] Implementation    [3] Implementation    [3] Implementation
      (subagent)           (Controller self)     (subagent or self)
            |                     |                    |
            v                     v                    v
         [4-7] Loop          [4-7] Loop           [4-7] Loop
```

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| All 7 steps executed | Checklist review | Each step has output file |
| [CODE] delegated | Verify subagent result file exists | subagent_results/{task}_result.md present |
| Fix Phase on failure | Verify F1-F5 executed before retry | Fix guidance file exists |
| Max 3 retries | Count retry entries | No more than 3 retry cycles |
| Commit criteria | All steps pass | All 7 steps complete, commit triggered |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| `skill_workflow_subagent_delegation` | `depends_on` | Explains delegation rules |
| `skill_requirements_pm_style` | `depends_on` | PM-style requirements template |
| `skill_workflow_fix_phase` | `child` | Detailed Fix Phase workflow |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| Controller implements code directly | Lesson 1 in PHASE_LOOP.md |
| Context compression mid-work | Lesson 2 in PHASE_LOOP.md |

## Notes

- Controller NEVER implements code directly for [CODE] tasks
- On context compression: check subagent status FIRST before compressing
- All tasks must have [CODE]/[DOC]/[DATA]/[TEST]/[AUTO] marker
- Unmarked tasks default to [CODE] (delegate)
- Handoff outputs go to subagent_results/{phase}_{step}.md

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation from PHASE_LOOP.md |