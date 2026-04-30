## Context

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot. The first vertical slice builds the ticket intake and risk triage foundation without RAG retrieval or Streamlit UI.

**Current state**: Empty project with FastAPI, LangGraph, PostgreSQL, pgvector, Pydantic infrastructure ready.

**Constraints**:
- No RAG yet
- No Streamlit review UI yet
- No real LLM API calls yet
- Use deterministic rules or fake provider output
- Use Pydantic schemas for all critical outputs
- Include tests or smoke tests
- Update docs/changelog.md after implementation

## Goals / Non-Goals

**Goals:**
- End-to-end pipeline: raw Chinese ticket -> normalized ticket -> intent classification -> risk assessment -> structured JSON
- Deterministic 8-class intent classification using keyword/regex rules
- Rule-based 8-flag risk assessment
- Pydantic schemas for all critical outputs
- Smoke tests validating the pipeline
- Well-documented code structure for future extension

**Non-Goals:**
- No RAG retrieval (handled in later vertical slice)
- No Streamlit review UI (handled in later vertical slice)
- No real LLM API integration (fake provider for now)
- No database persistence yet
- No evaluation harness (placeholder only)

## Decisions

### 1. Package structure: `src/ticketpilot/`

**Decision**: Create `src/ticketpilot/` with sub-modules: `intake/`, `classification/`, `risk/`, `schema/`, `pipeline.py`

**Rationale**: Clear separation of concerns matching the workflow stages. Each stage (intake, classification, risk) is independently testable.

**Alternatives considered**:
- Single `ticketpilot.py` module: Too monolithic, harder to test individual stages
- Flat structure with prefixes (e.g., `intake_*.py`): Less explicit about groupings

### 2. Intent classification: keyword/regex rule-based approach

**Decision**: Use deterministic keyword matching with Chinese synonyms and regex patterns for the 8 classes:
- refund, return_exchange, account_issue, technical_issue, product_consulting, logistics, complaint, other

**Rationale**: First vertical slice requires deterministic behavior for testing. Real LLM-based classification comes later.

**Alternatives considered**:
- Random/fake classification: Not deterministic, can't write meaningful tests
- Real LLM: Out of scope per constraints

### 3. Fake LLM provider

**Decision**: Create a `providers/fake.py` that returns predetermined outputs for each intent class.

**Rationale**: Allows pipeline testing without real API calls. Structured so real provider can replace it later.

### 4. Risk assessment: rule-based with 8 flags

**Decision**: Each risk flag triggered by specific keyword patterns:
- `complaint_risk`: 投诉, 差评, 曝光, 媒体
- `compensation_risk`: 赔偿, 补偿, 3倍, 5倍, 惩罚性
- `legal_risk`: 律师, 法院, 起诉, 法律
- `privacy_risk`: 泄露, 隐私, 个人信息
- `account_security_risk`: 盗号, 盗刷, 异常登录, 冻结
- `policy_conflict`: 违反, 违规, 政策, 条款
- `insufficient_evidence`: (no order number, no product info, vague description)
- `low_confidence`: (classification confidence < threshold)

**Rationale**: Deterministic rules enable consistent testing and clear risk triage behavior.

### 5. Pydantic schemas

**Decision**: Schemas defined in `schema/` module:
- `RawTicket`: input (original Chinese text, metadata)
- `NormalizedTicket`: after intake processing
- `IntentClass`: enum of 8 classes
- `ClassificationResult`: intent class + confidence
- `RiskFlag`: enum of 8 risk flags
- `RiskAssessment`: set of triggered flags + severity
- `TicketOutput`: final structured output combining all above

**Rationale**: Pydantic enforces validation, provides type hints, and serializes to JSON cleanly.

## Risks / Trade-offs

[Risk] Rule-based classification is brittle for nuanced tickets
→ **Mitigation**: Document limitation; real LLM classification replaces this in v2

[Risk] No real LLM means classification quality cannot improve through prompts
→ **Mitigation**: Fake provider interface matches real provider interface; swap is trivial

[Risk] Rule-based risk flags may miss edge cases
→ **Mitigation**: Clear escalation path (low_confidence flag) for human review

## Migration Plan

1. Create `src/ticketpilot/` structure with schema definitions
2. Implement `intake/` module for normalization
3. Implement `classification/` module with keyword rules
4. Implement `risk/` module with rule-based flags
5. Implement `pipeline.py` chaining all stages
6. Add smoke tests in `tests/unit/test_intake_risk_triage.py`
7. Run quality gate and update docs/changelog.md

**Rollback**: Delete `src/ticketpilot/` and revert changelog.

## Open Questions

- Exact keyword sets for classification and risk flags need validation with real ticket data
- Confidence score handling in fake provider (fixed values vs. heuristics)
- Severity calculation algorithm for risk assessment (sum vs. weighted vs. threshold)
