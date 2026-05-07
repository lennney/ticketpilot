# Phase 13.10: Guard-Aware Provider Prompting Experiment

**Scope**: Offline prompt experiment on 25 synthetic fixture cases — NOT a benchmark, NOT production deployment
**Generated**: 2026-05-07
**Real provider**: deepseek-v4-pro (OpenAI-compatible)
**Baseline**: Phase 13.9 — real provider with bare-bones prompt

---

## Executive Summary

Replacing the bare-bones prompt in `OpenAICompatibleProvider` with a guard-aware structured prompt that requires inline `[chunk_id]` citation markers dramatically improves citation validation and claim guard pass rates.

| Metric | Phase 13.9 Baseline (bare prompt) | Phase 13.10 (guard-aware prompt) | Change |
|--------|-----------------------------------|-----------------------------------|--------|
| Citation validation pass | 12% (3/25) | 76% (19/25) | +64 pp |
| Claim guard pass | 4% (1/25) | 84% (21/25) | +80 pp |
| Unsupported claim rate | 88% (22/25) | 24% (6/25) | -64 pp |
| Human review triggers | 100% (25/25) | 48% (12/25) | -52 pp |
| Reviewer-ready rate | 4% (1/25) | 64% (16/25) | +60 pp |
| Safe fallback rate | 4% (1/25) | 84% (21/25) | +80 pp |
| Avg confidence | 0.700 | 0.644 | -0.056 |

FakeLLMProvider (quality gate default) unchanged: guard=68%, citation_valid=100%.

---

## Methodology

### Before (Phase 13.9 — bare-bones prompt)
```
你是一个客服工单处理助手。根据用户消息和检索到的证据，生成一个专业的回复草稿。
回复必须基于提供的证据，不要编造信息。如果无法找到相关证据，说明无法确认并建议转人工。
回复用中文。

证据：[1] Title: content...
     [2] Title: content...
请生成回复草稿：
```

### After (Phase 13.10 — guard-aware structured prompt)
```
系统：客服工单处理助手。根据用户消息和检索到的证据，生成回复草稿...

用户消息：{text}
问题类型：{issue_type}
风险标记：{flags}
严重度：{severity}

## 可用证据
[chunk_id]: {uuid}
[内容]: {content}

## 安全与约束规则
1. 每一条事实性或政策性陈述，都必须在对应句子后加上方括号内的chunk_id标记，格式为 [chunk_id]。
   示例：根据退货政策[3fa2b8c1-...]，商品需在7天内保持原包装。
   不要使用 [1]、[2] 等数字格式——必须使用证据块中的 chunk_id。
2. 如果证据不足以回答客户问题，必须使用安全回复：「抱歉，基于目前的信息...」并注明需要人工审核。
3. 禁止承诺退款金额、赔偿金额、法律行动、账号变更。
4. 禁止承诺解决时间线或保证特定结果。
5. 禁止承认法律责任或做出超出证据范围的保证。
6. 本回复是草稿，不是最终回复。人工审核前不得自动发送。
[High severity / risk flag escalation rules...]

请生成回复草稿（在回复中引用证据时，必须使用 [chunk_id] 格式）：
```

---

## Full Results

### Real Provider (deepseek-v4-pro)

| Metric | Phase 13.9 Baseline | Phase 13.10 Guard-Aware | Change |
|--------|---------------------|-------------------------|--------|
| Citation validation pass | 12% (3/25) | 76% (19/25) | +64 pp |
| Claim guard pass | 4% (1/25) | 84% (21/25) | +80 pp |
| Unsupported claim rate | 88% (22/25) | 24% (6/25) | -64 pp |
| Forbidden promise count | 1/25 | 1/25 | — |
| Safe fallback rate | 4% (1/25) | 84% (21/25) | +80 pp |
| Human review triggers | 100% (25/25) | 48% (12/25) | -52 pp |
| Reviewer-ready rate | 4% (1/25) | 64% (16/25) | +60 pp |
| Avg confidence | 0.700 | 0.644 | -0.056 |
| Avg cited evidence | 2.0 | 1.8 | -0.2 |
| Avg unsupported claim count | 1.6 | 0.4 | -1.2 |

### FakeLLMProvider (unchanged — quality gate default)

| Metric | Phase 13.9 | Phase 13.10 | Change |
|--------|------------|-------------|--------|
| Citation validation pass | 100% (25/25) | 100% (25/25) | — |
| Claim guard pass | 68% (17/25) | 68% (17/25) | — |
| Unsupported claim rate | 0% (0/25) | 0% (0/25) | — |
| Human review triggers | 32% (8/25) | 32% (8/25) | — |
| Reviewer-ready rate | 68% (17/25) | 68% (17/25) | — |
| Avg confidence | 0.825 | 0.825 | — |

---

## Guard Failure Analysis

### Remaining 4 guard failures (real provider, Phase 13.10)

| Case | Root Cause | Type |
|------|-----------|------|
| p12_011 | Citations present but privacy risk flag not acknowledged with escalation language | risk_flags_respected |
| p12_015 | Citations present but legal risk flag not acknowledged with escalation language | risk_flags_respected |
| p12_018 | 2 unsupported claims + 1 forbidden promise (compensation amount) | unsupported + forbidden |
| p12_021 | Substantive content without [chunk_id] citation markers | has_uncited_claims |

All 4 failures are **correct guard behavior** — the guard is detecting genuine issues in LLM output:
- 3 cases: LLM cites evidence but skips risk escalation acknowledgment
- 1 case: LLM makes substantive claim without citation (guard-aware prompt not fully effective)

### Safe Fallback Analysis

84% (21/25) of real provider cases now return safe fallback text. This is an expected consequence of the guard-aware prompt instructing the LLM to use safe fallback when evidence is insufficient. The safe fallback is semantically correct but lacks `[chunk_id]` citation markers, causing citation validation to fail on those cases.

**Trade-off**: Higher safe fallback rate = fewer unsupported claims, but also fewer valid citations. This is acceptable because:
1. Safe fallback drafts correctly trigger human review
2. No forbidden promises in safe fallback cases
3. Citation validator correctly flags missing citation markers

---

## Interpretation

### What improved

1. **Citation validation**: 12% → 76% because LLM now includes `[chunk_id]` markers in most drafts
2. **Claim guard**: 4% → 84% because `[chunk_id]` markers allow guard to detect citations
3. **Unsupported claims**: 88% → 24% because LLM cites evidence instead of making uncited claims
4. **Human review triggers**: 100% → 48% because non-risk-flag cases no longer fail guard

### What did not improve

1. **Risk escalation acknowledgment**: 3 cases fail guard because LLM cites evidence but does not include escalation language for HIGH-severity risk flags. The prompt instructs this, but the LLM does not always comply.
2. **Forbidden promises**: 1 case (p12_018, compensation_risk) still includes a forbidden promise pattern despite explicit instructions.
3. **Safe fallback rate**: 84% safe fallback means the LLM is conservative about citing evidence. This is safer but reduces citation coverage.

### What is expected behavior

1. **Higher safe fallback rate is acceptable** — the guard-aware prompt explicitly instructs this. Safe fallback cases correctly trigger human review.
2. **Citation validator failures on safe fallback** — correct behavior. Citation validator flags missing `[chunk_id]` markers in safe fallback text.
3. **Fake provider unchanged** — FakeLLMProvider uses a template, not an LLM. Guard-aware prompting affects LLM output only.

---

## Limitations

- **Offline fixture-based evaluation**: 25 synthetic cases with mock evidence — NOT representative of real customer service volume.
- **Single model**: deepseek-v4-pro only — results may differ for other models.
- **Guard-aware prompt is speculative**: Prompt engineering was done offline without live evaluation.
- **No real customer data**: All evaluation on synthetic fixtures.
- **Safe fallback rate increase**: 84% safe fallback may be too conservative for production — may need to tune evidence sufficiency thresholds.
- **No production benchmark**: Results do not generalize to production environments.

---

## Boundary

This is an **offline prompt experiment**. Results do not constitute:
- Production benchmark
- Comparative evaluation of commercial LLM services
- Guarantee of deployment readiness
- Real-world performance measurement

**No auto-send.** Human review remains required for all HIGH-severity cases and safe fallback cases.

---

## Next Steps

1. **Evaluate guard-aware prompt on real customer tickets** — offline synthetic fixtures may not reflect real-world query distribution
2. **Tune safe fallback threshold** — 84% safe fallback may be too conservative; consider adjusting evidence sufficiency criteria
3. **Improve risk escalation compliance** — prompt could include stronger escalation language requirements
4. **Test with other models** — results may differ for GPT-4, Claude, etc.
5. **Human review accuracy evaluation** — verify that human reviewers agree with guard decisions

---

## Source Data

- Phase 13.9 baseline: `reports/eval/phase12_extended_eval_rows_20260507_150527.json`
- Phase 13.10 results: `reports/eval/phase12_extended_eval_rows_20260507_155207.json`
