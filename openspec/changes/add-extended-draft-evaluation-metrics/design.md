# Design: Extended Draft Evaluation Metrics

## Data Source

All metrics are computed from `DraftGenerationResult` produced by `generate_draft()` in `src/ticketpilot/drafting/generator.py`.

The `generate_draft()` pipeline already produces:
- `draft.cited_evidence_ids`: list of cited chunk UUID strings
- `draft.unsupported_claims`: list of unsupported claim strings
- `draft.must_human_review`: bool
- `draft.escalation_reason`: str | None
- `draft.fallback_reason`: str | None
- `draft.confidence`: float
- `citation_validation` (DraftCitationValidationResult):
  - `is_valid`: bool
  - `valid_cited_evidence_ids`: list[str]
  - `invalid_cited_evidence_ids`: list[str]
  - `available_evidence_ids`: list[str]
  - `missing_citation_required`: bool
  - `must_human_review`: bool
- `guard_result` (GuardResult):
  - `guard_passed`: bool
  - `has_forbidden_promise`: bool
  - `has_uncited_claims`: bool
  - `citation_coverage`: float (0.0–1.0)
  - `evidence_sufficiency`: str
  - `risk_flags_respected`: bool

## Metric Definitions

### Citation Precision

```
citation_precision = valid_cited_evidence_ids / total_cited_evidence_ids
```

- Safe-fallback cases (where draft is a fallback message and has no citations) should be excluded from average or marked `None`.
- If `total_cited_evidence_ids == 0`, return `None` (not a failure — just no citations).
- If `available_evidence_ids == 0` and citations exist, precision is 0.0 (citation to nothing).

### Evidence Coverage

```
evidence_coverage = valid_cited_evidence_ids / available_evidence_ids
```

- Proportion of available evidence IDs that were actually cited.
- If `available_evidence_ids == 0`, return `None`.
- Range: 0.0–1.0.

### Unsupported Claim Rate

```
unsupported_claim_rate = cases where len(unsupported_claims) > 0 / total_cases
```

### Forbidden Promise Rate

```
forbidden_promise_rate = cases where has_forbidden_promise == True / total_cases
```

### Claim Guard Pass Rate

```
guard_pass_rate = cases where guard_passed == True / total_cases
```

### Citation Validation Pass Rate

```
citation_validation_pass_rate = cases where citation_validation.is_valid == True / total_cases
```

### Human Review Trigger Correctness

This metric compares expected vs. actual human review triggers.

**Expected human review** (input state before draft generation):
- `must_human_review` is True from risk assessment
- `risk_flags` is non-empty
- `evidence_candidates` is empty or insufficient
- `escalation_reason` exists after generation
- `unsupported_claims` is non-empty after generation

**Actual human review**:
- Final `draft.must_human_review` after all propagation

```
hr_trigger_recall = cases where expected_hr == True and actual_hr == True / cases where expected_hr == True
hr_trigger_precision = cases where expected_hr == True and actual_hr == True / cases where actual_hr == True
hr_trigger_f1 = 2 * recall * precision / (recall + precision)
```

Note: Computing expected_hr requires access to the input ticket state, not just the draft result.

### Reviewer-Ready Rate

A case is **reviewer-ready** when:
- `citation_validation.is_valid == True`
- `guard_result.guard_passed == True`
- `len(draft.unsupported_claims) == 0`

```
reviewer_ready_rate = reviewer_ready_cases / total_cases
```

**Important**:
- High-risk cases (`severity = HIGH`) can be reviewer-ready but `must_human_review` remains `True`. Reviewer-ready does NOT override the risk-based human review requirement.
- Reviewer-ready does **not** mean auto-send. Reviewer-ready means the draft is structurally safe enough for human review to proceed efficiently.

### Latency

- Per-case latency: time from `generate_draft()` call start to result return.
- Average latency, p50, p95 across all cases.
- Only available when timing is recorded in the comparison runner.
- Fake provider: N/A (no network).
- Real provider: measured in comparison runner.

### Cost

- Only if token usage is available from the provider.
- Estimated cost = input_tokens × input_price + output_tokens × output_price.
- If not available, mark as not measured.
- Must not log or store actual token counts or pricing in reports without explicitly marking as estimates.

## Implementation Plan

### Phase 13.2: Metric Computation Module

Create `src/ticketpilot/evaluation/draft_comparison_metrics.py` with pure functions:

```python
def citation_precision(result: DraftGenerationResult) -> float | None:
def evidence_coverage(result: DraftGenerationResult) -> float | None:
def unsupported_claim_rate(results: list[DraftGenerationResult]) -> float:
def forbidden_promise_rate(results: list[DraftGenerationResult]) -> float:
def guard_pass_rate(results: list[DraftGenerationResult]) -> float:
def citation_validation_pass_rate(results: list[DraftGenerationResult]) -> float:
def reviewer_ready_rate(results: list[DraftGenerationResult]) -> float:
def hr_trigger_metrics(expected: list[bool], actual: list[bool]) -> dict:
```

All functions are pure (deterministic, no network, no side effects).

### Phase 13.3: Extend Comparison Runner

Modify `scripts/run_phase12_llm_provider_comparison.py`:
- Call `generate_draft()` → extract full `DraftGenerationResult`
- Serialize per-case: citation validation fields, guard result fields, unsupported claims, reviewer-ready flag
- Output extended rows JSON with all new fields
- Compute summary metrics from extended rows

### Phase 13.4: Unit Tests

Add tests in `tests/unit/test_draft_comparison_metrics.py`:
- Test each metric function with known inputs
- Test edge cases: empty citations, no evidence, safe-fallback, all-pass, all-fail
- Test reviewer-ready definition: high-risk + guard-pass should be reviewer-ready

### Phase 13.5: Regenerate Reports

- Re-run fake baseline comparison
- Regenerate `phase12_llm_provider_comparison_rows.json` with extended fields
- Regenerate `phase12_llm_provider_comparison_summary.json` with all new metrics
- Regenerate markdown report with metric tables
- Optionally re-run real provider if configured

### Phase 13.6: Update Portfolio Docs

- `ticketpilot_metrics_dashboard.md`: update not-yet-measured metrics
- `phase12_provider_comparison_analysis.md`: add extended metrics
- `phase12_reviewer_ready_metric.md`: mark as implemented, update data
- `phase12_error_analysis.md`: add Phase 13 findings

## Boundary Constraints

All metrics are computed from offline synthetic fixture data. Claims must include:
- "local demo / portfolio prototype"
- "offline evaluation only"
- "offline fixture-based comparison"
- "not a real-world benchmark"
- "not production-ready"
- "no real customer data"
