# Proposal: Guard-Aware Provider Prompting

## Problem

Phase 13.9 discovered that `OpenAICompatibleProvider` generates short free-form Chinese text (80–174 chars) without inline `[chunk_id]` citation markers. The claim guard's content-level check (`has_uncited_claims`) and citation validator's structural check both fail because the LLM output does not include citation markers.

Result: real provider citation validation pass rate = 12%, claim guard pass rate = 4%, human review triggers = 100%.

## Root Cause

`OpenAICompatibleProvider.generate_draft()` uses a minimal hardcoded prompt (lines 250–261 in `llm_provider.py`) that does not:
1. Require inline `[chunk_id]` citation markers for substantive claims
2. Explicitly forbid free-form responses without citation markers
3. Use the existing `build_safety_instructions()` from `prompt_builder.py`

## Proposed Change

Replace the hardcoded prompt in `OpenAICompatibleProvider.generate_draft()` with structured prompt instructions that include:
1. Guard-aware citation instruction: every factual/policy claim must include `[chunk_id]` marker
2. Explicitly forbidden patterns (numeric `[1]`, `[2]` citations, uncited substantive claims)
3. Evidence sufficiency instruction: if evidence insufficient, use safe fallback
4. No-auto-send boundary: draft-only, not final reply
5. Forbidden promise patterns (same as claim guard)

## Scope

- `src/ticketpilot/drafting/llm_provider.py`: replace hardcoded prompt in `OpenAICompatibleProvider.generate_draft()`
- `src/ticketpilot/drafting/prompt_builder.py`: extend `build_safety_instructions()` with more explicit citation format requirements
- `tests/unit/test_prompt_builder.py`: add tests for guard-aware citation instructions
- `tests/unit/test_draft_generator.py`: ensure FakeLLMProvider remains unaffected

## Out of Scope

- Claim guard weakening or bypass
- Citation validator weakening
- Production deployment
- Real customer data
- Online A/B testing
- Retrieval tuning

## Evaluation Plan

1. Run 5-case smoke test with real provider (guard-aware prompt)
2. Run full 25-case comparison with real provider
3. Compare Phase 13.9 baseline vs Phase 13.10 guard-aware results:
   - Citation validation pass rate
   - Claim guard pass rate
   - Unsupported claim rate
   - Human review triggers
   - Confidence

## Risks

- Guard-aware prompting may not be fully effective (LLM may still ignore citation markers)
- Prompt changes are speculative offline — real effectiveness requires live evaluation
- Quality gate must remain FakeLLMProvider-based (real provider is opt-in only)
