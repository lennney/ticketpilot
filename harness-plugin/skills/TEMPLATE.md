# Skill Template

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_{domain}_{short_description}` (e.g., `skill_retrieval_class_collision`) |
| **Version** | `1.0.0` |
| **Created** | YYYY-MM-DD |
| **Last Updated** | YYYY-MM-DD |
| **Author** | Controller (auto-generated) or human |
| **Status** | `active` / `deprecated` / `superseded` |

## Classification

| Field | Value |
|-------|-------|
| **Domain** | `retrieval` / `drafting` / `agent` / `intake` / `review` / `pipeline` / `workflow` |
| **Pattern Type** | `error_fix` / `best_practice` / `anti_pattern` / `optimization` / `configuration` |
| **Complexity** | `simple` (1 step) / `moderate` (2-3 steps) / `complex` (4+ steps) |

## Problem Statement

<!-- What problem does this skill solve? Be specific. -->

**Trigger Condition**: When does this skill apply? (e.g., "When code-reviewer reports class name collision")

**Error Message** (if applicable):
```
Paste error message or pattern here
```

## Root Cause Analysis

<!-- Why does this problem occur? -->

<!-- What are the contributing factors? -->

## Solution Pattern

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | | |
| 2 | | |
| 3 | | |

### Code Examples

#### Before (Anti-Pattern)
```python
# Problematic code
```

#### After (Solution)
```python
# Corrected code
```

### Decision Tree

```
                    [Condition A]
                         |
            +------------+------------+
            |                         |
      [Yes] |                    [No] |
            |                         |
     [Action 1]              [Check B]
                                  |
                         +--------+--------+
                         |                 |
                   [Yes] |             [No] |
                         |                 |
                  [Action 2]       [Action 3]
```

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| | | |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| | `supersedes` / `related_to` / `depends_on` | |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| | |

## Notes

<!-- Additional context, edge cases, known limitations -->

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | YYYY-MM-DD | Initial creation |
