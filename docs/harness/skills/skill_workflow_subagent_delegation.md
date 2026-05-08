# Skill: Subagent Delegation for Code Tasks

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_workflow_subagent_delegation` |
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
| **Complexity** | `simple` (1 rule) |

## Problem Statement

**Trigger Condition**: When executing any [CODE] task, Controller must delegate to subagent, not implement directly.

**Root Cause**: Early versions allowed Controller to implement code, violating role separation and causing quality issues.

**Error Message** (if applicable):
```
Controller implemented code directly for task XYZ.
Subagent principle violated.
```

## Solution Pattern

### Core Rule

```
+------------------------------------------------------------------+
|  CONTROLLER NEVER IMPLEMENTS CODE DIRECTLY                        |
|  For [CODE] tasks: ALWAYS dispatch to backend-engineer subagent   |
|  Controller role = Orchestrate + Review + Approve                |
|  Controller NEVER = Implement + Write code                        |
+------------------------------------------------------------------+
```

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Identify task type from tasks.md marker | Determines delegation path |
| 2 | If [CODE]: dispatch to backend-engineer subagent | Controller does not implement |
| 3 | If [DOC]: Controller executes directly (no code changes) | Doc-only tasks are Controller's domain |
| 4 | Verify subagent result file is produced | Ensures delegation happened |
| 5 | Controller reviews subagent output | Maintains quality gate |

### Code Examples

#### Before (Anti-Pattern)

```python
# Controller violates subagent principle
async def execute_phase(phase_id):
    plan = create_plan(phase_id)

    # WRONG: Controller implements directly
    code = await controller.implement(plan)  # VIOLATION
    result = await controller.review(code)
    await commit(result)
```

#### After (Solution)

```python
# Controller orchestrates, subagent implements
async def execute_phase(phase_id):
    plan = create_plan(phase_id)

    # CORRECT: Dispatch [CODE] to backend-engineer
    result = await dispatch_subagent(
        agent_type="backend_engineer",
        task=plan,
        output_file=f"subagent_results/{phase_id}_result.md"
    )

    # Controller reviews subagent output
    review = await dispatch_subagent("code_reviewer", result)
    await commit_if_passed(review)
```

### Delegation Matrix

| Task Type | Who Executes | Controller Role |
|-----------|--------------|-----------------|
| [CODE] | subagent (backend-engineer) | Orchestrate + review |
| [DOC] | Controller (self) | Execute directly |
| [DATA] | subagent or Controller | Orchestrate or execute |
| [TEST] | subagent (backend-engineer) | Orchestrate + verify |
| [AUTO] | Controller (self) | Execute + report |

### Decision Tree

```
                    [Task loaded from tasks.md]
                                 |
                    [Check TYPE marker]
                                 |
            +--------------------+--------------------+
            |                     |                    |
       [CODE]                [DOC]                [DATA/TEST/AUTO]
            |                     |                    |
            v                     v                    v
    Dispatch to              Controller            Dispatch to
    backend-engineer         executes              appropriate
    subagent                 directly              agent
    (NEVER self)             (self)                (self or subagent)
```

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| [CODE] tasks delegated | Verify subagent_results/{task}_result.md exists | File present for each [CODE] task |
| Controller not in implementation | Check git diff | Controller commits only in subagent_results/ |
| Review happens post-delegation | Verify code-reviewer output | Review file exists |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| `skill_workflow_phase_loop` | `related_to` | Parent workflow that uses this rule |
| `skill_requirements_pm_style` | `related_to` | Requirements enable delegation |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| Controller implements code directly | error_memory.jsonl - Lesson 1 |

## Notes

- This is a hard rule, not a guideline
- [CODE] without delegation = process violation
- Controller can review, approve, reject - but never write implementation code
- subagent_results/ directory is evidence of proper delegation

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation from PHASE_LOOP.md Lesson 1 |