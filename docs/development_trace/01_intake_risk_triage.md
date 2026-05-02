# Stage 1A: Ticket Intake + Risk Triage

## Stage Goal

Build the first vertical slice of the TicketPilot pipeline: raw Chinese ticket input through intake normalization, intent classification, and risk assessment, producing a structured `TicketOutput`. This establishes the pipeline foundation without retrieval, drafting, or UI.

## Business Problem Addressed

Customer support teams receive unstructured Chinese-language tickets. Before any automated assistance can help, the system must:
- Normalize raw text (clean formatting, extract entities like order numbers and product info)
- Classify the intent of the ticket (refund, return, complaint, account issue, etc.)
- Assess risk level (compensation risk, legal risk, privacy risk, security risk, etc.)
- Produce structured, machine-readable output for downstream stages

Without this stage, tickets remain unstructured text that no automated system can process.

## Key Design Decisions

### 1. Package structure: `src/ticketpilot/` with sub-modules
- **Decision**: Separate modules for `intake/`, `classification/`, `risk/`, `schema/`, and `pipeline.py`.
- **Rationale**: Clear separation of concerns matching workflow stages. Each stage is independently testable.
- **Alternatives considered**: Single monolithic module (rejected — harder to test), flat file structure (rejected — less explicit about groupings).

### 2. Rule-based intent classification (8 classes)
- **Decision**: Deterministic keyword matching with Chinese synonyms and regex patterns for 8 intent classes (REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER).
- **Rationale**: First vertical slice requires deterministic behavior for testing. Real LLM-based classification comes later.
- **Alternatives**: Random/fake classification (not deterministic — can't write meaningful tests), real LLM (out of scope per constraints).

### 3. Rule-based risk assessment (8 flags)
- **Decision**: Each risk flag triggered by specific Chinese keyword patterns (e.g., "赔偿" for COMPENSATION_RISK, "律师" for LEGAL_RISK).
- **Rationale**: Deterministic rules enable consistent testing and clear risk triage behavior.
- **Key design**: `must_human_review` is set to `True` when substantive risk flags (not meta flags like LOW_CONFIDENCE or INSUFFICIENT_EVIDENCE) are triggered.

### 4. Pydantic schemas for all critical outputs
- **Decision**: Schemas defined in `schema/` module with RawTicket, NormalizedTicket, ClassificationResult, RiskAssessment, TicketOutput.
- **Rationale**: Pydantic enforces validation, provides type hints, and serializes to JSON cleanly.

### 5. Graceful degradation in pipeline stages
- **Decision**: Each stage (intake, classification, risk) is wrapped in try/except. If a stage fails, fallback values are returned and the pipeline continues.
- **Rationale**: A ticket processing pipeline should never crash. Even with partial results, the system produces actionable output.

## Implementation Scope

- Created `src/ticketpilot/schema/ticket.py` with all Pydantic models: RawTicket, NormalizedTicket, IntentClass (8 values), ClassificationResult, RiskFlag (8 values), RiskAssessment, TicketOutput
- Created `src/ticketpilot/intake/normalizer.py` with text cleaning and Chinese-specific normalization
- Created `src/ticketpilot/intake/entity_extractor.py` with regex patterns for order numbers, product info, amounts
- Created `src/ticketpilot/intake/pipeline.py` combining normalizer + entity extractor into `intake()` function
- Created `src/ticketpilot/classification/rules.py` with Chinese keyword dictionaries for 8 intent classes
- Created `src/ticketpilot/classification/classifier.py` with rule-based `classify()` returning ClassificationResult
- Created `src/ticketpilot/risk/rules.py` with keyword patterns for 8 risk flags
- Created `src/ticketpilot/risk/assessor.py` with `assess()` returning RiskAssessment and severity calculation
- Created `src/ticketpilot/pipeline.py` combining intake -> classification -> risk -> TicketOutput
- Unit tests in `tests/unit/test_intake_risk_triage.py` validating the full pipeline with Chinese tickets

## Forbidden Scope

- No RAG retrieval (handled in Stage 1B)
- No Streamlit review UI (handled in Stage 1D)
- No real LLM API integration (fake provider only)
- No database persistence (in-memory pipeline output only)
- No evaluation harness (placeholder only)

## Tests and Quality Gate Result

- Unit tests passed (count not tracked at this stage; later counts show ~150 unit tests prior to pipeline integration)
- Quality gate ran successfully (initial `|| true` gate — see Stage 04 for actual validation)
- Acceptance report created and archived as legacy

## Major Risks

| Risk | Handling |
|------|----------|
| Rule-based classification is brittle for nuanced tickets | Documented limitation; real LLM classification planned for v2 |
| No real LLM means classification quality cannot improve through prompts | Fake provider interface matches real provider interface; swap is trivial |
| Rule-based risk flags may miss edge cases | Clear escalation path (LOW_CONFIDENCE flag) triggers human review |

## Deferred Items

- Real LLM-based classification provider
- Database persistence for pipeline results
- Evaluation harness and golden test sets
- Retrieval, drafting, and review UI (all separate stages)

## Related Commits (chronological)

| Hash | Date | Message |
|------|------|---------|
| `ecd1de6` | 2026-04-29 | spec: add ticket intake risk triage change |
| (implementation commits on feature branch, merged into master before `9738f37`) | | |
| `55ed46e` | 2026-05-01 | chore: archive intake risk triage OpenSpec change |

## Reusable Patterns

1. **Pipeline stage pattern** — Each stage is a self-contained function with try/except graceful degradation. New stages can be added by inserting a function call in `pipeline.py` without modifying existing stages.
2. **Pydantic schema as pipeline boundary** — Each stage produces a typed Pydantic model consumed by the next stage. This enforces contracts and makes integration testing straightforward.
3. **Chinese keyword rules for intent/risk** — The keyword dictionary pattern with Chinese synonyms is reusable for any Chinese-language classification or risk assessment system.
4. **Severity calculation algorithm** — Risk severity computed from flag count with configurable thresholds. Simple but effective for MVP triage.
