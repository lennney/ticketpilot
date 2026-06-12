# Review: 2026-06-11-guard-safe-language-classifier.md

**Verdict: REQUEST_CHANGES**

---

## Checklist

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Task granularity (2-5 min each) | ✅ PASS | Each task is ~5 min (test→fail→impl→pass→commit) |
| 2 | File paths (exact, not vague) | ✅ PASS | `src/ticketpilot/drafting/claim_guard.py` and `tests/unit/test_claim_guard.py` are exact |
| 3 | Code examples (complete, copy-pasteable) | ✅ PASS | Full test classes + full function bodies provided |
| 4 | Commands (exact with expected output) | ⚠️ Minor | Commands are exact; expected output is stated as "7 passed" / "6 passed" without actual pytest output format — works but imprecise |
| 5 | TDD (test first, code second) | ✅ PASS | Step 1 tests → Step 2 run to fail → Step 3 implement → Step 4 run to pass |
| 6 | Verification steps (prove each task works) | ✅ PASS | Step 4 runs pytest to verify |
| 7 | DRY (no unnecessary repetition) | ✅ PASS | Standard pytest style; no redundant logic |
| 8 | YAGNI (nothing over-engineered) | ✅ PASS | Pure string matching, no regex, no new dependencies, no schema changes |
| 9 | No missing context (implementer can execute without guessing) | ❌ FAIL | Keyword mismatch with spec (see critical issue) |
| 10 | Backward compatible (won't break existing tests) | ✅ PASS | New functions + new test classes only; no changes to existing logic |
| 11 | Dependencies (tasks in correct order) | ✅ PASS | Tasks 1 and 2 are independent; order doesn't matter |
| 12 | Integration (new code integrates cleanly) | ✅ PASS | Functions placed after `_check_risk_acknowledgment` (line 190) and before `check_claim_guard` (line 193) as specified |

---

## Critical Issues

### 1. Safe escalation keywords mismatch with spec (❌ MUST FIX)

**The spec** (`openspec/changes/add-guard-architecture-improvement-planning/specs/guard-architecture/spec.md`, lines 56-57) lists safe escalation keywords as:

> 人工处理, 转人工客服, 需要人工审核, 人工审查, **升级至人工**, **已升级人工**

**The plan** (line 78-84) uses:

> 人工处理, 转人工客服, 需要人工审核, 人工审查, **升级处理**

`"升级处理"` and `"升级至人工"` / `"已升级人工"` are **different substrings** that match different text:

| Input text | `"升级处理"` match | `"升级至人工"` match | `"已升级人工"` match |
|---|---|---|---|
| `"此案件已升级处理。"` | ✅ Yes | ❌ No | ❌ No |
| `"此案件已升级至人工处理。"` | ❌ No | ✅ Yes | ❌ No |
| `"此案件已升级人工处理。"` | ❌ No | ❌ No | ✅ Yes |

The plan must either align with the spec (change to 升级至人工, 已升级人工) or the spec must be amended. Since this is a spec-derived implementation plan, the plan should match the authoritative spec.

**Additionally**, the tasks.md (`openspec/changes/add-guard-architecture-improvement-planning/tasks.md`, line 26) lists:

> 人工处理, 转人工客服, 需要人工审核, 人工审查, 升级处理

This matches the plan but NOT the spec. There is a 3-way inconsistency: spec says one thing, tasks.md says another, plan follows tasks.md. The implementer would be confused about which source is authoritative.

**Suggested fix**: Change plan keywords to match the spec:

```python
_SAFE_ESCALATION_KEYWORDS = [
    "人工处理",
    "转人工客服",
    "需要人工审核",
    "人工审查",
    "升级至人工",
    "已升级人工",
]
```

And update the corresponding test cases and acceptance criteria.

---

## Important Issues

### 2. Keyword constants should be module-level, not local (🔶 SHOULD FIX)

The plan defines `_SAFE_ESCALATION_KEYWORDS` and `_MANUAL_REVIEW_KEYWORDS` as **local variables** inside their respective functions. However, the existing codebase consistently uses **module-level constants** for keyword/pattern lists:

- `_FORBIDDEN_PROMISE_PATTERNS` (module-level, line 74)
- `_HIGH_RISK_FLAGS` (module-level, line 87)
- `_ESCALATION_PATTERNS` (module-level, line 95)
- `_GREETING_PATTERNS` (module-level, line 104)

Having local variables breaks this convention. If these keyword lists need to be shared (e.g., by Task 14.4's `check_claim_guard()` integration), they'll need to be refactored later anyway.

**Suggested fix**: Move both keyword lists to module level:

```python
# Safe escalation keywords — draft is requesting/acknowledging human escalation
_SAFE_ESCALATION_KEYWORDS: list[str] = [
    "人工处理",
    "转人工客服",
    "需要人工审核",
    "人工审查",
    "升级至人工",
    "已升级人工",
]

# Manual review keywords — draft acknowledges need for human oversight
_MANUAL_REVIEW_KEYWORDS: list[str] = [
    "人工审核",
    "需人工 review",
    "人工确认",
    "需人工介入",
]
```

---

## Minor Issues

### 3. `tasks.md` missing "需人工介入" keyword (ℹ️ NOTE)

The spec includes `"需人工介入"` as a manual review keyword, and the plan correctly includes it. However, `tasks.md` (line 28) only lists:

> 人工审核, 需人工 review, 人工确认

This is a minor inconsistency between tasks.md and the plan/spec. `tasks.md` should be updated to include `需人工介入` for completeness.

### 4. Overlap between the two functions via "需要人工审核" / "人工审核" (ℹ️ NOTE)

`"需要人工审核"` (safe escalation) contains the substring `"人工审核"` (manual review). Any text containing "需要人工审核" will trigger **both** functions. For example, `"此问题需要人工审核。"` returns True for both `check_safe_escalation_language()` and `check_manual_review_acknowledgement()`.

This is arguably **by design** per the spec (both types describe valid but distinct guard signals), but the plan's acceptance criterion for Task 2 says:

> Distinct detection from `check_safe_escalation_language()` (no false overlap)

This wording is misleading — there IS overlap by construction. The implementer could misinterpret "no false overlap" as a requirement to make them mutually exclusive, which would require refactoring the keywords or adding exclusion logic that the spec doesn't call for.

**Suggested fix**: Rephrase the acceptance criterion to:

> Functions can both trigger on the same text when it contains overlapping keywords (e.g., "需要人工审核" triggers both). This is by design — each function serves a distinct guard purpose.

### 5. Expected test output format is imprecise (ℹ️ SUGGESTION)

The verification steps say "Expected: 7 passed" / "Expected: 6 passed". Showing the actual pytest summary line would be more helpful:

```
Expected: == 7 passed in 0.xxs ==
```

---

## Summary

The plan is structurally sound — TDD flow, file paths, placement instructions, and overall architecture are all correct. However, there is a **critical keyword mismatch with the spec** (升级处理 vs 升级至人工/已升级人工) that must be resolved before an implementer can execute without guessing. The **module-level vs local variable** inconsistency is important but less blocking.

**Fix required before implementation can proceed:** Resolve the safe escalation keyword set to match the authoritative spec, then update test cases and acceptance criteria accordingly.
