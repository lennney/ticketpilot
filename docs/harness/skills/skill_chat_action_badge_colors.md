# Skill: Color-Coded Action Badge Pattern

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `skill_chat_action_badge_colors` |
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
| **Complexity** | `simple` (1-2 steps) |

## Problem Statement

Need consistent color coding for action buttons/status indicators in chat UI. Users should be able to quickly scan and understand action states (approve=green, reject=red, etc.).

**Trigger Condition**: When implementing review actions, status indicators, or any categorical state display in chat UI.

## Root Cause Analysis

Inline styles with HTML are needed for color coding in Streamlit markdown. Color choices must follow semantic conventions (green=positive, red=negative) to avoid confusion.

## Solution Pattern

### Steps

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Define color map as module constants | Single source of truth |
| 2 | Render using Streamlit markdown with inline HTML | `unsafe_allow_html=True` required |
| 3 | Use semantic colors (green=approve, red=reject) | Convention matches intuition |
| 4 | Include fallback for unknown actions | Gray (#6b7280) |

### Code Examples

#### Pattern
```python
# Module constants
ACTION_COLORS = {
    "approve": "#16a34a",    # green - positive action
    "edit": "#ca8a04",        # yellow - modification needed
    "escalate": "#ea580c",   # orange - needs attention
    "reject": "#dc2626",      # red - negative action
}

ACTION_LABELS = {
    "approve": "已批准",
    "edit": "已编辑",
    "escalate": "已升级",
    "reject": "已拒绝",
}

def render_action_badge(action: str) -> str:
    color = ACTION_COLORS.get(action, "#6b7280")  # fallback gray
    label = ACTION_LABELS.get(action, action.upper())
    return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{label}</span>'

# Usage in Streamlit
st.markdown(render_action_badge("approve"), unsafe_allow_html=True)
```

### Decision Tree

```
                    [Need color-coded status]
                         |
                         v
            +------------+------------+
            |                         |
      [Review actions]           [General status]
            |                         |
      Use ACTION_COLORS          Define own color map
      with semantic mapping      per domain
            |                         |
            v                         v
      approve=green, etc.        Match domain semantics
```

## Validation

| Check | Method | Expected Result |
|-------|--------|------------------|
| All actions have color | Render each action badge | No missing colors |
| Fallback works | Render unknown action | Gray badge with action name |
| HTML safe | Render all badges | No XSS issues |

## Related Skills

| Skill ID | Relationship | Notes |
|----------|--------------|-------|
| `skill_chat_review_decision_display` | related_to | Uses action badges to display decisions |

## Related Errors

| Error Pattern | Error Memory Entry |
|--------------|-------------------|
| Review decision not visible | repair_playbook: Human Review Decision Handoff |

## Notes

- Always include `unsafe_allow_html=True` in st.markdown
- Color hex values should be in standard CSS format
- Font size 12px works well for inline badges
- Border-radius 4px gives slightly rounded corners

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation from Phase 15.6 |