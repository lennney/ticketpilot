## Context

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot. The existing pipeline processes a raw Chinese ticket through intake normalization, intent classification, risk assessment, and evidence retrieval, producing a `TicketOutput` with evidence candidates but no actionable reply draft. This change adds a fifth pipeline stage -- draft generation -- that produces an evidence-grounded customer service reply draft in Chinese, with every substantive claim explicitly linked to its supporting evidence chunk via numbered citations.

**Current state**: Four-stage pipeline complete (intake, classification, risk assessment, retrieval). Evidence candidates are returned but no draft reply is generated. The `TicketOutput` model has `evidence_candidates: list[EvidenceCandidate]` and `retrieval_trace: RetrievalTrace | None` but no draft field.

**Constraints**:
- MUST NOT modify `src/ticketpilot/schema/ticket.py` or `src/ticketpilot/schema/evidence.py`
- MUST NOT modify the retrieval engine (`retrieval/` module, `retrieval/traces.py`)
- MUST NOT modify risk assessment, classification, or intake modules
- No real LLM provider code in MVP (deterministic, zero-LLM provider only)
- DraftReply MUST be an optional field on TicketOutput, not a required one
- Existing tests MUST continue to pass without modification


## Goals / Non-Goals

**Goals:**
- `Citation` Pydantic schema linking each claim to its evidence source
- `DraftReply` Pydantic schema with reply text, citations, confidence, and guard flags
- `DraftGenerationTrace` Pydantic schema capturing full generation metadata
- `AbstractDraftProvider` interface for pluggable draft generation
- `FakeDraftProvider` implementation: deterministic, template-based Chinese reply composition from evidence candidates
- `CitationValidator` for unsupported claim detection using regex-based pattern matching
- No-evidence fallback: safe Chinese message when `evidence_candidates` is empty
- High-risk fallback: draft with `human_review_required=True` when risk assessment demands it
- Stage 5 integration into `intake_risk_pipeline()` in `pipeline.py`
- Optional `DraftReply` and `DraftGenerationTrace` on `TicketOutput`
- Graceful degradation: any stage 5 failure produces a safe fallback draft, not a pipeline crash
- Unit and integration tests for all new code

**Non-Goals:**
- Real LLM provider (FakeDraftProvider is the only MVP implementation)
- LangGraph workflow orchestration for the drafting stage
- Streamlit review UI for drafts
- Langfuse/Ragas observability integration
- Evaluation pipeline with golden-answer test sets
- Auto-send or one-click send (all drafts are human-review only)
- Persistent draft generation trace storage in database (traces are in-memory only)
- Post-generation grounding validation for non-fake providers (out of scope until a real LLM provider is added)
- Reranker integration
- Embedding fine-tuning
- Multi-turn or conversational draft generation
- `source_id` DB lookup for multi-chunk documents (maintains seed-only doc_id == source_id assumption)


## Architecture Diagram

```
                                    +------------------+
                                    |   Ticket Input   |
                                    +--------+---------+
                                             |
                                             v
                              +-------------------------+
                              |   Intent Classification |
                              +--------+----------------+
                                         |
                                         v
                              +-------------------------+
                              |    Risk Assessment      |
                              +--------+----------------+
                                         |
                                         v
                              +-------------------------+
                              |   Evidence Retrieval    |
                              |   (keyword + vector)    |
                              +--------+----------------+
                                         |
                                         v
                              +-------------------------+
                              |   Draft Generation      |  <-- NEW
                              +-------------------------+
                              |                         |
                              v                         v
                  +------------------+       +---------------------+
                  |  needs human     |       |  has evidence &&    |
                  |  review?         |       |  low risk           |
                  +-------+----------+       +----------+----------+
                          |                             |
                          v                             v
                  +------------------+       +---------------------+
                  | Safe fallback    |       | Template-based      |
                  | no-promise reply |       | reply composition   |
                  +------------------+       +----------+----------+
                                                         |
                                                         v
                                              +---------------------+
                                              | CitationValidator   |
                                              | (unsupported claim  |
                                              |  guard scan)        |
                                              +----------+----------+
                                                         |
                                                         v
                                              +---------------------+
                                              |   DraftReply +      |
                                              |   DraftGenTrace     |
                                              +---------------------+
```


## New Schemas

Three new Pydantic models live in `src/ticketpilot/drafting/schemas.py`. They are imported by the drafting module only -- no existing schema files are modified.

### Citation

A single evidence reference used in a draft reply. Each citation maps to a numbered reference in the reply body.

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `UUID` | References the knowledge chunk used |
| `doc_id` | `UUID` | References the source document |
| `doc_type` | `DocType` | 'FAQ', 'POLICY', or 'CASE' |
| `source_table` | `str` | Source DB table name |
| `source_id` | `UUID` | Source document UUID |
| `evidence_excerpt` | `str` | Short excerpt of the cited evidence (max 200 chars) |
| `claim_supported` | `bool` | Whether this citation backs a specific claim |

Validation rules:
- `evidence_excerpt` must not exceed 200 characters.
- `chunk_id` must be a valid UUID.

### DraftReply

The generated draft reply with evidence citations and guard flags.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ticket_id` | `str` | required | Links back to the processed ticket |
| `draft_text` | `str` | required | Full generated draft reply text |
| `citations` | `list[Citation]` | `[]` | Evidence citations grounding the reply |
| `evidence_used` | `list[Citation]` | `[]` | Which evidence items were used (may overlap with citations) |
| `unsupported_claims` | `list[str]` | `[]` | Claims detected that lack citation backing |
| `missing_information` | `list[str]` | `[]` | Information gaps identified |
| `confidence` | `float` | `0.0` | Confidence score in [0.0, 1.0] |
| `must_human_review` | `bool` | `False` | Whether human review is required before use |
| `fallback_reason` | `str | None` | `None` | If a fallback path was taken, why |
| `generation_trace` | `dict | None` | `None` | Optional trace data for debugging |

Validation rules:
- `confidence` must be in [0.0, 1.0].

### DraftGenerationTrace

Full trace of the draft generation stage for debugging, audit, and explainability.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ticket_id` | `str` | required | Links back to the processed ticket |
| `evidence_used` | `list[Citation]` | `[]` | Citations that were actually used in the draft |
| `evidence_count` | `int` | `0` | Number of citations in the draft |
| `total_evidence_available` | `int` | `0` | Number of evidence candidates provided to the provider |
| `confidence_score` | `float` | `0.0` | Confidence score of the generated draft |
| `unsupported_claims` | `list[str]` | `[]` | Unsupported claims detected |
| `human_review_required` | `bool` | `False` | Whether human review is required before use |
| `fallback_reason` | `str | None` | `None` | Why a fallback path was taken |
| `created_at` | `datetime` | `utcnow()` | Trace timestamp |


## Evidence-Only Generation Rules

The draft generator enforces four grounding rules at the architectural level. These are documented requirements that the `AbstractDraftProvider` contract must satisfy.

**Rule 1: Each citation maps to a numbered reference in the reply.**

Every `Citation` in `DraftReply.citations` corresponds to a bracketed number in `draft_text` (e.g., `[1]`, `[2]`). The fake provider satisfies this by construction: it numbers each evidence chunk inline. The mapping is 1:1 -- citation `[i]` references `citations[i-1]`.

**Rule 2: Every factual claim must reference at least one citation.**

No factual claim in `draft_text` appears without an accompanying citation marker. Policy statements, compensation amounts, return windows, and procedural steps must all cite their source. Generic courtesy phrases (e.g., "感谢您的耐心等待") are exempt.

**Rule 3: No deterministic policy promises when no evidence supports the claim.**

If a claim about policy, compensation, or procedure cannot be attributed to a retrieved evidence chunk, the generator must not include it. The fake provider satisfies this by deriving all claims from the evidence content directly -- it never invents policy details.

**Rule 4: Reply stays within scope of retrieved evidence.**

The generator must not introduce external knowledge, assumptions about customer intent beyond the ticket text, or policy interpretations that exceed what the evidence supports. The reply is bounded by the evidence candidates returned from retrieval.

**FORBIDDEN: Drafting without citations**

Drafting a reply without attached `Citation` objects for every factual claim defeats the purpose of evidence grounding. Every non-courtesy sentence must be attributable to a source.


## Unsupported Claim Guard

After draft generation, the `CitationValidator` scans the reply for claims not backed by citations. This is a lightweight, regex-based guard -- not an LLM-based semantic check.

### Strategy

The validator performs two checks:

1. **Citation existence check**: Every `[N]` reference in `draft_text` must have a corresponding entry in `citations`. If `draft_text` contains `[3]` but only 2 citations exist, this is flagged.

2. **Claim-coverage pattern scan**: Uses regex patterns to detect common factual claim phrasings that lack a citation marker within the same sentence. Patterns include:
   - 根据... (according to...)
   - 按照...规定 (per... regulation)
   - 可以... (you can...)
   - 将... (will...)
   - 承诺... (promise/guarantee...)
   - 退款... (refund...)
   - 赔偿... (compensation...)
   - 处理... (handle/process...)

   If a sentence matches one of these patterns and contains no `[N]` citation marker, it is flagged as a potentially unsupported claim.

### Behavior

- If unsupported claims are detected: `DraftReply.unsupported_claims` is populated with the issue descriptions, and `DraftReply.must_human_review` is set to `True`.
- The validator does NOT raise exceptions. It always returns a `(passed: bool, issues: list[str])` tuple.
- Multiple issues are accumulated (not short-circuited).
- The validator is stateless and thread-safe.

```python
# Pseudocode for the claim-pattern scan
CLAIM_PATTERNS = [
    r"根据[^，。]*?(?![。]*\[(\d+)\])",
    r"按照[^，。]*?(?![。]*\[(\d+)\])",
    r"可以[^，。]*?(?![。]*\[(\d+)\])",
    r"承诺[^，。]*?(?![。]*\[(\d+)\])",
]

def validate(text: str, citations: list[Citation]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for i, citation_marker in enumerate(find_citation_markers(text), start=1):
        if citation_marker > len(citations):
            issues.append(f"Citation [{citation_marker}] exceeds available citations ({len(citations)})")
    for pattern in CLAIM_PATTERNS:
        for match in re.finditer(pattern, text):
            if not has_citation_in_sentence(text, match):
                issues.append(f"Unsupported claim pattern at position {match.start()}: '{match.group()}'")
    return (len(issues) == 0, issues)
```

**NOT YET: LLM-based semantic claim detection**

The regex approach is imprecise: it will miss subtle claims and may flag false positives. A future change should replace the regex scanner with a small classifier or LLM call that semantically verifies each claim against the evidence text. The `CitationValidator` interface remains the same; only the implementation changes.


## No-Evidence Fallback

When `evidence_candidates` is empty after retrieval, the draft generator must not fabricate a reply. Instead, it produces a standardized safe message:

```
draft_text = "根据现有信息，无法确认具体政策条款，建议转人工处理。"
```

Conditions:
- `confidence = 0.0`
- `unsupported_claims = []` (no claims were made)
- `must_human_review = True`
- `citations = []`
- `DraftGenerationTrace.fallback_reason = "no_evidence"`
- The risk assessment is also updated with `INSUFFICIENT_EVIDENCE` flag (handled by existing pipeline logic)

**FORBIDDEN: Making policy promises without evidence**

When evidence is empty, the draft must never say "根据政策" (according to policy) or similar. The only acceptable reply is the safe fallback message. This is enforced by the `FakeDraftProvider` which has a hardcoded path for empty evidence.


## High-Risk Fallback

When `risk_assessment.must_human_review` is `True`, the pipeline still generates a draft (the agent may find it useful as a starting point), but:

- `DraftReply.must_human_review = True`
- `DraftGenerationTrace.human_review_required = True`
- The draft is preview-only. The system never auto-sends.
- The draft is still generated from evidence; it is not replaced with the no-evidence fallback.
- The fake provider sets `must_human_review = True` on the draft when the risk assessment demands it.

When both high-risk and no-evidence conditions hold (e.g., risk flags include both `must_human_review` and `INSUFFICIENT_EVIDENCE`), the no-evidence fallback takes priority. A ticket with no evidence should never show a substantive draft, regardless of risk level.


## Fake / Deterministic Draft Provider

### AbstractDraftProvider Interface

```python
from abc import ABC, abstractmethod
from ticketpilot.schema.ticket import ClassificationResult, RiskAssessment
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.drafting.schemas import DraftReply


class AbstractDraftProvider(ABC):
    """Interface for draft generation providers."""

    @abstractmethod
    def generate(
        self,
        evidence_candidates: list[EvidenceCandidate],
        risk_assessment: RiskAssessment,
        classification: ClassificationResult,
        normalized_text: str,
    ) -> DraftReply:
        """Generate a reply draft from evidence and ticket context.

        Args:
            evidence_candidates: Retrieved evidence from the knowledge base.
            risk_assessment: Risk assessment result for the ticket.
            classification: Intent classification result.
            normalized_text: Normalized ticket text.

        Returns:
            DraftReply with citations and guard flags.
        """
        ...
```

The interface receives the raw data, not the full `TicketOutput`, to keep the provider focused on the core task. The pipeline wrapper is responsible for mapping `TicketOutput` fields to the provider call.

### FakeDraftProvider

The MVP ships with exactly one implementation: `FakeDraftProvider`. It is deterministic, zero-LLM, and template-based.

**Generation logic:**

1. If `evidence_candidates` is empty, return the no-evidence fallback immediately.
2. Sort evidence candidates by rank (ascending).
3. Take the top 3 evidence candidates (or all if fewer than 3).
4. Build a Chinese reply template:
   - **Opening**: "您好，关于您反馈的问题，" + (classification-derived context)
   - **Body**: For each evidence chunk, compose a sentence using the chunk title and content excerpt. Append a citation marker `[N]`.
   - **Closing**: "希望以上信息对您有帮助。如有其他问题，请随时联系我们。"
5. Create a `Citation` for each evidence chunk used.
6. Compute `confidence`: `min(1.0, max(0.0, average_score_of_evidence_used))`.
7. If `risk_assessment.must_human_review` is `True` or `risk_assessment.severity == RiskSeverity.HIGH`, set `must_human_review = True`.

**Template example (with 2 evidence chunks):**

```
您好，关于您反馈的退款问题，根据相关政策[1]，未发货订单可申请全额退款。同时，
参照类似案例[2]，平台通常在1-3个工作日内完成审核。希望以上信息对您有帮助。
如有其他问题，请随时联系我们。
```

**Key properties:**
- Deterministic: same input always produces identical output.
- No network calls, no API keys, no LLM dependencies.
- Millisecond-level latency.
- All citations reference real evidence chunks by ID.
- Thread-safe (no mutable shared state).


## File Layout for Drafting Module

```
src/ticketpilot/
  drafting/                # New module
    __init__.py             # Exports: Citation, DraftReply, DraftGenerationTrace,
                            #          AbstractDraftProvider, FakeDraftProvider,
                            #          CitationValidator
    provider.py             # AbstractDraftProvider base class + FakeDraftProvider
                            #   (template rendering, citation binding inline)
    citation_validator.py   # CitationValidator: unsupported claim guard
    schemas.py              # Citation, DraftReply, DraftGenerationTrace Pydantic models
    generate.py             # generate_draft(ticket_output) standalone function (Batch 2)
tests/
  unit/
    test_drafting_schemas.py           # Schema validation tests
    test_drafting_provider.py          # FakeDraftProvider tests
    test_drafting_citation_validator.py# CitationValidator tests
    test_drafting_generate.py          # generate_draft() tests (Batch 2)
  integration/
    test_drafting_integration.py       # End-to-end integration tests (Batch 2)
```

### Module Boundaries

| File | Responsibility | Input | Output |
|------|---------------|-------|--------|
| `schemas.py` | Pydantic model definitions only | None (constants + types) | `Citation`, `DraftReply`, `DraftGenerationTrace` classes |
| `provider.py` | Draft provider interface + fake impl (+ template rendering) | Evidence candidates + risk + classification | `DraftReply` |
| `citation_validator.py` | Unsupported claim detection | Reply text + citations | `(passed, issues)` tuple |
| `generate.py` | Standalone composition (Batch 2) | `TicketOutput` | `DraftReply` |

### Dependency Graph

```
schemas.py  (no internal dependencies)
     ^
     |
provider.py  (depends on schemas.py, ticket schema, evidence schema)
     ^
     |
     +--- citation_validator.py  (depends on schemas.py)
     |
     +--- generate.py  (Batch 2, depends on provider + validator + TicketOutput)
```


## Risks / Trade-offs

[Risk] Template-based replies sound mechanical and repetitive
-> The fake provider is intentionally simple for MVP. When a real LLM provider is added, the template is replaced with LLM-generated natural language. The fake provider is for development, CI, and testing only.

[Risk] Regex-based unsupported claim guard has high false-positive / false-negative rate
-> The regex patterns are tuned conservatively for MVP. A future change should replace this with a small classifier or LLM call. The `CitationValidator` interface is stable; only the implementation changes.

[Risk] DraftReply and DraftGenerationTrace increase TicketOutput memory footprint
-> Both are optional fields defaulting to `None`. Draft traces remain in-memory only (no DB persistence). The memory cost per ticket is negligible for MVP scale.

[Risk] FakeDraftProvider may mask real provider issues during development
-> The abstraction layer is designed to catch interface mismatches at compile time. CI runs with the fake provider; a separate evaluation pipeline (future change) runs with the real provider.

[Risk] No-evidence fallback is hardcoded Chinese text
-> Acceptable for MVP. A future change should make fallback messages configurable or locale-aware. The fallback is documented in a single location within `FakeDraftProvider`.

[Risk] Draft generation adds latency to the pipeline even when human review is required
-> The fake provider adds <1 ms. A real LLM provider would add seconds, but only for low-risk tickets. The conditional skip for empty evidence is instant.


## Pipeline Integration Design

### Standalone `generate_draft()` Function

Draft generation is exposed as a standalone function that consumes a `TicketOutput` and produces a `DraftReply`. This preserves the existing `intake_risk_pipeline()` contract (return type unchanged, no test breakage) while making draft generation available to any caller.

```python
def generate_draft(ticket_output: TicketOutput) -> DraftReply:
    """Generate an evidence-grounded draft reply from a processed ticket.

    Args:
        ticket_output: Completed TicketOutput from the intake-risk pipeline.

    Returns:
        DraftReply with citations and guard flags.
    """
    try:
        provider = FakeDraftProvider()
        validator = CitationValidator()

        draft = provider.generate(
            evidence_candidates=ticket_output.evidence_candidates,
            risk_assessment=ticket_output.risk_assessment,
            classification=ticket_output.classification,
            normalized_text=ticket_output.normalized_ticket.text,
        )

        # Run the citation validator
        passed, issues = validator.validate(
            text=draft.draft_text,
            citations=draft.citations,
            evidence_candidates=ticket_output.evidence_candidates,
        )

        if not ticket_output.evidence_candidates:
            passed = True
            issues = []

        if not passed:
            draft.unsupported_claims = issues
            draft.must_human_review = True

        return draft

    except Exception:
        # Graceful degradation: safe fallback on any provider/validator error
        return DraftReply(
            ticket_id=ticket_output.ticket_id,
            draft_text="根据现有信息，无法确认具体政策条款，建议转人工处理。",
            citations=[],
            evidence_used=[],
            unsupported_claims=["生成回复时发生异常"],
            missing_information=["未找到相关证据"],
            confidence=0.0,
            must_human_review=True,
            fallback_reason="generation_error",
        )
```

### Why Not PipelineResult Wrapper

An earlier design considered changing `intake_risk_pipeline()` to return a `PipelineResult` wrapper containing both `TicketOutput` and `DraftReply`. This was rejected because:

1. **Breaks ~30 existing test assertions** across 4 test files that access `TicketOutput` attributes directly.
2. **Breaks `isinstance(output, TicketOutput)` checks** in existing tests.
3. **Existing test `test_no_reply_or_draft_field_on_output`** was intentionally written to assert no draft fields leak onto `TicketOutput`.
4. **Does not actually resolve the constraint.** The `ticket.py` schema file remains unmodified either way.

The `generate_draft()` approach gives downstream callers (Streamlit, API, future pipeline integration) a clean function to compose without any breaking change.

**NOT YET: Automatic pipeline integration**

A future change can add an optional `generate_draft=True` parameter to `intake_risk_pipeline()` or create a new `full_pipeline()` entrypoint that composes both stages. This requires no schema changes and no breaking return-type changes.

### Graceful Degradation

The `generate_draft()` function follows the same try/except pattern as the existing pipeline stages:

| Scenario | Behavior |
|----------|----------|
| Provider raises exception | Safe fallback message returned |
| Validator raises exception | Safe fallback message returned |
| Empty evidence list | No-evidence fallback message (returned by FakeDraftProvider internally) |
| High risk assessment | Draft generated with `must_human_review=True` |
| Normal flow | Complete draft with citations and `unsupported_claims=[]` |


## Migration Plan (Batch 1)

1. Create `src/ticketpilot/drafting/` directory structure
2. Implement `schemas.py` with `Citation`, `DraftReply`, `DraftGenerationTrace`
3. Implement `provider.py` with `AbstractDraftProvider` + `FakeDraftProvider`
4. Implement `citation_validator.py` with `CitationValidator`
5. Update `src/ticketpilot/drafting/__init__.py` with clean exports
6. Write unit tests: schema validation, provider behavior, validator rules
7. Run quality gate (existing tests unchanged, coverage threshold maintained)

**Batch 2**: Implement `generate.py` with `generate_draft()` function, integration tests, documentation.

**Rollback**: Delete `src/ticketpilot/drafting/`. No other files are modified.

## Open Questions

- Exact regex patterns for the claim-pattern scan need tuning against real Chinese support ticket replies
- Whether the fake provider's template should be configurable (e.g., via constructor parameter) for different business domains
- Whether `confidence` should be computed from average evidence score or some other heuristic (e.g., minimum score, weighted by rank)
- How to handle the case where evidence candidates exist but none have sufficient score for confident use
- Whether the citation `[N]` format is the right UX or if Chinese-friendly markers like `【N】` would be better
