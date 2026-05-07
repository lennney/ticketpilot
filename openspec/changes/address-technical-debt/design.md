# Design: Address Technical Debt

## Current State

### A1: RetrievalTrace Class Collision

```
src/ticketpilot/retrieval/traces.py     → defines RetrievalTrace
src/ticketpilot/retrieval/schema/retrieval.py → also defines RetrievalTrace
src/ticketpilot/schema/ticket.py      → imports from traces.py
```

**Fix**: Rename `retrieval/schema/retrieval.py`'s class to `RetrievalSchema` or merge if possible.

### A2: ARCHITECTURE.md Out of Sync

Current doc claims:
- "Does not use real embedding providers" → FALSE, `openai_compatible.py` exists
- "Does not connect to real LLM providers" → FALSE, `llm_provider.py` has `OpenAICompatibleProvider`
- No mention of Phase 15 Chat module

**Fix**: Update doc to reflect:
- Real providers available via `.env.local` opt-in
- Phase 15 Chat Copilot layer exists
- Clear boundary: pipeline is deterministic by default

### B1: claim_guard Mapping Error

Current code:
```python
if citation_coverage < 1.0:
    failure_reasons.append(UNCITED_SUBSTANTIVE_CLAIM)
```

Problem: `citation_coverage < 1.0` means "partial citation" not "uncited claim".

**Fix**:
- `citation_coverage < 1.0` → `PARTIAL_CITATION` (new type, if needed) OR
- Only add `UNCITED_SUBSTANTIVE_CLAIM` when `has_uncited_claims = True`

### B2: _build_prompt_input Discarded

```python
# generator.py:184-187 (current)
_prompt_input = _build_prompt_input(ticket_output)  # discarded!
# ... inline duplicate logic ...
```

**Fix**: Use the return value or remove the call.

### B3: safe-fallback Logic Duplicated

Two identical implementations:
- `claim_guard.py:_is_safe_fallback`
- `draft_citation_validator.py:_is_safe_fallback`

**Fix**: Extract to `drafting/_safe_fallback.py` utility.

## Implementation Order

1. B2 (simplest, no risk)
2. B3 (extract shared utility)
3. B1 (guard logic fix, test carefully)
4. A2 (documentation only)
5. A1 (class rename, verify all imports)

## Constraints

- All existing tests must pass after each step
- No breaking changes to public API
- Quality gate: unit tests, 0 skipped, coverage >= 70%
