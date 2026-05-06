# Design: Evidence-Grounded LLM Draft Generation (Phase 11)

## Architecture Overview

```
                               Input
                    ┌──────────────────────────┐
                    │  NormalizedTicket         │
                    │  ClassificationResult     │
                    │  RiskAssessment           │
                    │  EvidenceCandidate[]      │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Prompt Builder          │
                    │   (evidence → system +    │
                    │    user prompt)           │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   LLM Provider            │
                    │   (abstract interface)    │
                    │   ├─ FakeLLMProvider      │
                    │   └─ OpenAICompatible     │
                    │      (future sub-phase)   │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   DraftReply (structured) │
                    │   + citations             │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Claim Guard             │
                    │   ├─ Citation coverage    │
                    │   ├─ Forbidden promises   │
                    │   ├─ Evidence match       │
                    │   └─ Risk-aware checks    │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Human Review Handoff    │
                    │   ├─ must_human_review?   │
                    │   ├─ escalation_reason   │
                    │   └─ guard_results        │
                    └──────────────────────────┘
```

## Component Design

### 1. LLM Provider Abstraction

**Interface** (`src/ticketpilot/drafting/llm_provider.py`):

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt. Returns raw text (not structured draft)."""
        ...

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier for trace logging."""
        ...
```

**FakeLLMProvider** (deterministic, for tests):
- Returns a predefined template response based on evidence content
- Does not call any external API
- Used as default provider (same pattern as FakeEmbeddingProvider)
- Enables all draft generation pipelines to run in CI without API keys

**OpenAICompatibleProvider** (future sub-phase):
- Configuration via environment variables only: `LLM_PROVIDER=openai_compatible`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
- `.env.local` pattern (same as embedding provider)
- API keys never committed to repository

### 2. Evidence-Grounded Prompt Builder

**Module**: `src/ticketpilot/drafting/prompt_builder.py`

**Input**:
- `normalized_text: str` — the customer's original message
- `classification: ClassificationResult` — intent label
- `risk_assessment: RiskAssessment` — flags, severity, must_human_review
- `evidence_candidates: list[EvidenceCandidate]` — retrieved evidence (pool, not just top-k)

**Output**: `str` — a structured prompt that constrains the LLM to:
- Use only the provided evidence for factual claims
- Cite each evidence source by its chunk_id
- Never make policy, refund, compensation, legal, or account-security promises
- Flag any request that cannot be answered from evidence as "insufficient evidence"
- Respect risk flags: high-risk tickets must recommend human review

**System prompt template**:
```
You are a customer service drafting assistant. Your task is to generate a
professional draft reply based ONLY on the evidence provided below.

Rules:
1. Every factual or policy statement MUST cite its evidence source [chunk_id].
2. Do NOT promise refund amounts, compensation, legal actions, or account changes
   unless explicitly stated in the evidence.
3. If the evidence does not cover the customer's request, state "根据现有信息，
   无法确认具体政策条款，建议转人工处理。" and mark as insufficient evidence.
4. Do NOT generate draft replies that:
   - Admit legal liability
   - Promise specific compensation amounts
   - Authorize account changes
   - Guarantee resolution timelines
5. High-risk tickets (legal, compensation, privacy, account_security) must include
   a statement that the case has been escalated for human review.
6. Format your response as a structured draft with:
   - A greeting
   - Specific answers citing evidence
   - Clear next steps
   - A closing

Evidence:
{formatted_evidence}

Customer message: {normalized_text}
Intent: {intent}
Risk flags: {risk_flags}
Severity: {severity}
```

### 3. Structured Draft Output

**Schema** (extends existing `DraftReply` in `src/ticketpilot/drafting/schemas.py`):

```python
class DraftReply(BaseModel):
    # Existing fields
    ticket_id: str
    draft_text: str
    citations: list[Citation]
    evidence_used: list[Citation]
    unsupported_claims: list[str]
    missing_information: list[str]
    confidence: float  # 0.0-1.0
    must_human_review: bool
    fallback_reason: str | None
    generation_trace: dict | None

    # New fields for Phase 11
    provider_id: str  # which provider generated this draft
    guard_results: GuardResult | None  # post-generation guard output
    escalation_reason: str | None  # why human review was triggered
```

**GuardResult** (new schema):
```python
class GuardResult(BaseModel):
    citation_coverage: float  # proportion of claims with citations
    has_uncited_claims: bool
    has_forbidden_promise: bool
    forbidden_promise_details: list[str]
    evidence_sufficiency: str  # "sufficient", "partial", "insufficient"
    risk_flags_respected: bool  # all risk flags properly handled
    guard_passed: bool  # overall guard result
```

### 4. Claim Guard Design

**Module**: `src/ticketpilot/drafting/claim_guard.py`

**Checks applied in order**:

1. **Citation existence**: Every `[chunk_id]` reference in `draft_text` must have a corresponding entry in `citations` that references a real `EvidenceCandidate`.

2. **Evidence coverage**: For each factual/policy claim in the draft, verify there is at least one cited evidence candidate whose content supports the claim. Uses rule-based keyword matching (deterministic, same pattern as current CitationValidator).

3. **Forbidden promise detection**: Scan draft for patterns that promise:
   - Specific refund amounts ("退款XX元", "赔偿XX元")
   - Legal action guarantees ("我们一定会起诉", "法律后果")
   - Account changes ("已为您修改密码", "账号已冻结")
   - Resolution timelines ("X天内解决", "保证X天")
   - Admission of liability ("承认责任", "我方过错")

4. **Risk-aware check**: If `RiskAssessment` flags contain `LEGAL_RISK`, `COMPENSATION_RISK`, `PRIVACY_RISK`, or `ACCOUNT_SECURITY_RISK`, verify the draft acknowledges escalation to human review.

**Output**: `GuardResult` with pass/fail per check. If any check fails, `guard_passed=False` and `must_human_review=True`.

### 5. Pipeline Integration

**Module**: `src/ticketpilot/drafting/generate.py` (modified)

Updated `generate_draft()` flow:
1. Receive `TicketOutput` with `evidence_candidates`
2. Build prompt via `PromptBuilder.build(ticket_output)`
3. Call `LLMProvider.generate(prompt)` → raw text
4. Parse raw text into structured `DraftReply` with `citations`
5. Run `CitationValidator.validate()` (existing)
6. Run `ClaimGuard.check()` (new)
7. Set `must_human_review` if: risk assessment requires it, claim guard fails, citation validator fails, or insufficient evidence
8. Return `DraftReply` with full `guard_results` and trace

### 6. Human Review Console Updates

**Module**: `src/ticketpilot/review/console.py` (modified)

Display additions:
- Show `guard_results` in the review panel (pass/fail per check)
- Show `provider_id` in trace information
- Show `escalation_reason` if triggered
- Existing approve/edit/escalate/reject actions unchanged

**ReviewDecision** schema extension:
```python
class ReviewDecision(BaseModel):
    # Existing fields unchanged
    ...
    # New fields
    guard_results: GuardResult | None
    provider_id: str | None
    escalation_reason: str | None
```

### 7. Draft Evaluation Metrics

**Module**: `src/ticketpilot/evaluation/draft_metrics.py` (new)

**Metrics**:
| Metric | Definition |
|---|---|
| Citation precision | Proportion of citations that reference valid evidence |
| Evidence coverage | Proportion of evidence claims that have supporting citations |
| Unsupported claim rate | Proportion of drafts with at least one unsupported claim |
| Safe fallback rate | Proportion of no-evidence cases that correctly produce fallback draft |
| Human review trigger correctness | Proportion of cases where `must_human_review` matches expected |
| Forbidden promise rate | Proportion of drafts with detected forbidden promises |
| Guard pass rate | Proportion of drafts where `guard_passed=True` |

**Golden expectations extension**: Add `expected_citation_count`, `expected_has_unsupported_claims`, `expected_guard_passed` fields to `GoldenExpectation` (or create `DraftGoldenExpectation`).

### 8. Trace

All generation runs record:
- `provider_id` — which provider generated the draft
- `evidence_ids_used` — which evidence chunk_ids were cited
- `guard_results` — full guard output
- `draft_evaluation_results` — if offline evaluation is run

## Data Flow

```
RawTicket
  │
  ▼
intake_risk_pipeline()
  │
  ▼
TicketOutput (with evidence_candidates)
  │
  ▼
PromptBuilder.build(ticket_output)
  │
  ▼
LLMProvider.generate(prompt)
  │
  ▼
DraftReply parser (raw text → structured)
  │
  ▼
CitationValidator.validate() ──→ issues → must_human_review=True
  │
  ▼
ClaimGuard.check() ──→ guard_results → must_human_review=True if failed
  │
  ▼
Human review handoff (if must_human_review)
  │
  ▼
DraftedTicketResult
```

## Provider Configuration

```python
# src/ticketpilot/drafting/provider_config.py (new)

class DraftProviderConfig:
    provider_type: str  # "fake" or "openai_compatible"
    model: str | None
    base_url: str | None
    api_key: str | None

def load_draft_provider_config() -> DraftProviderConfig:
    """Load from environment variables. Same pattern as embedding provider config."""
    ...

def create_draft_provider(config: DraftProviderConfig) -> LLMProvider:
    """Factory function. Default: FakeLLMProvider."""
    ...
```

## Safety Design

| Layer | What it prevents | How |
|---|---|---|
| Prompt constraint | LLM inventing policy | System prompt restricts to evidence only |
| Citation validation | Uncited claims | Post-generation check |
| Claim guard | Forbidden promises | Pattern matching + evidence cross-ref |
| Risk-aware check | Ignored risk flags | Verify escalation for high-risk |
| Human review | Auto-send bypass | must_human_review architectural gate |
| Architecture invariant | Auto-send | No send channel exists in pipeline |

## File Map

### New Files
- `src/ticketpilot/drafting/llm_provider.py` — LLM provider interface + FakeLLMProvider
- `src/ticketpilot/drafting/prompt_builder.py` — evidence-grounded prompt builder
- `src/ticketpilot/drafting/claim_guard.py` — claim guard validators
- `src/ticketpilot/drafting/provider_config.py` — provider configuration
- `src/ticketpilot/evaluation/draft_metrics.py` — draft evaluation metrics

### Modified Files
- `src/ticketpilot/drafting/schemas.py` — extend DraftReply with guard_results, provider_id
- `src/ticketpilot/drafting/generate.py` — integrate LLM provider flow
- `src/ticketpilot/review/console.py` — display guard results
- `src/ticketpilot/review/schemas.py` — extend ReviewDecision
- `src/ticketpilot/evaluation/metrics.py` — integrate draft metrics (optional)

### Test Files (new)
- `tests/unit/test_llm_provider.py`
- `tests/unit/test_prompt_builder.py`
- `tests/unit/test_claim_guard.py`
- `tests/unit/test_draft_metrics.py`
- `tests/unit/test_drafting_generate.py` (extend existing)
- `tests/integration/test_draft_generation.py` (new integration)
