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

## Phase 13.10: Guard-Aware Prompting Experiment (2026-05-07)

**Goal**: Test whether guard-aware structured prompts improve real provider citation and guard metrics.

**Root cause from Phase 13.9**: Real provider used bare-bones prompt without explicit `[chunk_id]` citation requirements. LLM generated free-form Chinese text without citation markers.

**Intervention**: Replaced hardcoded prompt in `OpenAICompatibleProvider.generate_draft()` with structured prompt that:
- Uses `format_evidence_block()` with `[chunk_id]` markers in evidence section
- Explicitly requires `[{chunk_id}]` inline citations (not `[1]`, `[2]`)
- Instructs safe fallback when evidence insufficient
- Adds forbidden promise and no-auto-send rules

**Results**:

| Metric | Phase 13.9 Baseline | Phase 13.10 Guard-Aware | Change |
|--------|---------------------|-------------------------|--------|
| Real citation validation pass | 12% (3/25) | 76% (19/25) | +64 pp |
| Real claim guard pass | 4% (1/25) | 84% (21/25) | +80 pp |
| Real unsupported claim rate | 88% (22/25) | 24% (6/25) | -64 pp |
| Real human review triggers | 100% (25/25) | 48% (12/25) | -52 pp |
| Real reviewer-ready rate | 4% (1/25) | 64% (16/25) | +60 pp |
| Real safe fallback rate | 4% (1/25) | 84% (21/25) | +80 pp |
| Real avg confidence | 0.700 | 0.644 | -0.056 |

FakeLLMProvider (quality gate default) unchanged: guard=68%, citation_valid=100%.

**Remaining 4 guard failures** (real provider):
- p12_011, p12_015: Citations present but privacy/legal risk flag not acknowledged with escalation language
- p12_018: 2 unsupported claims + 1 forbidden promise (compensation amount)
- p12_021: Substantive content without `[chunk_id]` citation markers

All failures are correct guard behavior — not false positives.

**Key insight**: The prompt explicitly instructs safe fallback when evidence is insufficient. 84% safe fallback rate is the expected consequence — the LLM is conservative about citing evidence. This is acceptable because safe fallback cases correctly trigger human review.

**Boundary**: Offline fixture-based evaluation on 25 synthetic cases with mock evidence — NOT a benchmark. Human review remains mandatory. No auto-send.

**Source**: `reports/eval/phase13_guard_aware_prompting_report.md`

---

## Phase 13.9 Baseline (bare prompt — superseded by Phase 13.10)

The Phase 13.9 extended runner produced `DraftEvaluationRow` objects for all 25 cases per provider using the bare-bones prompt.

### FakeLLMProvider (unchanged in Phase 13.10)

| Metric | Value |
|--------|-------|
| Citation validation pass rate | 100% (25/25) |
| Claim guard pass rate | 68% (17/25) |
| Unsupported claim rate | 0% (0/25) |
| Human review triggers | 32% (8/25) |
| Reviewer-ready rate | 68% (17/25) |

Guard failures: 8 HIGH-severity cases lacking escalation acknowledgment language in template.

### Real Provider (deepseek-v4-pro, bare prompt — superseded)

| Metric | Value |
|--------|-------|
| Citation validation pass rate | 12% (3/25) |
| Claim guard pass rate | 4% (1/25) |
| Unsupported claim rate | 88% (22/25) |
| Human review triggers | 100% (25/25) |
| Reviewer-ready rate | 4% (1/25) |

**Root cause**: Real LLM generated short free-form Chinese text (80–174 chars) without inline `[chunk_id]` citation markers. Claim guard flagged `has_uncited_claims=True` for substantive content without markers.

**Resolution**: Phase 13.10 replaced bare prompt with guard-aware structured prompt. Real provider guard pass rate improved to 84%. See Phase 13.10 section above.

---

## Next Steps (Post-Phase 13)

1. ~~**Extend Phase 12 comparison runner**~~ (DONE in Phase 13)
2. ~~**Re-run comparison**~~ (DONE in Phase 13)
3. ~~**Compute reviewer-ready rate**~~ (DONE in Phase 13)
4. ~~**Compare between providers**~~ (DONE in Phase 13.9) Fake=68%, Real=4%
5. ~~**Guard-aware real provider prompt**~~ (DONE in Phase 13.10) Real guard pass: 4% → 84%
6. **Evaluate on real customer tickets**: 25 synthetic fixtures may not reflect real-world query distribution
7. **Tune safe fallback threshold**: 84% safe fallback may be too conservative
8. **Improve risk escalation compliance**: 3 guard failures are LLM not acknowledging risk flags
9. **Set a minimum threshold**: Define acceptable reviewer-ready rate for system to proceed

---

## Interpretation

| Reviewer-ready rate | Interpretation |
|--------------------|----------------|
| 100% | All drafts are structurally safe — human reviewer can focus on quality, not safety |
| 80–99% | Most drafts are safe; minority need safety edits before review |
| 50–79% | Significant safety issues; system needs improvement before deployment |
| < 50% | Claim guard and citation validation are not yet effective; do not proceed |

**Boundary**: This metric measures structural safety (citations valid, no forbidden promises, no unsupported claims), not semantic quality. A reviewer-ready draft may still require substantive edits by the human reviewer.
