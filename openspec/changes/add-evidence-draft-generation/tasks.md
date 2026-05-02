## Phase 1: Drafting Schemas

- [x] 1.1 Create `src/ticketpilot/drafting/__init__.py` with package exports
- [x] 1.2 Create `src/ticketpilot/drafting/schemas.py` with Pydantic models:
  - `Citation` — single evidence reference used in a draft reply:
    - `chunk_id: UUID`
    - `doc_id: UUID`
    - `doc_type: DocType`
    - `source_table: str`
    - `source_id: UUID`
    - `evidence_excerpt: str` — short excerpt of cited evidence (max 200 chars)
    - `claim_supported: bool`
  - `DraftReply` — the generated draft:
    - `ticket_id: str` — links back to the processed ticket
    - `draft_text: str` — the full draft reply text
    - `citations: list[Citation]` — evidence citations grounding the reply
    - `evidence_used: list[Citation]` — which evidence items were used
    - `unsupported_claims: list[str]` — claims lacking citation backing
    - `missing_information: list[str]` — information gaps identified
    - `confidence: float` — confidence score in [0.0, 1.0]
    - `must_human_review: bool` — whether human review is required
    - `fallback_reason: str | None` — why fallback was triggered
    - `generation_trace: dict | None` — optional trace data
  - `DraftGenerationTrace` — full trace of draft generation:
    - `ticket_id: str`
    - `evidence_used: list[Citation]`
    - `evidence_count: int`
    - `total_evidence_available: int`
    - `confidence_score: float`
    - `unsupported_claims: list[str]`
    - `human_review_required: bool`
    - `fallback_reason: str | None`
    - `created_at: datetime`
- [x] 1.3 Write unit tests in `tests/unit/test_drafting_schemas.py`:
  - Instantiate Citation with all fields
  - Instantiate DraftReply with valid fields
  - Verify `confidence` defaults to `0.0` and `must_human_review` defaults to `False`
  - Verify `DraftReply.confidence` rejects values < 0.0 or > 1.0
  - Verify `evidence_excerpt` max length 200
  - Verify Citation preserves chunk_id, doc_id, doc_type, source_table, source_id

## Phase 2: Draft Provider Interface + FakeDraftProvider

- [x] 2.1 Create `src/ticketpilot/drafting/provider.py` with:
  - `AbstractDraftProvider` abstract base class with one method:
    - `generate(evidence_candidates: list[EvidenceCandidate], risk_assessment: RiskAssessment, classification: ClassificationResult, normalized_text: str) -> DraftReply`
  - `FakeDraftProvider` implementing `AbstractDraftProvider`:
    - Deterministic template-based generation: uses evidence candidates to produce a reply
    - Template structure: acknowledgment + evidence-grounded resolution + closing
    - Each evidence candidate referenced as a `Citation` in the draft
    - `must_human_review` set to `True` when risk assessment demands it
    - Falls back to a no-evidence safe message when `evidence_candidates` is empty
    - No network calls, no API keys, no environment variables
- [x] 2.2 Write unit tests in `tests/unit/test_drafting_provider.py`:
  - Test that FakeDraftProvider returns a DraftReply with correct type
  - Test with 1, 3, and 5 evidence candidates
  - Test that citations contain chunk_ids matching input evidence
  - Test that no-evidence input produces safe fallback message
  - Test determinism (same input yields identical output)
  - Test `must_human_review` is `True` when risk assessment demands it
  - Test no network/external calls

## Phase 3: CitationValidator

- [x] 3.1 Create `src/ticketpilot/drafting/citation_validator.py` with:
  - `CitationValidator` class with:
    - `validate(text: str, citations: list[Citation]) -> tuple[bool, list[str]]`
    - Returns `(passed: bool, issues: list[str])`
    - Validation rules:
      1. Citation existence check: every `[N]` reference in `text` must have a corresponding entry in `citations`. If `text` cites `[3]` but only 2 citations exist, flag it.
      2. Claim-coverage pattern scan: use regex patterns to detect common factual claim phrasings (根据, 按照, 可以, 承诺, 退款, 赔偿) that lack a citation marker `[N]` in the same sentence.
      3. No-evidence check: if `citations` is empty and `text` contains the safe fallback message, produce a warning (not a failure).
    - Does NOT raise exceptions — always returns a result tuple
- [x] 3.2 Write unit tests in `tests/unit/test_citation_validator.py`:
  - Test validator passes for citations referencing valid evidence
  - Test detection of citation referencing unknown chunk_id
  - Test detection of unsupported claims using simple rule
  - Test validator handles empty inputs gracefully
  - Test multiple issues are accumulated

## Phase 4: Standalone generate_draft() Function (Batch 2)

- [x] 4.1 Create `src/ticketpilot/drafting/generate.py` with a standalone function:
  - `generate_draft(ticket_output: TicketOutput) -> DraftReply`
  - Instantiates `FakeDraftProvider` and `CitationValidator` internally
  - Calls `provider.generate()` with data from `ticket_output`
  - Runs `CitationValidator.validate()` on the result
  - If validation fails, sets `has_unsupported_claims = True` on the DraftReply
  - Wraps everything in try/except with safe fallback on error
- [x] 4.2 Update `src/ticketpilot/drafting/__init__.py` to export `generate_draft`
- [x] 4.3 Write unit tests in `tests/unit/test_drafting_generate.py` for `generate_draft()`:
  - Test with a full TicketOutput (constructed in test) with evidence
  - Test with empty evidence
  - Test with high-risk ticket
  - Test graceful degradation on error

> **Note**: This phase does NOT modify `pipeline.py` or `schema/ticket.py`. The `generate_draft()` function is a standalone composition point. Full pipeline integration (calling `generate_draft` automatically inside `intake_risk_pipeline()`) is deferred to a future change.

## Phase 5: Integration Tests (Batch 2C)

- [x] 5.1 Create `tests/integration/test_drafting_integration.py` with integration test using `run_pipeline_with_draft()`:
  - Construct a real `RawTicket` and call `run_pipeline_with_draft(raw_ticket)`
  - Verify `DraftedTicketResult` structure with both `ticket_output` and `draft_reply`
  - Verify citations reference actual evidence chunk IDs when evidence exists
  - Verify high-risk case preserves `must_human_review=True`
- [x] 5.2 Verify no-evidence / low-confidence scenario:
  - Empty ticket text still produces a safe `DraftReply` (no crash)
  - If no evidence candidates, draft uses fallback message
  - If evidence exists, draft has citations with proper field types
- [x] 5.3 Verify high-risk integration:
  - Call with a legal/complaint ticket that triggers `LEGAL_RISK`
  - Verify `must_human_review=True` in both `ticket_output` and `draft_reply`
- [x] 5.4 Verify determinism:
  - Same input produces identical draft output across repeated calls

## Phase 6: Quality Gate and Documentation (Batch 2)

- [ ] 6.1 Update `docs/changelog.md` with evidence draft generation entry
- [ ] 6.2 Update `docs/technical_decisions.md` with drafting architecture decisions:
  - FakeDraftProvider chosen for deterministic, testable generation (no real LLM in MVP)
  - Template-based Chinese reply generation
  - CitationValidator as lightweight guard before any future LLM integration
  - Fallback patterns for no-evidence and high-risk scenarios
- [ ] 6.3 Run full quality gate: `bash scripts/run_quality_gate.sh`

## Phase 7: Optional Pipeline Entrypoint (Batch 2B)

- [x] 7.1 Add `DraftedTicketResult` wrapper schema to `src/ticketpilot/drafting/schemas.py`:
  - `ticket_output: TicketOutput`
  - `draft_reply: DraftReply`
- [x] 7.2 Create `src/ticketpilot/drafting/pipeline.py` with:
  - `run_pipeline_with_draft(raw_ticket: RawTicket) -> DraftedTicketResult`
  - Composes existing `intake_risk_pipeline()` + `generate_draft()` without modification
  - Returns wrapper result preserving both TicketOutput and DraftReply
- [x] 7.3 Update `src/ticketpilot/drafting/__init__.py` to export `DraftedTicketResult` and `run_pipeline_with_draft`
- [x] 7.4 Write unit tests in `tests/unit/test_drafting_pipeline.py`:
  - Returns DraftedTicketResult with ticket_output and draft_reply
  - Calls intake_risk_pipeline exactly once
  - Calls generate_draft exactly once with returned TicketOutput
  - Preserves high-risk must_human_review
  - Does not mutate TicketOutput
  - Deterministic for same mocked inputs
- [x] 7.5 Update `docs/changelog.md` with Batch 2B entry

## Batch Plan Summary

- **Batch 1**: Phases 1-3 (schemas + FakeDraftProvider + CitationValidator + unit tests). Creates only new files in `src/ticketpilot/drafting/` and `tests/unit/`. Zero risk to existing code or tests.
- **Batch 2**: Phases 4-6 (standalone `generate_draft()` function, integration tests, documentation). Uses `generate_draft(ticket_output: TicketOutput) -> DraftReply` — no modifications to `pipeline.py` or `schema/ticket.py`.

## Recommended Batch 1 Entry Point

Start with: Phase 1 (schemas) — new file `src/ticketpilot/drafting/schemas.py` with Citation, DraftReply, DraftGenerationTrace
