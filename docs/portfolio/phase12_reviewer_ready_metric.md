# Phase 12 Reviewer-Ready Metric Proposal

**Scope**: Local demo / portfolio prototype
**Generated**: 2026-05-07
**Status**: Implemented in Phase 13 — extended comparison runner produces reviewer-ready data

---

## Definition

**Reviewer-ready rate** is the proportion of draft cases where:
1. Citation validation passed (`citation_validation.is_valid = true`)
2. Claim guard passed (`guard_result.guard_passed = true`)
3. `unsupported_claims_count = 0`
4. Draft is structurally safe enough for human review

Note: High-risk cases (e.g., `severity = HIGH`) may still be reviewer-ready, but `must_human_review` remains `true`.

---

## Why Not Confidence Alone?

A draft with `confidence = 0.95` could still:
- Cite non-existent evidence IDs
- Make unsupported claims about policy or compensation
- Contain forbidden promises ("一定退款", "保证赔偿")
- Fail to acknowledge relevant risk flags

A draft with `confidence = 0.5` could still be:
- Fully citation-grounded
- Free of forbidden promises
- Safe for human review

**Therefore, reviewer-ready rate is a better signal than confidence for determining whether a draft should proceed to human review.**

---

## Current Data Gap (Phase 12 run)

Phase 12 provider comparison rows (`phase12_llm_provider_comparison_rows.json`) contain:
- `fake_has_citations` / `real_has_citations` (boolean)
- `fake_human_review` / `real_human_review` (boolean)
- `fake_confidence` / `real_confidence` (float)

Phase 12 does **not** contain:
- Citation validation result (valid/invalid IDs, duplicates, missing citations)
- Claim guard result (guard_passed, has_forbidden_promise, has_uncited_claims)
- Unsupported claims count

**Resolution in Phase 13**: Extended runner now produces all above fields via `DraftEvaluationRow` serialization.

---

## How to Compute It

### Required data fields per case:

```python
{
    "case_id": "p12_001",
    "citation_validation_valid": True,       # from DraftCitationValidationResult
    "guard_passed": True,                    # from GuardResult
    "has_forbidden_promise": False,          # from GuardResult
    "has_uncited_claims": False,            # from GuardResult
    "unsupported_claims_count": 0,           # from GuardResult
    "must_human_review": False,              # from DraftReply
    "severity": "LOW",                      # from RiskAssessment
    # reviewer-ready if:
    #   citation_validation_valid == True
    #   AND guard_passed == True
    #   AND unsupported_claims_count == 0
}
```

### Formula:

```
reviewer_ready_rate = (
    cases where citation_validation_valid == True
    AND guard_passed == True
    AND unsupported_claims_count == 0
) / total_cases
```

---

## Hypothetical Calculation (from Phase 12 rows)

**Current data**: All 25 Phase 12 cases show `has_citations: true` for both providers.
**Assumption**: If citations are present, citation validation would likely pass (unless IDs are invalid).
**Assumption**: Claim guard results are unknown.

| Provider | Cases | has_citations | Reviewer-ready (known) | Reviewer-ready (full, requires guard data) |
|----------|-------|---------------|----------------------|---------------------------------------------|
| FakeLLMProvider | 25 | 25/25 | >= 25/25 (lower bound) | requires guard data |
| OpenAICompatibleProvider | 25 | 25/25 | >= 25/25 (lower bound) | requires guard data |

**Lower bound**: At minimum, 25/25 (100%) cases have citations — a necessary but not sufficient condition for reviewer-ready.

---

## Phase 13 Implementation Results (Fixed)

The Phase 13 extended runner produced `DraftEvaluationRow` objects for all 25 FakeLLMProvider cases.
From the extended output (`phase12_llm_provider_comparison_summary.json`):

| Metric | Value |
|--------|-------|
| Citation validation pass rate | 100% (25/25) |
| Claim guard pass rate | 68% (17/25) — fixed from 0% after UUID citation fix |
| Unsupported claim rate | 0% (0/25) |
| Reviewer-ready rate (FakeLLMProvider) | 17/25 (68%) |

**Root cause of initial 0% guard pass rate**: FakeLLMProvider template used `[N]` numeric markers
instead of `[UUID]` chunk_id markers. Claim guard's `_extract_chunk_ids()` only recognizes `[UUID]`
format, so no chunk IDs were found in the text → `has_uncited_claims = True` → guard failed.
Fix: updated template to use `[{ev.chunk_id}]` format. After fix: 17/25 pass guard.

**Remaining failures**: All 8 are HIGH-severity cases where FakeLLMProvider template does not
include escalation acknowledgment language (e.g., "转人工", "人工处理"). This is correct behavior —
the claim guard's `risk_flags_respected` check correctly identifies that HIGH-risk drafts require
acknowledgment. A real LLM provider would likely produce different guard pass rates.

**Key interpretation**:
- FakeLLMProvider validates pipeline mechanics, not guard-compliant draft quality
- guard_pass_rate=68% for fake provider reflects template limitations, not a guard bug
- Real provider output should be evaluated separately when env is configured
- No auto-send; human review remains required for all HIGH-severity cases

**Next step**: Run extended runner with real provider (`.env.local` configured) to get per-provider reviewer-ready rates.

---

## Next Steps (Post-Phase 13)

1. ~~**Extend Phase 12 comparison runner**~~ (DONE in Phase 13) Extended output now includes citation validation and claim guard results
2. ~~**Re-run comparison**~~ (DONE in Phase 13) Extended rows generated with `DraftEvaluationRow` schema
3. ~~**Compute reviewer-ready rate**~~ (DONE in Phase 13) Available from extended summary output
4. **Compare between providers**: Run extended runner with real provider to get per-provider reviewer-ready rates
5. **Set a minimum threshold**: Define acceptable reviewer-ready rate for system to proceed

---

## Interpretation

| Reviewer-ready rate | Interpretation |
|--------------------|----------------|
| 100% | All drafts are structurally safe — human reviewer can focus on quality, not safety |
| 80–99% | Most drafts are safe; minority need safety edits before review |
| 50–79% | Significant safety issues; system needs improvement before deployment |
| < 50% | Claim guard and citation validation are not yet effective; do not proceed |

**Boundary**: This metric measures structural safety (citations valid, no forbidden promises, no unsupported claims), not semantic quality. A reviewer-ready draft may still require substantive edits by the human reviewer.
