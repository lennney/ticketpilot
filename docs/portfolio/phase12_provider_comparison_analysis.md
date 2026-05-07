# Phase 12 Provider Comparison Analysis

**Scope**: Local demo / portfolio prototype — offline provider comparison
**Generated**: 2026-05-07
**Source**: `reports/eval/phase12_llm_provider_comparison_summary.json`, `phase12_llm_provider_comparison_rows.json`

---

## 1. Overview

Phase 12 ran an offline provider comparison on a fixed 25-case synthetic fixture set.
Two providers were compared:

- **FakeLLMProvider**: Deterministic template-based provider. Default for quality gate. Validates pipeline mechanics only — no semantic generation quality.
- **OpenAICompatibleProvider (deepseek-v4-pro)**: Real OpenAI-compatible API provider. Opt-in via `TICKETPILOT_LLM_PROVIDER=openai_compatible` in `.env.local`. Runs against the DeepSeek API.

Both providers received the same evidence (mock) and the same case parameters. The comparison focuses on: case success rate, confidence scores, and human review triggers.

**Boundary**: This is an offline fixture-based comparison — not a production benchmark, not a real-world evaluation, not online performance measurement.

---

## 2. Summary Comparison

| Metric | FakeLLMProvider | OpenAICompatibleProvider (deepseek-v4-pro) |
|--------|-----------------|---------------------------------------------|
| Cases | 25 | 25 |
| Success count | 25 / 25 (100%) | 25 / 25 (100%) |
| Avg confidence | 0.85 | 0.70 |
| Human review triggers | 8 / 25 (32%) | 8 / 25 (32%) |
| Has citations | 25 / 25 (100%) | 25 / 25 (100%) |
| API errors | N/A (no network) | 0 |
| Citation precision | not yet measured | not yet measured |
| Unsupported claim rate | not yet measured | not yet measured |
| Forbidden promise count | not yet measured | not yet measured |
| Guard pass rate | not yet measured | not yet measured |
| Latency | N/A | not yet measured |
| Estimated cost | N/A | not yet measured |

**Source**: `reports/eval/phase12_llm_provider_comparison_summary.json`

---

## 3. Per-Case Breakdown

Both providers succeeded on all 25 cases. Human review triggers were identical (8 cases) across both providers.

Cases triggering human review (both providers):
- `p12_011`: privacy_risk
- `p12_012`: privacy_risk
- `p12_013`: account_security_risk
- `p12_014`: account_security_risk
- `p12_015`: legal_complaint
- `p12_016`: legal_complaint
- `p12_017`: compensation_risk
- `p12_018`: compensation_risk

All 8 human-review cases are high-risk scenarios (privacy, account security, legal, compensation). This confirms the human review rule correctly targets risk types that require human judgment.

Cases NOT triggering human review (both providers):
- `p12_001`–`p12_010`: ordinary_product_consulting, refund, return_exchange, logistics, complaint
- `p12_019`–`p12_025`: evidence_insufficient, policy_conflict, technical_issue, ordinary_product_consulting

**Source**: `reports/eval/phase12_llm_provider_comparison_rows.json`

---

## 4. Confidence Interpretation

### Why Confidence Alone Is Not a Quality Metric

**FakeLLMProvider avg confidence: 0.85**
Fake provider confidence is derived from mock evidence scores — it is a structural signal, not a semantic one. It tests whether the pipeline correctly propagates evidence scores into the draft metadata.

**OpenAICompatibleProvider avg confidence: 0.70**
Real provider confidence reflects the LLM's own judgment of response quality. A lower confidence does not mean worse output — it may mean the model is more calibrated or conservative.

### Why Lower/Higher Confidence Should Be Interpreted Carefully

1. **Confidence is not comparable across providers.** FakeLLMProvider uses a deterministic mapping from evidence scores. OpenAI-compatible providers return model-reported confidence. These are computed differently and on different scales.

2. **Confidence is not correctness.** A confidence of 0.85 from FakeLLMProvider does not mean 85% of drafts are correct. A confidence of 0.70 from the real provider does not mean the drafts are worse.

3. **Confidence does not capture safety.** Both providers produced the same human review trigger pattern (8/25). Neither confidence score tells us whether drafts contain unsupported claims or forbidden promises.

4. **On a fixed fixture set, identical human review triggers are more meaningful than confidence differences.** The fact that both providers triggered human review on the same 8 cases suggests the risk rules are correctly wired — regardless of confidence.

---

## 5. What This Comparison Proves / Does Not Prove

### What This Comparison Proves

- **Pipeline mechanics work end-to-end.** Both providers successfully generated drafts for all 25 cases with citations, suggesting the evidence retrieval, prompt building, citation extraction, and guard wiring are functional.
- **Human review triggers are consistent.** Identical human review triggers across both providers suggest the risk-rule wiring is provider-agnostic.
- **API connectivity is established.** DeepSeek API responded successfully to all 25 requests with no errors.
- **Citation extraction works.** Both providers produced `has_citations: true` for all 25 cases, suggesting `[chunk_id]` citation patterns are correctly embedded in prompt instructions.

### What This Comparison Does NOT Prove

- **It does not prove draft quality.** The 25 cases are synthetic and the evaluation is offline. Real-world customer service drafts would require human evaluation.
- **It is not a production benchmark.** No live traffic, no real customer data, no production system.
- **It does not validate semantic correctness.** Citation presence does not mean citations are accurate. Draft text was not audited for factual correctness.
- **It does not validate claim guard effectiveness.** Forbidden promise count and unsupported claim rate were not measured in this comparison.
- **It does not measure latency or cost.** Real deployment would require production latency and cost analysis.
- **It does not validate citation precision.** Whether cited evidence IDs actually correspond to the content cited was not audited.
- **The 25-case fixture set is not representative.** It covers diverse scenarios but is not a statistically significant sample.

---

## 6. Next Steps for Deeper Comparison

To move from a basic comparison to a meaningful evaluation:

1. **Add claim guard metrics to Phase 12 runner**: extend rows to include `guard_passed`, `has_forbidden_promise`, `has_uncited_claims`
2. **Add citation validation metrics**: audit whether cited evidence IDs match the evidence actually used in the draft
3. **Measure latency and cost**: time API calls and estimate per-case cost at scale
4. **Human evaluation of draft text**: have a human reviewer assess draft quality on a subset of cases
5. **Expand fixture set**: 25 cases is a starting point — larger sets would give more confidence
6. **Test on edge cases**: low-evidence scenarios, ambiguous intent, multi-turn complexity
