# Proposal: Extended Draft Evaluation Metrics

## Problem Statement

Phase 12 ran an offline provider comparison between FakeLLMProvider and OpenAICompatibleProvider (deepseek-v4-pro) on a fixed 25-case synthetic fixture set. The comparison established:

1. **API connectivity**: Both providers successfully generated drafts for all 25 cases with no API errors.
2. **Human review triggers**: Identical human review patterns across both providers (8/25 cases, all high-risk types).
3. **Citation presence**: All 25 cases produced drafts with citations.

However, Phase 12's dashboard and comparison analysis identified significant measurement gaps. The following metrics were marked **not yet measured**:

- Citation precision (are cited evidence IDs valid?)
- Evidence coverage (what proportion of available evidence was cited?)
- Unsupported claim rate (do drafts make claims not grounded in evidence?)
- Forbidden promise rate (do drafts contain prohibited commitments?)
- Claim guard pass rate
- Citation validation pass rate
- Human review trigger correctness (does must_human_review fire when it should?)
- Reviewer-ready rate (composite of citation_valid + guard_passed + no unsupported claims)
- Latency / cost (for real provider)

These gaps make the draft evaluation less product-readable and less interview-ready.

## Proposed Solution

Extend the Phase 12 provider comparison runner and the existing draft evaluation infrastructure to compute all the above metrics, using data already produced by `generate_draft()` and available in `DraftGenerationResult`:

- `citation_validation` (DraftCitationValidationResult): is_valid, valid/invalid cited IDs, available evidence IDs
- `guard_result` (GuardResult): guard_passed, has_forbidden_promise, has_uncited_claims, citation_coverage

The runner already calls `generate_draft()` but only extracts `draft_text_length`, `confidence`, `must_human_review`, `fallback_reason`, `escalation_reason`, `has_citations`, `safety_notes_count`. It needs to extract the full `DraftGenerationResult` fields.

## Scope

### In Scope

- Extend Phase 12 provider comparison runner to extract citation validation and claim guard results per case
- Add metric computation functions in `evaluation/draft_metrics.py` or a new module
- Compute all Phase 12 not-yet-measured metrics
- Regenerate fake baseline comparison with extended output
- Optionally run real provider comparison if configured
- Update portfolio docs (metrics dashboard, provider comparison analysis, reviewer-ready metric, error analysis)
- Add unit tests for new metric functions

### Out of Scope

- Retrieval tuning, RRF changes, embedding changes, knowledge expansion, golden label modifications
- Production deployment, auto-send, online A/B testing
- Real-world benchmark claims
- Modifying archived Phase 7/8/9/10/11 reports

## Success Criteria

- Citation precision, evidence coverage, unsupported claim rate, forbidden promise rate, guard pass rate, citation validation pass rate, reviewer-ready rate computed from Phase 12 fixture data
- Fake baseline regenerated with extended metrics
- Real provider comparison regenerated if configured
- All new metric functions have unit tests
- Portfolio docs updated with new metrics
- ruff clean, openspec --all valid, secret scan clean
- No benchmark or production claims
