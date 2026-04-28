## Why

TicketPilot needs a functional vertical slice to demonstrate end-to-end ticket processing from raw Chinese input to structured JSON output. This establishes the core workflow foundation: normalization, 8-class intent classification, and rule-based risk triage. Building this first vertical slice validates the data flow and provides concrete Pydantic schemas for all critical outputs before adding RAG retrieval or review UI.

## What Changes

- Add ticket intake pipeline: raw Chinese text -> normalized ticket
- Add 8-class intent classification with deterministic rule-based approach
- Add rule-based risk assessment with 8 risk flags
- Add structured JSON output via Pydantic schemas
- Add smoke tests for the intake-risk-triage pipeline
- Update docs/changelog.md

## Capabilities

### New Capabilities

- `ticket-intake`: Raw Chinese ticket normalization (language detection, text cleaning, entity extraction placeholder)
- `intent-classification`: 8-class issue type classification using keyword/regex rules (refund, return_exchange, account_issue, technical_issue, product_consulting, logistics, complaint, other)
- `risk-assessment`: Rule-based risk triage with 8 flags (complaint_risk, compensation_risk, legal_risk, privacy_risk, account_security_risk, policy_conflict, insufficient_evidence, low_confidence)
- `ticket-schema`: Pydantic schemas for normalized ticket, classification result, risk assessment, and final structured output
- `intake-risk-pipeline`: End-to-end pipeline combining intake -> classification -> risk assessment -> JSON output

### Modified Capabilities

- (none - first vertical slice)

## Impact

- New module: `src/ticketpilot/` with intake, classification, risk, and schema components
- New test files: `tests/unit/test_intake_risk_triage.py` with smoke tests
- Updated: `docs/changelog.md`
- No external API calls (uses deterministic rules or fake provider output)
- No RAG retrieval yet
- No Streamlit UI yet
