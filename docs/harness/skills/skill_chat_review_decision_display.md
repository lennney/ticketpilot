# Skill: ReviewDecisionDisplay Schema Pattern

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_chat_review_decision_display` |
| **Version** | 1.0.0 |
| **Created** | 2026-05-08 |
| **Last Updated** | 2026-05-08 |
| **Author** | Phase 15.6 Experience Consolidation |
| **Status** | `active` |

## Classification

| Field | Value |
|-------|-------|
| **Domain** | `chat` |
| **Pattern Type** | `best_practice` |
| **Complexity** | `simple` (2-3 steps) |

## Problem Statement

Need a lightweight, validated schema for passing structured decisions between Streamlit pages via session state. The data needs validation, timestamp tracking, and enum-like action field.

**Trigger Condition**: When implementing any cross-page data transport that needs validation and structure (review decisions, form submissions, action confirmations).

## Root Cause Analysis

Streamlit session state serializes data via JSON. Plain dicts lack validation, making errors hard to debug. Pydantic model with explicit fields provides validation, type hints, and automatic timestamp handling.

## Solution Pattern

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Define Pydantic model with required fields | Clear structure, validation |
| 2 | Add `@field_validator` for enum-like string fields | Enforce valid actions |
| 3 | Use `Field(default_factory=...)` for timestamps | Auto-generated with timezone |
| 4 | Include metadata fields for audit trail | reviewed_at, decision_reason |

### Code Examples

#### Pattern
```python
from pydantic import BaseModel, field_validator, Field
from datetime import datetime, timezone

class ReviewDecisionDisplay(BaseModel):
    action: str  # approve, edit, escalate, reject
    edited_text: str | None = None
    decision_reason: str = ""
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("action")
    @classmethod
    def action_must_be_valid(cls, v: str) -> str:
        valid_actions = {"approve", "edit", "escalate", "reject"}
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v
```

### Decision Tree

```
                    [Need cross-page data structure]
                         |
                         v
            +------------+------------+
            |                         |
      [Needs validation]        [No validation needed]
            |                         |
      Use Pydantic model       Use simple dict/None
            |                         |
      +-----+-----+                     |
      |           |                     |
  [Enum field] [Timestamp]         [Done]
      |           |
      v           v
  field_validator Field(default_factory)
```

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| Invalid action | `ReviewDecisionDisplay(action="invalid")` | Raises ValueError |
| None edited_text | `ReviewDecisionDisplay(action="edit")` | Works, edited_text=None |
| Timestamp auto-set | Create instance, check reviewed_at | UTC datetime present |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| `skill_chat_streamlit_multipage_handoff` | depends_on | Session state handoff pattern |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| Review decision not returned to chat | repair_playbook: Human Review Decision Handoff |

## Notes

- This is a "lightweight boundary schema" pattern — for data transport, not persistence
- For persistence, use the full domain models (ChatSession, DraftWithEvidence, etc.)
- The schema validates at boundary crossing, not at storage

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation from Phase 15.6 |