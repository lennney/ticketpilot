# Review: 2026-06-11-scoring-classifier.md

**RE-REVIEW VERDICT: APPROVED ✅**

All 3 critical + 4 important issues from first review are resolved:

| Issue | Status |
|-------|--------|
| C1: Line range 55-103 + own return statement | ✅ Fixed |
| C2: `_score_intents` signature (no `excluded` param) | ✅ Fixed |
| C3: Genuine failing TDD test | ✅ `test_scoring_overrides_priority_order` added |
| I1: Placeholder test removed | ✅ `test_exclusion_penalty_reduces_score` has real body |
| I2: Working directory note | ✅ Added at top |
| I3: Unused imports cleanup | ✅ Step in Task 1 |
| I4: Confidence verification | ✅ Step 5 verifies |

Plan is complete and ready for execution.

---

**Original review below:**


**Reviewer:** Hermes Agent  
**Date:** 2026-06-11  
**Verdict: REQUEST_CHANGES**

---

## Checklist

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Task granularity (2-5 min each?) | ✓ |
| 2 | File paths (exact, not vague?) | ✗ |
| 3 | Code examples (complete, copy-pasteable?) | ✗ |
| 4 | Commands (exact with expected output?) | ✓ |
| 5 | TDD (test first, code second?) | ✗ |
| 6 | Verification steps (prove each task works?) | ✓ |
| 7 | DRY (no unnecessary repetition?) | ✓ |
| 8 | YAGNI (nothing over-engineered?) | ✗ |
| 9 | No missing context (implementer can execute without guessing?) | ✗ |
| 10 | Backward compatible (won't break existing tests?) | ✗ |
| 11 | Dependencies (tasks in correct order?) | ✓ |
| 12 | Integration (new code integrates cleanly?) | ✗ |
| 13 | Scope integrity (files listed == files that need changing?) | ✓ |
| 14 | Spec alignment (constants match authoritative spec?) | ✓ |

---

## Critical Issues

### C1 [Backward Compat / Integration] — Line range "55-78" causes SyntaxError + dead code overwrite

**Severity: CRITICAL** — will produce broken code if followed literally.

The plan says: *"Replace lines 55-78 (Phase 2) in classifier.py"*. This range does **not** include:

- **Line 79:** `if match_count > 0:` / `break` — When the new scoring code replaces lines 55-78, line 79 remains as an orphaned `break` **outside any loop**. Python raises `SyntaxError: 'break' outside loop`.

- **Lines 81-103:** The old confidence calculation and `return ClassificationResult(...)` remain below. The new code in the plan sets `matched_intent` and `confidence` as local variables, then **falls through** to the old confidence logic at lines 81-97, which **overwrites** the new confidence with the old values (e.g., CONFIDENCE_KEYWORD_WITH_ORDER = 0.88 instead of CONFIDENCE_HIGH = 0.78).

**Fix needed:** The replacement range must be `lines 55-103` (the entire Phase 2 + confidence logic + return statement), and the new code snippet must include its own `return ClassificationResult(...)`.

---

### C2 [Integration / Code Example] — `_score_intents` signature has orphaned `excluded` parameter; call site omits it → TypeError

**Severity: CRITICAL** — will crash at runtime.

The method signature reads:

```python
def _score_intents(self, text: str, excluded: set[IntentClass]) -> dict[str, float]:
```

But the call site reads:

```python
scores = self._score_intents(text)
```

This passes only 1 positional argument where 2 are required. Python raises `TypeError: IntentClassifier._score_intents() missing 1 required positional argument: 'excluded'`.

The `excluded` parameter is never used inside the method body (all exclusion logic is inline within the same loop). It serves no purpose.

**Fix needed:** Remove `excluded: set[IntentClass]` from the method signature (or make it optional with `= None`).

---

### C3 [TDD] — Proposed new tests do NOT fail under current code; no "red" phase

**Severity: CRITICAL** — undermines the TDD workflow the plan claims to follow.

Every proposed new test already passes under the **current** first-match-wins implementation:

| Proposed test | Text | Why it already passes |
|---------------|------|----------------------|
| `test_multi_intent_text_scores_both` | "退款投诉" | REFUND (priority #1) matches "退款" under first-match-wins → already returns REFUND |
| `test_complaint_wins_with_more_keywords` | "我要投诉态度太差" | No earlier-rule keyword matches; COMPLAINT (priority #7) matches "投诉" → already returns COMPLAINT |
| `test_no_keywords_returns_other` | "今天天气不错" | No rule matches at all → already returns OTHER |
| `test_strong_indicator_still_fast_path` | "我要12315投诉你们" | Phase 1 strong indicator "12315投诉" → already fast-paths to COMPLAINT |

A TDD test that exercises the **differentiating** behavior of scoring would need a case where first-match-wins produces the **wrong** result but scoring produces the **right** one. For example: a text that matches both a high-priority rule (weakly) and a low-priority rule (strongly with more keyword hits), where scoring should pick the low-priority rule. Example:

> "退款！东西坏了，投诉，12315，过期变质，态度太差"  
> Under first-match-wins: REFUND (退款 → first 25 lines matches, wins).  
> Under scoring: COMPLAINT has 投诉(2)+坏(2)+过期(2)+变质(2)+态度(2)+差(2)+12315(5)≈17pts vs REFUND's 退款(2)≈2pts → COMPLAINT wins.

A test asserting `COMPLAINT` here would properly fail before the change and pass after.

**Fix needed:** Add at least one test where scoring produces a **different outcome** than first-match-wins.

---

## Important Issues

### I1 — `test_refund_with_exclusion_penalty` is incomplete (just `pass`)

**Severity: IMPORTANT**

The test body is:

```python
def test_refund_with_exclusion_penalty(self):
    ...
    pass
```

This is a placeholder. It must either be completed with a real assertion (including the expected confidence reflecting the penalty) or removed.

---

### I2 — No working directory context for commands

**Severity: IMPORTANT**

Commands reference relative paths like `tests/unit/test_classification.py`, but the plan never specifies the project root. The implementer needs to know to either `cd /home/hermes/ticketpilot` or ensure their working directory is the project root. Add a note at the top: *"Run all commands from the project root (ticketpilot/)."*

---

### I3 — Unused imports left in classifier.py after change

**Severity: IMPORTANT** — will cause ruff lint failure.

After replacing lines 55-103, the following imports in classifier.py become **unused**:

```python
from ticketpilot.config import (
    ...
    CONFIDENCE_KEYWORD_1CHAR,       # ← unused
    CONFIDENCE_KEYWORD_LONG_TEXT,   # ← unused
    CONFIDENCE_KEYWORD_WITH_ORDER,  # ← unused
)
```

These are used only in the old confidence logic (lines 89-97) which is being removed. The project enforces ruff linting in the quality gate — unused imports will fail. The plan must include removing these three constants from the import statement.

(Note: the constants remain valid in `config/__init__.py` — only the import in classifier.py needs cleanup.)

---

### I4 — Existing tests that assert `confidence >= X` — all still pass but verification needed

**Severity: IMPORTANT**

While my analysis shows all existing tests pass under scoring (see Appendix A), the implementer should verify by running `python -m pytest tests/unit/test_classification.py -v` both before and after the change, as the plan instructs. The plan's analysis in Task 2 is mostly correct, but it should note that tests asserting specific confidence **values** (not just >= thresholds) could break — though none currently do.

---

## Minor Issues

### M1 — `matched_intent` variable shadowing

The proposed new code shadows the variable name `matched_intent` which previously was initialized at the top of Phase 2. Under the old structure, it was initialized before the loop. Under the new structure, it's set inside `if not scores:` / `else:` branches. The return statement at the end (if kept) uses whatever was last assigned. This works but is fragile — the plan should be explicit: either keep the old return statement or include a new one within the replacement block. See C1.

### M2 — `found_keyword_in_other` logic silently removed

The old code had a subtle feature: if the OTHER rule's `strong_indicator` matched the text, confidence was set to MEDIUM (0.6) instead of WEAK (0.5) even when no other keyword matched. The plan removes this. This is likely fine (scoring for OTHER is always 0 anyway), but it should be explicitly noted as a behavioral change.

### M3 — Confidence values drop for texts with order numbers

Under old code, "我申请退款，订单号123456" got `CONFIDENCE_KEYWORD_WITH_ORDER = 0.88`. Under new code it gets `CONFIDENCE_HIGH = 0.78`. This is a **0.10 drop** in confidence for the same text. No existing test asserts a value this high, so it won't break tests, but the plan doesn't mention this behavioral change.

---

## Acceptance Criteria Verification

### Task 1: Score-based classification logic

| Acceptance Criterion | Verifiable? | Notes |
|---------------------|-------------|-------|
| Strong indicators still fast-path | ✓ | Phase 1 unchanged |
| Multi-intent text scores multiple intents correctly | ✗ | No test validates the score dict itself (only the final intent) |
| Exclusion penalties reduce but don't block scores | ✗ | `test_refund_with_exclusion_penalty` is `pass` — no test validates this |
| No-keyword text returns OTHER | ✓ | Existing + proposed tests cover this |
| Existing classification tests still pass | ✓ | Verifiable by running tests before/after |

### Task 2: Update existing tests

| Acceptance Criterion | Verifiable? | Notes |
|---------------------|-------------|-------|
| All existing classification tests pass after scoring change | ✓ | Run `pytest tests/unit/test_classification.py -v` |
| No test modifications change the *intent* | ✓ | Check git diff for test file |

### Task 3: Run full test suite

| Acceptance Criterion | Verifiable? | Notes |
|---------------------|-------------|-------|
| All tests pass (or same pre-existing failures) | ✓ | Run `python -m pytest tests/ -q --tb=short` |

### Task 4: Verify optimizer still works

| Acceptance Criterion | Verifiable? | Notes |
|---------------------|-------------|-------|
| Optimizer still runs | ✓ | Command provided |
| Same number of issues found | ✓ | |
| Baseline composite is same or better | ✓ | |

---

## Summary of Required Changes

1. **Fix line range**: Change "lines 55-78" to "lines 55-103" (or "entire Phase 2 block through the return statement").
2. **Fix `_score_intents` signature**: Remove `excluded: set[IntentClass]` parameter; make it just `(self, text: str)`.
3. **Add return statement in new code**: The replacement code must end with `return ClassificationResult(...)`.
4. **Add a genuine TDD test**: A test that fails under first-match-wins and passes under scoring (e.g., a multi-intent text where keyword density overrides priority).
5. **Complete or remove the placeholder test**: `test_refund_with_exclusion_penalty` must have a real body.
6. **Clean up unused imports**: Remove `CONFIDENCE_KEYWORD_1CHAR`, `CONFIDENCE_KEYWORD_LONG_TEXT`, `CONFIDENCE_KEYWORD_WITH_ORDER` from the import statement in classifier.py.
7. **Add working directory note**: Add "Run all commands from ticketpilot/ project root" to the plan.

---

## Appendix A: Existing Test Compatibility Analysis

| Existing Test | Old Result | New Scoring Result | Compatible? |
|---|---|---|---|
| `test_classify_refund` | REFUND, conf≈0.88 | REFUND, conf=0.78 (≥0.5) | ✓ |
| `test_classify_return_exchange` | RETURN_EXCHANGE, conf≈0.78 | RETURN_EXCHANGE, conf=0.78 | ✓ |
| `test_classify_account_issue` | ACCOUNT_ISSUE | ACCOUNT_ISSUE | ✓ |
| `test_classify_technical_issue` | TECHNICAL_ISSUE | TECHNICAL_ISSUE | ✓ |
| `test_classify_product_consulting` | PRODUCT_CONSULTING | PRODUCT_CONSULTING | ✓ |
| `test_classify_logistics` | LOGISTICS | LOGISTICS | ✓ |
| `test_classify_complaint` | COMPLAINT | COMPLAINT | ✓ |
| `test_classify_other` | OTHER, conf=0.5 | OTHER, conf=0.5 | ✓ |
| `test_classify_empty_text` | OTHER, conf=0.5 | OTHER, conf=0.5 (early return) | ✓ |
| `test_confidence_high_for_strong_match` | REFUND, conf=0.78 | REFUND, conf=0.78 (≥0.78) | ✓ |
| `test_confidence_low_for_weak_match` | COMPLAINT, conf=0.78 | COMPLAINT, conf=0.78 (≥0.7) | ✓ |
| `test_classified_at_is_set` | timestamp set | timestamp set | ✓ |
| `TestLegalClassification` (7 cases) | All pass | All pass (analyzed per case) | ✓ |
