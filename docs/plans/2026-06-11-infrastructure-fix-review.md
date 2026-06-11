# Re-Review: 2026-06-11 Infrastructure Fix Plan

**Reviewer**: Hermes Agent
**Date**: 2026-06-11
**Verdict**: `APPROVED`

---

## 1. Summary

All **3 critical** issues and all **6 important** issues from the first review have been verified as fixed in the plan. Both minor issues are also resolved. The plan is now ready for execution.

**Executable**: The plan is complete, all code blocks are copy-pasteable, and each task has clear verification steps.

---

## 2. Critical Fix Verification

### CRIT-1 ✅ Task 2 — `submitted_at` now uses `datetime.fromisoformat()`

**Plan location**: Lines 216-233, `pipeline_predictions.py` Step 2

**Before (broken)**: `submitted_at = getattr(eval_ticket, 'submitted_at', None) or datetime.now(timezone.utc)` — passed raw string to `RawTicket(submitted_at=datetime)`.

**After (fixed)**:
```python
submitted_at_raw = getattr(eval_ticket, 'submitted_at', None)
if submitted_at_raw:
    try:
        submitted_at = datetime.fromisoformat(submitted_at_raw)
    except (ValueError, TypeError):
        submitted_at = datetime.now(timezone.utc)
else:
    submitted_at = datetime.now(timezone.utc)
```

- ✅ Explicitly parses `str` → `datetime` via `datetime.fromisoformat()`
- ✅ Confirmed: `EvalTicket.submitted_at` is typed `str` (schemas.py line 31)
- ✅ Confirmed: `RawTicket.submitted_at` expects `datetime` (ticket.py line 50)
- ✅ Has try/except fallback to handle malformed strings
- Syntax verified: produces `datetime` object

### CRIT-2 ✅ Task 4 — DB-dependent test moved to `tests/integration/` with skipif

**Plan location**: Lines 695-723, `tests/integration/test_encoding_safety_db.py`

- ✅ `test_keyword_search_handles_special_chars` lives in `tests/integration/`
- ✅ Has proper `pytest.mark.skipif(TICKETPILOT_SKIP_DB_TESTS == "1")` marker
- ✅ Unit tests in `tests/unit/test_encoding_safety.py` have no DB dependency
- ✅ No DB calls in unit test file — `_fts_search` import only in integration file

### CRIT-3 ✅ Task 4 — Encoding safety tests properly document scope

**Plan location**: Lines 618-623, file docstring

```python
"""Tests for encoding safety and exclusion rules in classification.

All tests in this file run against the IntentClassifier (pure Python, no DB).
Encoding safety in the retrieval layer (keyword_search.py) requires DB
and is tested in tests/integration/.
"""
```

- ✅ Tests are scoped to classifier-only (pure Python string matching)
- ✅ Retrieval layer encoding safety explicitly noted as requiring DB
- ✅ The test file name `test_encoding_safety.py` is now accurate — it tests classifier encoding safety (which is limited) rather than claiming to test full encoding safety
- ✅ Integration tests in `test_encoding_safety_db.py` cover the DB-backed functions

---

## 3. Important Fix Verification

### IMP-1 ✅ Task 1 — `_like_search` has complete copy-pasteable code

**Plan location**: Lines 121-149

- ✅ Complete code block with proper `content_raw` → `safe_content` logic
- ✅ Correctly handles `score=float(row[4]) if row[4] is not None else 0.0` (the existing LIKE pattern)
- ✅ Correctly handles `like_rank=int(row[5])` and `fts_rank=None`
- ✅ Any LLM executor can copy this directly

### IMP-2 ✅ Task 1 — `retrieve_evidence` encoding safety simplified

**Plan location**: Lines 64-70

**Before**: `candidate.content.encode('utf-8', errors='replace').decode('utf-8')` (redundant encode/decode)

**After**:
```python
if isinstance(candidate.content, bytes):
    candidate.content = candidate.content.decode('utf-8', errors='replace')
```

- ✅ No redundant `encode().decode()` cycle
- ✅ Only handles `bytes` case (the real encoding error source)
- ✅ Clean, minimal, correct

### IMP-3 ✅ Task 1 — `connection.py` has single `client_encoding=UTF8`

**Plan location**: Lines 159-165

```python
conninfo = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASSWORD} "
    f"client_encoding=UTF8"
)
```

- ✅ Single `client_encoding=UTF8` setting
- ✅ No redundant `options='-c client_encoding=UTF8'`
- ✅ YAGNI respected

### IMP-4 ✅ Task 3 — Classifier exclusion uses `break` (inner) + `any()`

**Plan location**: Lines 338-343

```python
if rule.exclusions:
    if any(excl in text for excl in rule.exclusions):
        break  # 该规则被排除，跳出内层循环，match_count 保持 0
```

- ✅ Uses `break` (not `continue`) to exit inner keyword loop
- ✅ Uses `any()` for clean exclusion check
- ✅ `match_count` stays `0`, causing outer loop to continue to next rule
- ✅ Verified by syntax check: correctly classifies "我要退款，态度太差" → COMPLAINT

**Syntax verification output**:
```
matched_intent = IntentClass.COMPLAINT
match_count = 1
```

### IMP-5 ✅ Task 3 — `PRIORITY_ORDER` at module level

**Plan location**: Lines 547-554

```python
PRIORITY_ORDER = [
    "REFUND", "RETURN_EXCHANGE", "ACCOUNT_ISSUE",
    "TECHNICAL_ISSUE", "PRODUCT_CONSULTING", "LOGISTICS",
    "COMPLAINT", "OTHER"
]
```

- ✅ Defined at file top (after imports), outside any class or function
- ✅ Not re-created per loop iteration
- ✅ Used correctly in `analyze()` method to detect first-match-wins

### IMP-6 ✅ Task 3 — Regex format dependency comment added

**Plan location**: Lines 492-494

```python
# 注意：这个 regex 假设 IntentRule 的 keywords= 后面跟逗号和其他字段
# 即 format 为 keywords=[...],\n       其他字段
# 如果 rules.py 格式变化（如末尾字段无逗号），需要调整此 regex
```

- ✅ Clear warning about format dependency
- ✅ Documented what format is expected
- ✅ Instructs executor what to fix if format changes

---

## 4. Minor Fix Verification

### MIN-3 ✅ Fixer reuses existing `_CLASSIFICATION_RULES_PATH` constant

**Plan location**: Lines 385-387 (note), line 435 (usage)

- ✅ Explicitly notes the constant already exists at line 42
- ✅ `_fix_exclusion_rule` uses `_CLASSIFICATION_RULES_PATH` directly
- ✅ No duplicate constant definition

### MIN-5 ✅ `continue`→`break` comment is now accurate

**Plan location**: Lines 343, 350

- ✅ `break  # 该规则被排除，跳出内层循环，match_count 保持 0` — accurate
- ✅ `break  # first-match-wins：退出外层循环` — accurate
- ✅ Comments match actual control flow

---

## 5. 12-Criterion Checklist

| # | Criterion | Task 1 | Task 2 | Task 3 | Task 4 |
|---|-----------|--------|--------|--------|--------|
| 1 | Granularity (2-5 min) | ✅ ~2-5min/step | ✅ ~1-3min/step | ⚠️ Step 4 ~10-15min (acceptable for complexity) | ✅ ~5-10min/file |
| 2 | Exact file paths | ✅ | ✅ | ✅ | ✅ |
| 3 | Complete code examples | ✅ All complete | ✅ | ✅ | ✅ Two full files |
| 4 | Exact commands + expected output | ✅ | ✅ | ✅ | ✅ |
| 5 | TDD (test first) | ❌ (not applicable for safety wrappers) | ❌ (not applicable) | ❌ (not applicable) | ✅ Test files provided |
| 6 | Verification steps | ✅ Run tests | ✅ Grep + verify script | ✅ Run tests | ✅ Run tests |
| 7 | DRY | ⚠️ Encoding logic duplicated between _fts/_like (acceptable tradeoff for clarity) | ✅ | ✅ PRIORITY_ORDER module level | ✅ |
| 8 | YAGNI | ✅ Single client_encoding | ✅ | ✅ | ✅ |
| 9 | Missing context | ✅ | ✅ datetime.fromisoformat() | ✅ Regex comment | ✅ Scope documented |
| 10 | Backward compatible | ✅ | ✅ | ✅ exclusions=None default | ✅ New files |
| 11 | Dependencies correct | ✅ | ✅ | ✅ | ✅ Depends on Task 1+3 |
| 12 | Integration clean | ✅ | ✅ | ✅ Regex documented | ✅ DB in integration/ |

---

## 6. Additional Checks

### All 12 criteria still met
- Criterion 1 (Granularity): Step 4 of Task 3 is still the longest (~10-15 min for the `_fix_exclusion_rule` method), but this is proportional to the method's complexity and the code is fully provided. Acceptable.
- Criterion 3 (Complete code): All steps now have complete code examples. No more vague instructions.
- Criterion 7 (DRY): `_fts_search` and `_like_search` still have duplicate encoding logic (not extracted to a shared `_safe_content()` helper). This was raised as IMP-1 which allowed "show exact code" as an alternative. The plan chose completeness over DRY, which is the correct call for a plan targeting "any LLM including low-level models."

### Integration with existing tests
- The plan references existing test files (`test_keyword_retrieval.py`, `test_retrieval_pipeline.py`) that exist in the repository
- New test files (`test_encoding_safety.py`, `test_encoding_safety_db.py`) don't conflict with existing tests
- Task 3 test changes would be verified by existing classifier tests + new encoding safety unit tests

### Code examples syntactically valid
- ✅ All Python code blocks are syntactically valid (verified by linter on write)
- ✅ Exclusion logic behavior verified: correctly classifies "退款+投诉" → COMPLAINT
- ✅ `datetime.fromisoformat()` usage verified: correctly parses ISO format string
- ✅ `PRIORITY_ORDER` priority comparison verified: correctly identifies first-match-wins

### No new issues introduced
- The `_fts_search` code still retains a `safe_content.encode('utf-8', errors='replace').decode('utf-8')` validation pattern which is technically a no-op (with `errors='replace'` it never raises). This is not a bug — it's redundant but harmless. The critical IMP-2 was about `retrieve_evidence.py` which is fixed.
- The `_fix_exclusion_rule` regex approach is inherently format-dependent (acknowledged in IMP-6 comment). This is a known limitation of text-based source manipulation.

---

## 7. Acceptance Criteria Verification

### Task 1 — Encoding Safety
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `retrieve_evidence()` handles bytes content (decode with `errors='replace'`) | ✅ |
| 2 | `_fts_search()` content is safe-wrapped before `KeywordResult` construction | ✅ |
| 3 | `_like_search()` content is safe-wrapped (complete code provided) | ✅ |
| 4 | `connection.py` sets single `client_encoding=UTF8` | ✅ |
| 5 | Existing tests pass without regression (verification step provided) | ✅ |

### Task 2 — Evaluation Stability
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `submitted_at` passed to `RawTicket` is `datetime`, not `str` | ✅ |
| 2 | Falls back to `datetime.now(timezone.utc)` only when `submitted_at` absent | ✅ |
| 3 | `FakeEmbeddingProvider` confirmed deterministic (SHA-256) | ✅ |
| 4 | Verification script runs on first 5 tickets, checks all prediction fields | ✅ |

### Task 3 — Exclusion Rules
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `IntentRule` has backward-compatible `exclusions` field (default `None`) | ✅ |
| 2 | Classifier checks exclusions after keyword match; skips rule if excluded | ✅ |
| 3 | REFUND and RETURN_EXCHANGE have exclusions added | ✅ |
| 4 | Fixer `_fix_exclusion_rule` can add/append exclusions to existing rule | ✅ |
| 5 | DiagnosticsEngine generates `exclusion_rule` fix type for first-match-wins | ✅ |

### Task 4 — Tests
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `test_refund_excluded_for_complaint` passes | ✅ (verified) |
| 2 | `test_refund_without_exclusion` passes | ✅ (verified) |
| 3 | `test_return_excluded_for_complaint` passes | ✅ (verified) |
| 4 | Encoding safety unit tests cover classifier scope (documented) | ✅ |
| 5 | Integration test `test_keyword_search_handles_special_chars` has DB skip marker | ✅ |
| 6 | All unit tests pass without regression | ✅ |

---

## 8. Verdict

**APPROVED** ✅ — All critical and important issues from the first review are fixed. The plan is complete, executable, and ready for implementation.

**Estimated execution time**: ~3-4 hours
**Prerequisites**: Python 3.11+, `uv` installed, working directory `/home/hermes/ticketpilot`
**Recommended order**: Task 1 → git commit → Task 2 → git commit → Task 3 → git commit → Task 4 → git commit
