# add-mvp-evidence-pack — Demo Scenarios Specification

## Baseline (Before Change)

- No structured demo scenario documentation exists.
- Demo is currently ad-hoc: paste a ticket into Streamlit console, click "处理工单", observe result.
- The README has a "Quick Start" section for running the console but no guided demo walkthroughs.

## ADDED Requirements

### Requirement: Demo Scenario 1 — 退款投诉 (Refund + Complaint)
The system SHALL provide a documented demo scenario for a refund request combined with complaint/legal risk.

#### Scenario: Demo scenario document exists
- WHEN checking `docs/demo/` or `docs/portfolio/`
- THEN a document exists describing the refund+complaint scenario

#### Scenario: Scenario includes 3–5 sample tickets
- WHEN the scenario document is read
- THEN it contains 3–5 sample ticket texts in Chinese covering variations:
  - Refund request with damaged product + complaint about customer service
  - Refund request mentioning lawyer/legal action (legal risk trigger)
  - Refund request with compensation demand (compensation risk trigger)

#### Scenario: Scenario documents expected pipeline behavior
- WHEN the scenario document is read
- THEN it describes the expected flow through each pipeline stage:
  - Intake: normalized text, extracted order number
  - Classification: complaint or refund intent
  - Risk: COMPLAINT_RISK, COMPENSATION_RISK, possibly LEGAL_RISK; HIGH or MEDIUM severity
  - must_human_review: true
  - Retrieval: expected evidence doc types (CASE, POLICY, FAQ)
  - Draft: citation-grounded draft with high-risk warning
  - Human review: required before any action

### Requirement: Demo Scenario 2 — 隐私/账号异常 (Account Issue + Privacy Risk)
The system SHALL provide a documented demo scenario for account security issues combined with privacy/data leak risk.

#### Scenario: Demo scenario document exists
- WHEN checking `docs/demo/` or `docs/portfolio/`
- THEN a document exists describing the account+privacy scenario

#### Scenario: Scenario includes 3–5 sample tickets
- WHEN the scenario document is read
- THEN it contains 3–5 sample ticket texts in Chinese covering:
  - Account hacked/stolen, cannot log in
  - Phone number leaked, receiving spam calls (privacy risk)
  - ID number / real name exposed through platform (privacy + account_security risk)

#### Scenario: Scenario documents expected pipeline behavior
- WHEN the scenario document is read
- THEN it describes the expected flow:
  - Classification: account_issue
  - Risk: ACCOUNT_SECURITY_RISK, PRIVACY_RISK; MEDIUM severity
  - must_human_review: true
  - Retrieval: FAQ (account recovery steps) + POLICY (privacy policy, data protection)
  - Draft: draft reply with privacy warning and account recovery instructions
  - Human review: required

### Requirement: Demo Scenario 3 — 发票/支付争议 (Billing/Invoice + Payment Dispute)
The system SHALL provide a documented demo scenario for billing, invoicing, and payment amount disputes.

#### Scenario: Demo scenario document exists
- WHEN checking `docs/demo/` or `docs/portfolio/`
- THEN a document exists describing the billing/payment scenario

#### Scenario: Scenario includes 3–5 sample tickets
- WHEN the scenario document is read
- THEN it contains 3–5 sample ticket texts in Chinese covering:
  - Invoice not issued after purchase (billing issue)
  - Payment deducted but order not confirmed (payment dispute)
  - Charged wrong amount / overcharge dispute (amount dispute)

#### Scenario: Scenario documents expected pipeline behavior
- WHEN the scenario document is read
- THEN it describes the expected flow:
  - Classification: logistics, refund, or consulting depending on specifics
  - Risk: POLICY_CONFLICT or INSUFFICIENT_EVIDENCE; LOW to MEDIUM severity
  - must_human_review: false for simple cases, true if escalation language present
  - Retrieval: FAQ (payment FAQ) + POLICY (billing policy) + CASE (similar dispute resolutions)
  - Draft: evidence-grounded draft explaining policy or proposing resolution
  - Human review: required only if risk flags triggered

### Requirement: All Demo Scenarios Include Limitations Context
All three demo scenario documents SHALL include a clear limitations section.

#### Scenario: Limitations documented per scenario
- WHEN each demo scenario document is read
- THEN it includes a limitations section stating:
  - Data is synthetic, not real enterprise customer data
  - Retrieval uses deterministic fake embeddings (no semantic understanding)
  - Drafts are template-generated (no LLM), not production-quality replies
  - System is a local demo/portfolio project, not a production deployment

## MODIFIED Requirements

(None — demo scenarios are entirely new.)

## DELETED Requirements

(None)

## Data Sources

- Demo scenario tickets are synthetic Chinese customer service messages.
- Scenarios are designed to demonstrate specific pipeline behaviors (risk detection, evidence retrieval, must_human_review trigger).
- No real customer data, real tickets, or production transcripts are used.

## Validation

- All 3 demo scenario documents exist in `docs/demo/` or `docs/portfolio/`
- Each document contains sample tickets, expected pipeline flow, and limitations
- OpenSpec validate --all passes
- Quality gate passes
