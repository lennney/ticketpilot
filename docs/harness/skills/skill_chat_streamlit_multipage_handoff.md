# Skill: Streamlit Multipage Session State Handoff

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_chat_streamlit_multipage_handoff` |
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
| **Complexity** | `moderate` (3-4 steps) |

## Problem Statement

Need to pass complex data (Pydantic models, ChatSession) between Streamlit multipage pages without serialization issues. Data must survive page navigation and be accessible to the receiving page.

**Trigger Condition**: When implementing cross-page data flow in Streamlit multipage app (e.g., passing ChatSession to review console, passing form data between wizard steps).

## Root Cause Analysis

Streamlit multipage apps share session state but navigate via `st.query_params`. Simple variable assignment breaks on rerun. Need deep copy to prevent mutation, proper session state management for cross-page access, and clear separation between navigation (query params) and data transport (session state).

## Solution Pattern

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Use `st.session_state` for cross-page data | Query params only handle navigation, not data |
| 2 | Deep copy before storing: `session.model_copy(deep=True)` | Prevent mutation from other pages |
| 3 | Use Pydantic model for the data structure | Validation ensures data integrity |
| 4 | Clear session state after processing | Avoid stale data on re-entry |
| 5 | Use `st.query_params` for navigation only | Page selection, not data transport |

### Code Examples

#### Before (Anti-Pattern)
```python
# Sending page - broken on rerun
st.session_state["pending_session"] = session  # shallow copy, may mutate
st.query_params["page"] = "review"  # data lost on rerun

# Receiving page
session = st.session_state.get("pending_session")  # may be stale or None
```

#### After (Solution)
```python
# Sending page (app.py)
if st.button("进行人工审核", type="primary"):
    st.session_state.pending_review_session = session.model_copy(deep=True)
    st.query_params["page"] = "review"
    st.rerun()

# Receiving page (2_review_console.py)
session = st.session_state.get("pending_review_session")
if not session:
    st.warning("No review session found.")
    st.stop()
```

### Decision Tree

```
                    [Need cross-page data]
                         |
                         v
            +------------+------------+
            |                         |
      [Complex data]            [Simple data]
            |                         |
      Use session_state +       Use query_params
      deep copy + pydantic     (navigation only)
            |                         |
            v                         v
      [Receiving page]          [Receiving page]
      reads from session       reads from query
```

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| Data integrity | Navigate full flow, verify data on receiving page | All fields match |
| No stale data | Re-enter flow, verify fresh state | No previous data |
| Mutation safety | Modify data on receiving page, check source | Source unchanged |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| `skill_chat_review_decision_display` | depends_on | Uses Pydantic model pattern |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| Human review flow broken | repair_playbook: Human Review Decision Handoff |

## Notes

- Deep copy is critical — shallow copy leads to mutation propagation
- Clear session state after use to avoid confusion on re-entry
- If data needs persistence across page navigations, consider storing in ChatSession (which is persisted)

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation from Phase 15.6 |