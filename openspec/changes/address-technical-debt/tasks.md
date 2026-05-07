# Tasks: Address Technical Debt

## Task List

### B2: Fix _build_prompt_input Discarded (Simplest)

- [x] Read `src/ticketpilot/drafting/generator.py` lines 180-220
- [x] Identify what `_build_prompt_input` returns
- [x] Either use the return value OR remove the call
- [x] Run unit tests to verify no regression
- [x] Update tasks.md when done

### B3: Extract safe-fallback Utility

- [x] Identify common patterns between claim_guard.py and draft_citation_validator.py
- [x] Create `src/ticketpilot/drafting/_safe_fallback.py` with shared function
- [x] Update `claim_guard.py` to import from shared module
- [x] Update `draft_citation_validator.py` to import from shared module
- [x] Run unit tests to verify no regression
- [x] Update tasks.md when done

### B1: Fix claim_guard Mapping Error

- [x] Read `src/ticketpilot/drafting/claim_guard.py` lines 265-275
- [x] Understand `citation_coverage` vs `has_uncited_claims` semantics
- [x] Fix mapping: `citation_coverage < 1.0` should NOT add `UNCITED_SUBSTANTIVE_CLAIM`
- [x] Update related tests if needed
- [x] Run unit tests to verify no regression
- [x] Update tasks.md when done

### A2: Update ARCHITECTURE.md

- [ ] Read current `docs/technical/ARCHITECTURE.md`
- [ ] Update embedding/LLM sections to reflect opt-in reality
- [ ] Add Phase 15 Chat Copilot section
- [ ] Verify no claims contradict current implementation
- [ ] Update tasks.md when done

### A1: Fix RetrievalTrace Class Collision (If Time Permits)

- [ ] Identify which `RetrievalTrace` is used where
- [ ] Rename `retrieval/schema/retrieval.py`'s class to `RetrievalSchema`
- [ ] Update any imports from `retrieval/schema/retrieval.py`
- [ ] Run unit tests to verify no regression
- [ ] Update tasks.md when done

## Dependencies

- B2 must complete before B3
- B3 must complete before B1
- A2 has no dependencies (documentation only)
- A1 depends on understanding the full import graph

## Exit Criteria

- All tasks marked done
- Quality gate: `uv run ruff check .` passes
- Unit tests: all pass, 0 skipped
- Coverage: >= 70%
- No breaking changes to public API
