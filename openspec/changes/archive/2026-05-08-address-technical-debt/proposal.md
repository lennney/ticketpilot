# Proposal: Address Technical Debt

## Problem Statement

The codebase has accumulated technical debt across multiple phases:

1. **RetrievalTrace class name collision** — `retrieval/traces.py` and `retrieval/schema/retrieval.py` both define `RetrievalTrace`
2. **ARCHITECTURE.md out of sync** — Claims no real embedding/LLM, but code already has `OpenAICompatibleProvider`
3. **claim_guard mapping error** — `citation_coverage < 1.0` incorrectly mapped to `UNCITED_SUBSTANTIVE_CLAIM`
4. **_build_prompt_input discarded** — Result is assigned to `_` and discarded, logic duplicated inline
5. **safe-fallback logic duplicated** — `claim_guard.py` and `draft_citation_validator.py` have identical checks

## Scope

This change addresses:
- Code-level refactoring (B1, B2, B3)
- Documentation sync (A2, C2)
- Architectural cleanup (A1) — only if minimal

**Out of scope:**
- A3 (DraftGenerationResult Pydantic) — low priority, no current impact
- C1 (METRICS.md stale data) — can be updated separately
- D-class items — explicitly not technical debt

## Non-Goals

- No guard weakening
- No schema changes that break existing tests
- No new features

## Success Criteria

- ARCHITECTURE.md reflects current implementation
- claim_guard.py mappings are semantically correct
- No duplicate logic between modules
- All existing tests pass
- Quality gate passes
