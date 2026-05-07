# Tasks: Guard-Aware Provider Prompting

## Task List

- [ ] T1: Update `OpenAICompatibleProvider.generate_draft()` prompt in `llm_provider.py`
  - Replace hardcoded minimal prompt with guard-aware structured prompt
  - Use `format_evidence_block()` for evidence section
  - Add explicit `[{chunk_id}]` citation requirement
  - Add forbidden numeric `[N]` citation instruction
  - Preserve existing `DraftReply` construction logic

- [ ] T2: Add unit tests in `test_prompt_builder.py`
  - Test that guard-aware prompt template includes `[{chunk_id}]` instruction
  - Test that prompt explicitly forbids `[1]`, `[2]` style numeric citations
  - Test that prompt includes safe fallback instruction
  - Test that prompt maintains no-auto-send boundary

- [ ] T3: Run smoke test (5 cases) with real provider
  - Verify no API errors
  - Check draft text includes at least one `[chunk_id]` marker
  - Check citation validation pass

- [ ] T4: Run full 25-case comparison with real provider
  - Compare Phase 13.9 baseline vs Phase 13.10 guard-aware results
  - Report: citation validation pass, guard pass, unsupported claim rate, HR triggers

- [ ] T5: Update portfolio docs with guard-aware results
  - Update `phase12_provider_comparison_analysis.md`
  - Update `phase12_reviewer_ready_metric.md`

- [ ] T6: Run full quality gate
  - 1069 unit + 146 integration, 0 skipped, coverage >= 70%
  - Ruff clean, OpenSpec --all pass, secret scan clean

## Dependencies

- T2 depends on T1
- T3 depends on T1 + T2
- T4 depends on T3
- T5 depends on T4
- T6 depends on T1 + T2 + T5

## Exit Criteria

- Real provider guard pass rate improved vs Phase 13.9 baseline (4%)
  - OR: guard-aware prompting confirmed ineffective, limitation documented
- No claim guard or citation validator weakening
- Quality gate: 1069 unit + 146 integration, 0 skipped, coverage >= 70%
- No API key in tracked files
