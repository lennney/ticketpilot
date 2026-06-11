# 14.3 Safe Language Classifier Implementation Plan

**Goal:** Implement `check_safe_escalation_language()` and `check_manual_review_acknowledgement()` functions in `claim_guard.py`.

**Architecture:** Two standalone deterministic functions added to `claim_guard.py`. They're pure keyword-detection — no new dependencies, no schema changes, no wiring into `check_claim_guard()` yet (deferred to Task 14.4).

**Tech Stack:** Python 3.11, re (stdlib), existing test helpers from `test_claim_guard.py`.

---

### Task 1: `check_safe_escalation_language()`

**Objective:** Detect safe escalation keywords in draft text.

**Files:**
- Modify: `src/ticketpilot/drafting/claim_guard.py` (add function after `_check_risk_acknowledgment`, before `check_claim_guard`)
- Test: `tests/unit/test_claim_guard.py` (append new test class)

**Step 1: Write failing tests**

Append to `tests/unit/test_claim_guard.py`:

```python
class TestSafeEscalationLanguage:
    """Detect safe escalation language in draft text."""

    def test_detects_人工处理(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("此案件需要人工处理。") is True

    def test_detects_转人工客服(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("建议转人工客服处理。") is True

    def test_detects_需要人工审核(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("此问题需要人工审核。") is True

    def test_detects_人工审查(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("已提交人工审查。") is True

    def test_detects_升级至人工(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("此案件已升级至人工处理。") is True

    def test_detects_已升级人工(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("此案件已升级人工处理。") is True

    def test_no_keywords_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("尊敬的客户，您好。") is False

    def test_empty_text_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_safe_escalation_language
        assert check_safe_escalation_language("") is False
```

**Step 2: Run tests → FAIL**

Run: `cd /home/hermes/ticketpilot && PYTHONPATH=src python3 -m pytest tests/unit/test_claim_guard.py::TestSafeEscalationLanguage -v --tb=short`
Expected: ImportError — function not defined

**Step 3: Implement function + module-level constant**

In `claim_guard.py`, add module-level constant before `check_safe_escalation_language()`, and the function after `_check_risk_acknowledgment()` (line 191):

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


def check_safe_escalation_language(draft_text: str) -> bool:
    """Detect safe escalation language in draft text.

    Checks for keywords that indicate the draft is requesting or
    acknowledging escalation to human agents.

    Args:
        draft_text: The draft reply text to check.

    Returns:
        True if any safe escalation keyword is found.
    """
    text = draft_text.lower()
    return any(kw in text for kw in _SAFE_ESCALATION_KEYWORDS)
```

**Step 4: Run tests → PASS**

Run: `cd /home/hermes/ticketpilot && PYTHONPATH=src python3 -m pytest tests/unit/test_claim_guard.py::TestSafeEscalationLanguage -v --tb=short`
Expected: 7 passed

**Step 5: Commit**

```bash
cd /home/hermes/ticketpilot && git add src/ticketpilot/drafting/claim_guard.py tests/unit/test_claim_guard.py && git commit -m "feat(guard): add check_safe_escalation_language() with tests"
```

**Acceptance Criteria:**
1. `check_safe_escalation_language()` detects all 5 keywords: 人工处理, 转人工客服, 需要人工审核, 人工审查, 升级处理
2. Returns False for text without any escalation keywords
3. Returns False for empty text
4. Pure string matching (no network, no LLM)
5. All 7 tests pass

---

### Task 2: `check_manual_review_acknowledgement()`

**Objective:** Detect manual review acknowledgment keywords in draft text.

**Files:**
- Same files as Task 1

**Step 1: Write failing tests**

Append to `test_claim_guard.py`:

```python
class TestManualReviewAcknowledgement:
    """Detect manual review acknowledgement in draft text."""

    def test_detects_人工审核(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement
        assert check_manual_review_acknowledgement("需进行人工审核。") is True

    def test_detects_需人工review(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement
        assert check_manual_review_acknowledgement("此问题需人工 review。") is True

    def test_detects_人工确认(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement
        assert check_manual_review_acknowledgement("已人工确认并处理。") is True

    def test_detects_需人工介入(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement
        assert check_manual_review_acknowledgement("此案件需人工介入。") is True

    def test_no_keywords_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement
        assert check_manual_review_acknowledgement("尊敬的客户，您好。") is False

    def test_empty_text_returns_false(self) -> None:
        from ticketpilot.drafting.claim_guard import check_manual_review_acknowledgement
        assert check_manual_review_acknowledgement("") is False
```

**Step 2: Run tests → FAIL**

Run similar command — expected ImportError.

**Step 3: Implement function + module-level constant**

In `claim_guard.py`, after `check_safe_escalation_language()`, add:

```python
# Manual review keywords — draft acknowledges need for human oversight
_MANUAL_REVIEW_KEYWORDS: list[str] = [
    "人工审核",
    "需人工 review",
    "人工确认",
    "需人工介入",
]


def check_manual_review_acknowledgement(draft_text: str) -> bool:
    """Detect manual review acknowledgement in draft text.

    Checks for keywords that acknowledge the need for manual human review.
    Distinct from safe escalation language — manual review acknowledgment
    signals that the draft itself requires human oversight.

    Args:
        draft_text: The draft reply text to check.

    Returns:
        True if any manual review keyword is found.
    """
    text = draft_text.lower()
    return any(kw in text for kw in _MANUAL_REVIEW_KEYWORDS)
```

**Step 4: Run tests → PASS**

**Step 5: Commit**

```bash
cd /home/hermes/ticketpilot && git add src/ticketpilot/drafting/claim_guard.py tests/unit/test_claim_guard.py && git commit -m "feat(guard): add check_manual_review_acknowledgement() with tests"
```

**Acceptance Criteria:**
1. `check_manual_review_acknowledgement()` detects all 4 keywords: 人工审核, 需人工 review, 人工确认, 需人工介入
2. Returns False for text without any keywords
3. Returns False for empty text
4. Functions can both trigger on the same text when it contains overlapping keywords (e.g., "需要人工审核" triggers both). This is by design — each function serves a distinct guard purpose.
5. All 6 tests pass

---

## Rollback

```bash
git reset --hard HEAD~2
```
