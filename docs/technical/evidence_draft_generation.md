# Evidence Draft Generation

## Overview

The draft generation stage is an **optional workflow** that produces evidence-grounded Chinese customer service reply drafts from the pipeline's `TicketOutput`. Every factual claim in the draft is linked to supporting evidence via numbered citations. The stage uses a deterministic, template-based provider (no LLM) and a regex-based citation validator.

**Source module:** `src/ticketpilot/drafting/`

## `generate_draft(ticket_output)`

**Signature:** `generate_draft(ticket_output: TicketOutput) -> DraftReply`

**Source:** `src/ticketpilot/drafting/generate.py`

This is the primary entrypoint for draft generation. It is a standalone composition function that:

1. Instantiates `FakeDraftProvider` (the only MVP provider)
2. Instantiates `CitationValidator`
3. Wires them together: provider generates draft text with citations, validator checks the output
4. Wraps any exceptions in a safe fallback draft (never crashes)
5. Returns a `DraftReply` without modifying the input `TicketOutput`

### Behavior Matrix

| Scenario | `draft_text` | `confidence` | `citations` | `must_human_review` | `fallback_reason` |
|----------|-------------|-------------|-------------|---------------------|-------------------|
| Evidence available | Template reply with `[N]` citations | 0.7-0.9 | Populated | False (unless high-risk) | None |
| No evidence | Safe fallback: "根据现有信息，无法确认具体政策条款" | 0.0 | [] | True | `"no_evidence"` |
| High risk | Template reply with citations, capped confidence | 0.5 (capped) | Populated | True | None |
| Unsupported claims | Template reply + CitationValidator flags | 0.0-0.9 | Populated | True | None |
| Exception | Safe fallback: generation error message | 0.0 | [] | True | `"generation_error"` |

## `run_pipeline_with_draft(raw_ticket)`

**Signature:** `run_pipeline_with_draft(raw_ticket: RawTicket) -> DraftedTicketResult`

**Source:** `src/ticketpilot/drafting/pipeline.py`

An optional entrypoint that composes the 4-stage pipeline with draft generation:

```python
ticket_output = intake_risk_pipeline(raw_ticket)
draft_reply = generate_draft(ticket_output)
return DraftedTicketResult(ticket_output=ticket_output, draft_reply=draft_reply)
```

Returns a `DraftedTicketResult` wrapper containing both fields. Does not modify `intake_risk_pipeline()` or `TicketOutput`.

## FakeDraftProvider

**Source:** `src/ticketpilot/drafting/provider.py`

### AbstractDraftProvider Interface

```python
class AbstractDraftProvider(ABC):
    @abstractmethod
    def generate(self, ticket_output: TicketOutput) -> DraftReply: ...
```

### FakeDraftProvider Implementation

The only MVP implementation. It is:

- **Deterministic**: Same input always produces the same output
- **Template-based**: Uses a fixed Chinese template: opening ("您好...") + evidence body with `[N]` citation markers + closing
- **Stateless**: No internal state, thread-safe
- **Zero external dependencies**: No LLM, no network, no API keys, no database queries
- **Sub-millisecond latency**: No external calls

**Provider strategy:** The `AbstractDraftProvider` interface is designed so a real LLM provider can replace `FakeDraftProvider` without changing any other code. The interface is the same; only the implementation changes.

## CitationValidator

**Source:** `src/ticketpilot/drafting/citation_validator.py`

The `CitationValidator` is a **deterministic regex-based guardrail**, not a full NLP claim verifier.

### Checks Performed

1. **Citation existence**: Every `[N]` marker in `draft_text` must have a corresponding `Citation` in the provided list. If a marker references an out-of-range index, it is flagged.

2. **Claim-coverage scan**: Sentences containing Chinese claim keywords without a citation marker are flagged:
   - Claim keywords: "根据", "按照", "可以", "承诺", "退款", "赔偿"
   - If a sentence has a keyword and no `[N]` marker, it is flagged as potentially unsupported

3. **Cross-reference against evidence** (optional): If `evidence_candidates` is provided, each `Citation.chunk_id` is verified against the set of valid chunk IDs from retrieval.

### Method: `validate()`

```python
def validate(
    self,
    text: str,
    citations: list[Citation],
    evidence_candidates: list[EvidenceCandidate] | None = None,
) -> tuple[bool, list[str]]:
```

Returns `(passed, issues)` where `passed=True` when no issues found.

### Known Limitations

- Regex patterns are imprecise — false positives and false negatives expected with real Chinese text
- The claim keyword list ("根据", "按照", "可以", "承诺", "退款", "赔偿") is not exhaustive
- Sentence splitting (`[。！？!?]`) may not handle all Chinese punctuation correctly
- Future replacement: LLM-based semantic claim verifier (same interface, different implementation)

## DraftReply

**Source:** `src/ticketpilot/drafting/schemas.py`

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | `str` | Associated ticket ID |
| `draft_text` | `str` | Generated draft reply text |
| `citations` | `list[Citation]` | Citations referenced in the draft |
| `evidence_used` | `list[Citation]` | Evidence actually used in generating the draft |
| `unsupported_claims` | `list[str]` | Claims flagged as unsupported by CitationValidator |
| `missing_information` | `list[str]` | Information gaps noted during generation |
| `confidence` | `float` | Generation confidence (0.0-1.0) |
| `must_human_review` | `bool` | True when high-risk, unsupported claims, or no evidence |
| `fallback_reason` | `str \| None` | Reason for fallback: "no_evidence", "generation_error", or None |
| `generation_trace` | `dict \| None` | Optional generation metadata |

## No-Evidence Fallback

When `TicketOutput` has empty `evidence_candidates`, the draft generation produces a safe fallback:

**Template:** "您好，感谢您的耐心等待。根据现有信息，无法确认具体政策条款，建议转人工处理。我们会尽快为您核实并安排专人跟进。"

This message:
- Makes no deterministic policy promises
- Cannot be factually wrong (it says "cannot confirm specific policy terms")
- Routes to human handling
- Has `confidence=0.0` and `citations=[]`

## Unsupported Claim Guard

When `CitationValidator` detects issues after draft generation:

1. The issues are populated in `DraftReply.unsupported_claims`
2. `DraftReply.must_human_review` is set to `True`
3. The `DraftedTicketResult` propagates this to the human review console, which displays the flagged claims

## High-Risk Review Preservation

When the pipeline's `RiskAssessment` has `must_human_review=True`:

1. The draft is generated normally (same template process)
2. `DraftReply.must_human_review` is set to `True`
3. `DraftReply.confidence` is capped at 0.5 (never reports high confidence for risky tickets)
4. The `DraftedTicketResult` preserves both the risk flags and the draft

## No Auto-Send

The draft generation stage **never dispatches replies**. It produces a `DraftReply` (optional) that must go through human review before any hypothetical downstream use. There is no send functionality anywhere in the codebase.

## Deferred Items

- Real LLM provider (OpenAI, Claude, etc.) — `AbstractDraftProvider` interface ready
- LLM-based semantic claim verifier (replaces regex `CitationValidator`)
- Configurable/locale-aware fallback messages
- Persistent `DraftGenerationTrace` storage in database
- Multi-turn or conversational draft generation
- Evaluation pipeline with golden-answer test sets for draft quality
