# Proposal: Real LLM Provider Offline Comparison

## Why

Phase 11 built evidence-grounded draft generation infrastructure. FakeLLMProvider validates pipeline mechanics deterministically. To assess semantic quality of LLM-generated drafts, a real provider comparison is needed — but as an offline, fixture-based, opt-in comparison, not a production integration.

This enables portfolio evidence without production deployment.

## What Changes

1. `src/ticketpilot/drafting/openai_compatible_provider.py` — OpenAI-compatible LLM provider
2. `src/ticketpilot/drafting/provider_config.py` — extended to support openai_compatible
3. `tests/fixtures/phase12_draft_comparison_cases.json` — 25 synthetic fixture cases
4. `scripts/run_phase12_llm_provider_comparison.py` — offline comparison runner
5. `tests/unit/test_openai_compatible_llm_provider.py` — unit tests (mock only, no network)
6. `tests/integration/test_phase12_llm_provider_comparison.py` — integration tests
7. `reports/eval/phase12_llm_provider_comparison_report.md` — comparison report
8. `docs/technical/phase12_real_provider_comparison.md` — technical documentation
9. OpenSpec change files (proposal, design, tasks, spec)

## Non-Goals

- Production deployment
- Live customer integration
- Auto-send capability
- Real customer data
- Real-world benchmark
- Online A/B testing
- Retrieval tuning
- Knowledge expansion
- Golden label modification

## Scope Boundaries

- local demo / portfolio prototype
- synthetic/adapted data only
- offline evaluation only
- draft-only
- no auto-send
- human-in-the-loop
- no production-ready claim
- no real enterprise validation
- no real customer data
- no real-world benchmark claim