# Phase 12 Reviewer-Ready Metric Proposal

**Scope**: Local demo / portfolio prototype
**Generated**: 2026-05-07
**Status**: Proposal — not yet implemented in evaluation runner

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

## Current Data Gap

Phase 12 provider comparison rows (`phase12_llm_provider_comparison_rows.json`) contain:
- `fake_has_citations` / `real_has_citations` (boolean)
- `fake_human_review` / `real_human_review` (boolean)
- `fake_confidence` / `real_confidence` (float)

Phase 12 does **not** currently contain:
- Citation validation result (valid/invalid IDs, duplicates, missing citations)
- Claim guard result (guard_passed, has_forbidden_promise, has_uncited_claims)
- Unsupported claims count

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

## Next Steps to Implement

1. **Extend Phase 12 comparison runner** to output per-case citation validation and claim guard results alongside existing fields
2. **Re-run comparison** with the extended output schema
3. **Compute reviewer-ready rate** from the new rows
4. **Compare between providers**: if fake and real have different reviewer-ready rates, investigate the cause
5. **Set a minimum threshold**: define what reviewer-ready rate is acceptable for the system to proceed

---

## Interpretation

| Reviewer-ready rate | Interpretation |
|--------------------|----------------|
| 100% | All drafts are structurally safe — human reviewer can focus on quality, not safety |
| 80–99% | Most drafts are safe; minority need safety edits before review |
| 50–79% | Significant safety issues; system needs improvement before deployment |
| < 50% | Claim guard and citation validation are not yet effective; do not proceed |

**Boundary**: This metric measures structural safety (citations valid, no forbidden promises, no unsupported claims), not semantic quality. A reviewer-ready draft may still require substantive edits by the human reviewer.
