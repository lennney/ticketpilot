# Evidence-Grounded Generation Skill

## Purpose

Build an evidence-grounded draft generation system that produces replies with numbered citations linked to retrieved evidence, validates citations deterministically, guards against unsupported claims, provides safe fallbacks for no-evidence scenarios, and enforces high-risk review routing. The system must never fabricate policy promises, never auto-send, and always flag outputs that require human review.

## When to Use

- Designing a draft or reply generation stage for a RAG pipeline
- Implementing citation validation as a deterministic guardrail
- Defining safe fallback behavior for no-evidence, high-risk, and error scenarios
- Integrating draft generation as an optional workflow that preserves the core pipeline contract
- Reviewing generation output for unsupported claims, citation integrity, and risk-appropriate handling
- Do NOT use this skill as a replacement for real LLM-based generation

## Required Inputs

- Pipeline output type (e.g., TicketOutput) with evidence candidates
- Evidence data model (chunk_id, doc_id, doc_type, content, score, rank)
- Draft reply schema definition (DraftReply or equivalent)
- Citation data model (Citation with chunk_id, doc_id, doc_type, evidence_excerpt)
- Risk assessment schema (must_human_review, risk flags, severity)

## Allowed Scope

- Creating a draft generation provider with abstract interface and deterministic (template/fake) implementation
- Implementing citation validation with regex-based checks (citation existence, claim-coverage scan)
- Defining safe fallback behavior for no-evidence, high-risk, and error scenarios
- Creating an optional workflow entrypoint that composes pipeline + draft generation without modifying the pipeline contract
- Documenting deferred items: real LLM provider, evaluation pipeline, persistent traces

## Forbidden Scope

- Do NOT claim real LLM generation capability if using only template/fake provider
- Do NOT auto-send or dispatch generated drafts anywhere
- Do NOT modify the core pipeline return type to accommodate draft generation
- Do NOT claim evaluation pipeline for draft quality (no golden-answer test sets, no automated quality metrics)
- Do NOT claim the CitationValidator is a full NLP claim verifier (it is regex-based with known limitations)
- Do NOT reduce confidence thresholds or bypass must_human_review for high-risk or no-evidence scenarios
- Do NOT fabricate citations or evidence in generated drafts

## Step-by-Step Procedure

1. **Define the draft output schema**
   - Create a DraftReply model with: draft_text, citations (list of Citation), evidence_used, unsupported_claims, missing_information, confidence, must_human_review, fallback_reason, generation_trace
   - Every field should have a clear purpose and valid range

2. **Create an abstract provider interface**
   - AbstractDraftProvider with a single `generate(ticket_output) -> DraftReply` method
   - This allows multiple provider implementations (template-based, LLM-based) to be swapped without changing the pipeline

3. **Implement a deterministic (fake/template) provider**
   - Construct replies from evidence candidates using a fixed template
   - Template structure: opening + evidence body with [N] citation markers + closing
   - Must be deterministic (same input always produces same output)
   - Must have zero external dependencies (no LLM, no network, no API keys)

4. **Implement citation validation**
   - Citation existence check: every [N] marker in draft_text must have a corresponding Citation
   - Claim-coverage scan: Chinese claim keywords (based on, according to, can, promise, refund, compensation) without [N] markers in the same sentence are flagged
   - Cross-reference against evidence (optional): verify each Citation.chunk_id exists in the evidence set
   - Known limitation: regex patterns are imprecise; false positives and negatives expected with real Chinese text

5. **Implement safe fallback behavior**

   | Scenario | Fallback |
   |----------|----------|
   | No evidence | Safe message: "cannot confirm specific policy terms, recommend manual processing." Confidence=0.0, citations=[], must_human_review=True |
   | High risk | Draft generated normally, but confidence capped at 0.5, must_human_review=True |
   | Exception during generation | Safe fallback draft returned (never crashes), fallback_reason="generation_error", must_human_review=True |

6. **Create an optional workflow entrypoint**
   - `run_pipeline_with_draft(raw_ticket)` that composes: existing pipeline -> generate_draft
   - Returns a wrapper type (e.g., DraftedTicketResult) combining pipeline output + draft reply
   - Does NOT modify the core pipeline's return type

7. **Wire the generation stage to human review**
   - DraftReply.must_human_review propagates to the human review console
   - Unsupported claims from CitationValidator populate DraftReply.unsupported_claims
   - The review console displays flagged claims, fallback warnings, and risk indicators alongside the draft

8. **Document deferred items**
   - Real LLM provider integration
   - LLM-based semantic claim verifier (replaces regex CitationValidator)
   - Evaluation pipeline for draft quality
   - Persistent DraftGenerationTrace storage

## Acceptance Checklist

- [ ] DraftReply schema defined with all required fields
- [ ] Abstract provider interface defined
- [ ] Deterministic provider implementation (non-LLM) working
- [ ] CitationValidator performs citation existence check
- [ ] CitationValidator performs claim-coverage scan
- [ ] No-evidence fallback produces safe message with no policy promises
- [ ] High-risk fallback caps confidence and sets must_human_review=True
- [ ] Exception handling produces safe fallback (never crashes)
- [ ] Optional entrypoint composes pipeline + draft without modifying pipeline contract
- [ ] No auto-send capability exists anywhere in the generation code
- [ ] Deferred items documented: real LLM provider, evaluation pipeline, persistent traces
- [ ] FakeDraftProvider labeled as MVP-only, not a real LLM

## Common Failure Modes

- **Claiming the system "generates natural language" with a template provider**: Template-based replies are not natural language generation. Describe them honestly as "template-based deterministic replies."
- **The CitationValidator reports no issues, but the draft is factually wrong**: The validator checks citation format and claim coverage, not factual accuracy. A draft can pass validation and still be wrong.
- **No-evidence fallback makes a policy promise**: If the fallback text says something like "we will process your refund," it creates a commitment that cannot be fulfilled. The fallback should say "cannot confirm specific policy terms."
- **Confidence not capped for high-risk tickets**: A high-risk ticket should never have high confidence, even if the draft generation succeeds. Cap confidence explicitly.
- **Unhandled exception crashes generation**: Wrap the entire generation in a try/except that returns a safe fallback draft. Generation should never crash the pipeline.
- **Auto-send capability accidentally added**: If the review console has a "send" button or an API endpoint dispatches replies, the no-auto-send constraint is violated. Audit all interfaces for send functionality.

## Reusable Claude Code Prompt Template

```
I need to implement evidence-grounded draft generation. Walk through:

1. **DraftReply schema** — Define with: draft_text, citations, evidence_used, unsupported_claims, confidence, must_human_review, fallback_reason

2. **AbstractDraftProvider interface** — Single `generate(ticket_output)` method. Enables provider swapping.

3. **Deterministic provider (template-based)** — Template: opening + [N]-cited evidence body + closing. Deterministic, no LLM, no network, no API keys.

4. **CitationValidator** — Two checks:
   - Citation existence: every [N] needs a matching Citation
   - Claim-coverage: Chinese claim keywords without [N] are flagged
   - Note: regex-based, not NLP. Accept known limitations.

5. **Safe fallbacks** (three scenarios):
   - No evidence: safe text, conf=0.0, citations=[], must_human_review=True
   - High risk: cap conf at 0.5, must_human_review=True
   - Exception: safe fallback, fallback_reason="generation_error", never crash

6. **Optional entrypoint** — `run_pipeline_with_draft(raw_ticket)` composes pipeline + draft. Does NOT modify pipeline return type.

7. **Document deferred** — Real LLM, evaluation pipeline, persistent traces.

Critical constraints:
- No auto-send
- No claiming real LLM if using template provider
- No modifying pipeline return type
- No fabricating citations
- CitationValidator is regex-based, not NLP — document limitations
```

## TicketPilot Example

TicketPilot's evidence-grounded draft generation (Stage 1C) implements all of the above:

**DraftReply schema**: 10 fields including draft_text, citations, confidence, must_human_review, fallback_reason, unsupported_claims.

**AbstractDraftProvider**: Interface with `generate(ticket_output) -> DraftReply`. Currently only FakeDraftProvider (template-based, deterministic). Real LLM provider can replace it without pipeline changes.

**FakeDraftProvider**: Constructs Chinese replies from evidence using a template: "您好，感谢您的来信。关于您的问题..." with [N] citation markers and "如有疑问，欢迎随时联系我们。" closing. Zero external dependencies. Deterministic.

**CitationValidator**: Regex-based checks for citation existence (every [N] has matching Citation) and claim-coverage (Chinese keywords 根据, 按照, 可以, 承诺, 退款, 赔偿 without citation markers flagged). Known limitation: false positives/negatives expected with real Chinese text.

**Safe fallbacks**:
- No evidence: "您好，感谢您的耐心等待。根据现有信息，无法确认具体政策条款，建议转人工处理。"
- High risk: confidence capped at 0.5, must_human_review=True
- Exception: safe fallback with fallback_reason="generation_error", never crashes

**Optional entrypoint**: `run_pipeline_with_draft(raw_ticket)` composes the 4-stage pipeline with generate_draft. Returns DraftedTicketResult (TicketOutput + DraftReply). Pipeline return type unchanged.

**No auto-send**: Verified by integration tests. No send functionality exists anywhere in the generation code.

**Deferred**: Real LLM provider (interface ready, not implemented), evaluation pipeline (no golden-answer test sets for draft quality), persistent DraftGenerationTrace storage.
