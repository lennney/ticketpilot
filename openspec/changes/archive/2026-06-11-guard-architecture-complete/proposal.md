# Proposal: Guard Architecture Improvement — Granular Failure Taxonomy

## Why

Phase 13.10 (guard-aware prompting) improved real provider guard pass rate from 4% to 84% on 25 synthetic cases. The remaining 4 failures reveal that the current `GuardResult` schema uses simplified boolean fields (`has_uncited_claims`, `has_forbidden_promise`, `risk_flags_respected`) that cannot distinguish between distinct failure modes. Without granular taxonomy, it is impossible to:
1. Prioritize which failure types to address first
2. Distinguish correct blocks from false positives
3. Design targeted improvements (prompt vs. architecture vs. validation rule)
4. Report meaningful per-failure-type metrics

## What Changes

This OpenSpec change introduces a granular `GuardFailureType` taxonomy to classify distinct guard failure modes. The taxonomy extends — not replaces — the existing `GuardResult` schema. Current boolean fields (`has_uncited_claims`, `has_forbidden_promise`, `risk_flags_respected`) are preserved for backward compatibility.

### Taxonomy Types

| Type | Description | Detection Method |
|---|---|---|
| `UNSUPPORTED_POLICY_CLAIM` | Substantive policy/factual claim without citation | Pattern: substantive text without `[chunk_id]` |
| `FORBIDDEN_PROMISE` | Refund/compensation/legal/timeline promise | Regex: 9 forbidden patterns |
| `UNCITED_SUBSTANTIVE_CLAIM` | Alias for UNSUPPORTED_POLICY_CLAIM | Same as above |
| `MISSING_RISK_ESCALATION` | HIGH severity / risk flag ticket without escalation language | Pattern: severity/risk present, escalation keywords absent |
| `SAFE_ESCALATION_STATEMENT` | Draft contains safe escalation language | Pattern: 人工/转人工/人工处理 keywords |
| `MANUAL_REVIEW_ACKNOWLEDGEMENT` | Draft acknowledges human review requirement | Pattern: 人工审核/需人工 review keywords |
| `EVIDENCE_INSUFFICIENT_FALLBACK` | Draft uses safe fallback when evidence insufficient | Exact string match: safe fallback text |
| `AMBIGUOUS_GUARD_CASE` | Cannot determine failure type from current data | Catch-all for indeterminate cases |

## What Does NOT Change

- `ClaimGuard` boolean fields remain intact (`has_uncited_claims`, `has_forbidden_promise`, `risk_flags_respected`, `guard_passed`)
- Citation validator unchanged
- DraftReply schema unchanged
- Human review requirements unchanged
- No-auto-send invariant unchanged
- No weakening of any guard check

## Scope

This phase (14.1) is **planning and spec only** — no runtime code changes.

Future phases will:
- Add `GuardFailureType` enum to schema
- Extend `GuardResult` with `failure_reasons: list[GuardFailureType]`
- Add safe escalation language classifier
- Integrate taxonomy into evaluation runner
- Update reviewer console display

## Out of Scope

- Claim guard weakening
- Citation validator weakening
- Human review requirement reduction
- Real provider calls
- Retrieval changes
- Knowledge data changes
- Golden label changes

## Evaluation

After implementation (future phases):
- Per-failure-type pass rate on 25 synthetic cases
- False positive rate per taxonomy type
- Ambiguous guard case rate
- Comparison with Phase 13.10 guard pass rate (must not decrease)
