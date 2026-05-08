# Skill: PM-Style Requirements with Field Definitions

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_requirements_pm_style` |
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
| **Complexity** | `moderate` (3 sections) |

## Problem Statement

**Trigger Condition**: When creating requirements for a phase with data/API changes, requirements must include explicit field definitions to prevent implementation ambiguity.

**Context**: Requirements Analysis (Step 2 of Phase Loop) must produce specs detailed enough to code from without asking questions. This includes field definitions for all data structures.

## Solution Pattern

### Requirements Template (Product Manager Spec)

Requirements must be structured with:

| Section | Required | Description |
|---------|----------|-------------|
| Phase Information | Yes | Phase ID, task type, priority, OpenSpec reference |
| Functional Requirements | Yes | WHAT the system must do with FR-{number} format |
| Non-Functional Requirements | No | Performance, security, compatibility constraints |
| Constraints | Yes | Out-of-scope items and dependencies |
| Verification Plan | Yes | How to verify each requirement |

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Define phase info | Establish context and scope |
| 2 | Create FR-{number} entries | Trackable, testable requirements |
| 3 | Include field definitions for all data structures | Prevents implementation ambiguity |
| 4 | Specify API signatures if applicable | Contract between requirements and implementation |
| 5 | Define acceptance criteria per requirement | Clear pass/fail conditions |
| 6 | Document edge cases | Prevents unexpected behavior |
| 7 | Create verification plan | How to test each requirement |

### Code Examples

#### Before (Anti-Pattern - Ambiguous requirements)

```markdown
## Requirements
FR-1: Add pagination to ticket retrieval
- Should support pagination
- Page size should be configurable
```

Problem: Implementation must ask questions about:
- What parameters? (page, offset, cursor?)
- What range for page size? (1-100? unlimited?)
- What response format? (list + total count? cursor?)
- What happens on invalid page?

#### After (Solution - PM-style with field definitions)

```markdown
## Requirements Specification: Pagination

### Phase Information
- **Phase ID**: 15.5
- **Task Type**: [CODE]
- **Priority**: High

---

### Functional Requirements

#### FR-1: Pagination Support

| Field | Value |
|-------|-------|
| **ID** | FR-1 |
| **Title** | Add pagination to ticket retrieval |
| **Type** | `feature` |
| **Module** | retrieval/ |

**Description**:
Paginate the ticket retrieval endpoint to support large result sets.

**API Signature**:
```python
def get_tickets(
    page: int = 1,
    page_size: int = 20
) -> TicketListResponse
```

**Fields**:

| Field Name | Type | Required | Description | Valid Values / Constraints |
|------------|------|----------|-------------|-----------------------------|
| page | integer | Yes | Page number (1-indexed) | 1 to max_pages |
| page_size | integer | Yes | Results per page | 1-100 |
| total_count | integer | Yes | Total matching records | >= 0 |
| items | array | Yes | List of tickets | max length = page_size |

**Acceptance Criteria**:
- [ ] page=1 returns first page of results
- [ ] page_size=50 returns exactly 50 items (if available)
- [ ] page > max_pages returns empty items array
- [ ] page_size > 100 is clamped to 100

**Edge Cases**:
- page=0 -> return error (minimum is 1)
- page_size=0 -> return error (minimum is 1)
- page_size=500 -> clamp to 100

**Related Requirements**:
- FR-2 (sorting must work with pagination)
- FR-3 (filtering must work with pagination)

---

### Verification Plan

| FR ID | Verification Method | Expected Result |
|-------|---------------------|------------------|
| FR-1 | Unit test: test_pagination.py | All acceptance criteria pass |
```

### Field Definition Table Format

For data structures, always include:

```markdown
| Field Name | Type | Required | Description | Valid Values / Constraints |
|------------|------|----------|-------------|-----------------------------|
```

This table should appear in:
- API request/response structures
- Data class definitions
- Database schema definitions
- Configuration objects

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| All data fields have types | Requirements review | No " unspecified" types |
| All fields have constraints | Requirements review | No " any value" constraints |
| Acceptance criteria are testable | Review criteria vs test plan | Each criterion has corresponding test |
| Edge cases documented | Requirements review | All boundary conditions listed |
| API signatures present | Requirements review | Function signatures match implementation |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| `skill_workflow_phase_loop` | `related_to` | Phase Loop Step 2 uses this template |
| `skill_workflow_subagent_delegation` | `related_to` | Clear requirements enable proper delegation |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| Ambiguous requirements leading to rework | repair_playbook.md |

## Notes

- Requirements template from PHASE_LOOP.md Step 2
- Template uses Product Manager specification format
- Every field must have type, description, and constraints
- No ambiguous language ("should", "could", "may" -> use "must" for requirements)
- Edge cases are as important as happy path

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation from PHASE_LOOP.md Step 2 |