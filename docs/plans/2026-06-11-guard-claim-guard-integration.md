# 14.4 Claim Guard Integration Implementation Plan

**Goal:** Wire `check_safe_escalation_language()` and `check_manual_review_acknowledgement()` into `check_claim_guard()`'s failure_reasons taxonomy.

**Scope:**
- Add `SAFE_ESCALATION_STATEMENT` to failure_reasons when guard fails AND safe escalation detected
- Add `MANUAL_REVIEW_ACKNOWLEDGEMENT` to failure_reasons when guard fails AND manual review acknowledged
- These are informational annotations — they do NOT change guard_passed
- `EVIDENCE_INSUFFICIENT_FALLBACK` remains deferred (guard_passed=True invariant prevents adding it to failure-only list)

**Files:**
- Modify: `src/ticketpilot/drafting/claim_guard.py` (lines 307-317, add after risk check in failure_reasons block)
- Test: `tests/unit/test_claim_guard.py` (add tests to TestFailureReasonsTaxonomy + TestCheckClaimGuard)

---

### Task: Integrate taxonomy + tests

**Step 1: Write failing tests**

Add to `TestFailureReasonsTaxonomy` in `test_claim_guard.py`:

```python
def test_safe_escalation_statement_included_when_present(self) -> None:
    """SAFE_ESCALATION_STATEMENT added when safe escalation language detected and guard fails."""
    # Draft with forbidden promise AND safe escalation language
    text = "尊敬的用户，退款500元。此问题需要人工审核。"
    draft = _draft(text)
    result = check_claim_guard(draft, [])
    assert result.guard_passed is False
    assert GuardFailureType.FORBIDDEN_PROMISE in result.failure_reasons
    assert GuardFailureType.SAFE_ESCALATION_STATEMENT in result.failure_reasons

def test_manual_review_acknowledgement_included_when_present(self) -> None:
    """MANUAL_REVIEW_ACKNOWLEDGEMENT added when manual review acknowledged and guard fails."""
    text = "尊敬的用户，退款500元。需人工审核。"
    draft = _draft(text)
    result = check_claim_guard(draft, [])
    assert result.guard_passed is False
    assert GuardFailureType.FORBIDDEN_PROMISE in result.failure_reasons
    assert GuardFailureType.MANUAL_REVIEW_ACKNOWLEDGEMENT in result.failure_reasons

def test_safe_escalation_not_included_when_not_present(self) -> None:
    """SAFE_ESCALATION_STATEMENT absent when guard fails without escalation language."""
    text = "尊敬的用户，退款500元。"
    draft = _draft(text)
    result = check_claim_guard(draft, [])
    assert result.guard_passed is False
    assert GuardFailureType.SAFE_ESCALATION_STATEMENT not in result.failure_reasons

def test_manual_review_not_included_when_not_present(self) -> None:
    """MANUAL_REVIEW_ACKNOWLEDGEMENT absent when guard fails without review acknowledgement."""
    text = "尊敬的用户，退款500元。"
    draft = _draft(text)
    result = check_claim_guard(draft, [])
    assert result.guard_passed is False
    assert GuardFailureType.MANUAL_REVIEW_ACKNOWLEDGEMENT not in result.failure_reasons
```

**Step 2: Run tests → FAIL**

Run: `cd /home/hermes/ticketpilot && PYTHONPATH=src python3 -m pytest tests/unit/test_claim_guard.py -k "safe_escalation or manual_review" -v --tb=short`
Expected: AssertionError — SAFE_ESCALATION_STATEMENT/MANUAL_REVIEW_ACKNOWLEDGEMENT not in failure_reasons

**Step 3: Implement wiring**

In `check_claim_guard()`, after the `risk_respected` check in the failure_reasons block (line 315), add:

```python
        if not risk_respected:
            failure_reasons.append(GuardFailureType.MISSING_RISK_ESCALATION)
        # Safe escalation language — informational annotation
        if check_safe_escalation_language(draft_text):
            failure_reasons.append(GuardFailureType.SAFE_ESCALATION_STATEMENT)
        # Manual review acknowledgement — informational annotation
        if check_manual_review_acknowledgement(draft_text):
            failure_reasons.append(GuardFailureType.MANUAL_REVIEW_ACKNOWLEDGEMENT)
        if not failure_reasons:
```

**Step 4: Run tests → PASS**

Run: `cd /home/hermes/ticketpilot && PYTHONPATH=src python3 -m pytest tests/unit/test_claim_guard.py -v --tb=short`
Expected: 78 passed (all existing + 4 new)

**Step 5: Commit**

```bash
cd /home/hermes/ticketpilot && git add src/ticketpilot/drafting/claim_guard.py tests/unit/test_claim_guard.py && git commit -m "feat(guard): wire safe escalation + manual review into check_claim_guard() failure_reasons"
```

**Acceptance Criteria:**
1. `SAFE_ESCALATION_STATEMENT` appears in failure_reasons when guard fails AND escalation language present
2. `MANUAL_REVIEW_ACKNOWLEDGEMENT` appears in failure_reasons when guard fails AND review keyword present
3. Both are absent when guard passes
4. Both are absent when guard fails but the respective keywords are absent
5. `guard_passed` logic unchanged (no guard weakening)
6. All 78 tests pass
