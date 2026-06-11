# Plan: Fix 5 Failing Optimizer Diagnostics Tests

## Context

5 tests in `test_optimizer_diagnostics.py` fail because the corresponding diagnosis
functions were intentionally disabled after the tests were written. The optimizer
still works correctly — it just doesn't generate certain diagnosis types.

## Strategy

**Re-enable 1 diagnosis type** (`confidence_misroute`) where the fixer already has
a working handler (`_fix_confidence_threshold`). **Update 4 other tests** to reflect
the current design tradeoffs (diagnosis disabled for practical reasons).

### Task A: Re-enable `_analyze_confidence_misroute` 
*File: `src/ticketpilot/optimizer/diagnostics.py` (~lines 441-460)*

Replace the "return empty" stub with real logic:
- Count cases where `must_human_review_accuracy` or `no_auto_send_compliance` is False
- Calculate fix_gain using `no_auto_send + fallback` weight (0.20)
- Generate 1 diagnosis with `suggested_fix_type = "confidence_threshold"`
- Suggest `threshold_name = "CONFIDENCE_MEDIUM"` and `new_value = 0.5` (reasonable default)

### Task B: Update `test_risk_false_positive_diagnosis`
*File: `tests/unit/test_optimizer_diagnostics.py` (~lines 287-309)*

Replace: `assert len(fp_diags) == 1` → `assert len(fp_diags) == 0`
Add comment: `# risk_false_positive disabled — removing keywords is risky`

### Task C: Update `test_evidence_gap_diagnosis`
*File: `tests/unit/test_optimizer_diagnostics.py` (~lines 311-332)*

Replace: `assert len(ev_diags) == 1` → `assert len(ev_diags) == 0`
Add comment: `# evidence_gap disabled — no fix handler implemented`

### Task D: Update `test_severity_mismatch_diagnosis`
*File: `tests/unit/test_optimizer_diagnostics.py` (~lines 334-351)*

Replace: `assert len(sev_diags) == 1` → `assert len(sev_diags) == 0`
Add comment: `# severity_wrong disabled — derived from risk flags; fixing risk side-effects it`

### Task E: Update `test_multiple_mismatch_types`
*File: `tests/unit/test_optimizer_diagnostics.py` (~lines 376-423)*

Remove `assert TYPE_SEVERITY_WRONG in types_found` (severity is disabled)
Add comment explaining why

### Task F: Verify

```bash
cd ~/ticketpilot
.venv/bin/python -m pytest tests/unit/test_optimizer_*.py -q --tb=short
```
Expected: 121/121 PASS

## Acceptance Criteria

1. All 121 optimizer tests pass
2. `_analyze_confidence_misroute` produces real diagnoses (not empty stub)
3. Other disabled diagnosis types are explicitly documented in tests
4. No changes to fixer/engine logic — only diagnostics and tests
