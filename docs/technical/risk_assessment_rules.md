# Risk Assessment Rules

## Overview

The risk assessment stage (Stage 3 of the pipeline) evaluates a normalized, classified ticket for potential risks using deterministic Chinese keyword matching. It produces a set of risk flags, a severity level, and a `must_human_review` decision.

**Source code:** `src/ticketpilot/risk/rules.py` (risk rule definitions), `src/ticketpilot/risk/assessor.py` (assessment logic)

## 8 Issue Types (Risk Flags)

### Substantive Flags (6)

These flags represent real business risks and contribute to severity calculation.

| Flag | Enum Value | Chinese Keywords | Business Context |
|------|-----------|-----------------|------------------|
| Complaint Risk | `COMPLAINT_RISK` | "投诉", "差评", "曝光", "媒体" | Customer threatening negative reviews or media exposure |
| Compensation Risk | `COMPENSATION_RISK` | "赔偿", "补偿", "3倍", "5倍", "惩罚性" | Customer demanding monetary compensation or punitive damages |
| Legal Risk | `LEGAL_RISK` | "律师", "法院", "起诉", "法律" | Customer mentioning legal action, lawyers, or courts |
| Privacy Risk | `PRIVACY_RISK` | "身份证", "证件号", "实名信息", "手机号", "地址信息", "泄露", "隐私", "个人信息" | Personal data exposure, privacy concerns, identity information |
| Account Security Risk | `ACCOUNT_SECURITY_RISK` | "盗号", "盗刷", "异常登录", "冻结" | Account compromise, unauthorized transactions, frozen accounts |
| Policy Conflict | `POLICY_CONFLICT` | "违反", "违规", "政策", "条款", "违约" | Customer claims company policy violation or breach of terms |

### Meta Flags (2)

These flags describe pipeline state rather than business risk. They are excluded from severity calculation.

| Flag | Enum Value | Trigger Condition |
|------|-----------|-------------------|
| Low Confidence | `LOW_CONFIDENCE` | Classification confidence < 0.7 threshold |
| Insufficient Evidence | `INSUFFICIENT_EVIDENCE` | Short ticket text (1-9 chars) with no order numbers or product info; also added by Stage 4 when retrieval returns empty results |

## Severity Logic

Severity is calculated from the **count of substantive flags only** (meta flags are excluded):

| Substantive Flag Count | Severity | Notes |
|-----------------------|----------|-------|
| 0 | `LOW` | No substantive risk flags triggered |
| 1 | `LOW` | Single substantive flag |
| 2 | `MEDIUM` | Two distinct substantive risk categories |
| 3+ | `HIGH` | Three or more substantive risk categories |
| LEGAL_RISK present | `HIGH` | Legal risk always overrides other severity calculations |

**Implementation detail** (`src/ticketpilot/risk/assessor.py`):
```python
substantive_flags = {
    f for f in flags
    if f not in (RiskFlag.LOW_CONFIDENCE, RiskFlag.INSUFFICIENT_EVIDENCE)
}
substantive_count = len(substantive_flags)
```

## `must_human_review` Behavior

The `must_human_review` field is `True` when **any** risk flags are present (including meta flags):

- `must_human_review = len(flags) > 0` — any flag triggers required human review
- Stage 4 (retrieval) also sets `must_human_review = True` when adding `INSUFFICIENT_EVIDENCE` via the `_with_added_risk_flag()` helper
- The draft generation stage preserves this: high-risk tickets get `must_human_review=True` in the `DraftReply`

## Meta Flags vs. Substantive Flags

| Aspect | Meta Flags | Substantive Flags |
|--------|-----------|-------------------|
| **Affect severity?** | No | Yes (count-based) |
| **Affect must_human_review?** | Yes | Yes |
| **Affect query expansion?** | No (excluded in query builder) | Yes (mapped to Chinese business terms) |
| **Examples** | LOW_CONFIDENCE, INSUFFICIENT_EVIDENCE | COMPLAINT_RISK, COMPENSATION_RISK, LEGAL_RISK, PRIVACY_RISK, ACCOUNT_SECURITY_RISK, POLICY_CONFLICT |

The query builder explicitly excludes meta flags from retrieval query expansion (`src/ticketpilot/retrieval/query_builder.py`):
```python
_META_FLAGS: set[RiskFlag] = {RiskFlag.LOW_CONFIDENCE, RiskFlag.INSUFFICIENT_EVIDENCE}
```

## Graceful Degradation

If the risk assessment stage itself fails (exception), the pipeline returns a safe default:
- Flags: `{LOW_CONFIDENCE}`
- Severity: `LOW`
- `must_human_review: True`

## Deferred Refinements

The following risk assessment refinements are explicitly deferred:

- **Real LLM-based risk classification** — Current rule-based keyword matching is brittle for nuanced tickets. An LLM-based assessor can use the same `RiskAssessor` interface.
- **Severity threshold tuning** — Current thresholds (0-1 LOW, 2 MEDIUM, 3+ HIGH) are initial values without empirical validation.
- **Confidence threshold tuning** — Current unified threshold of 0.7 was set during audit remediation; per-class thresholds may be more appropriate.
- **Risk flag test coverage for PRIVACY_RISK** — Deferred from audit remediation (GAP-1); not a critical gap but flagged for future improvement.
- **Contextual risk assessment** — Current rules match keywords anywhere in text. Future versions should consider negation, context, and intent-aware risk detection.
- **Temporal risk scoring** — Ticket frequency from same customer, historical complaint patterns, etc., are not tracked.
