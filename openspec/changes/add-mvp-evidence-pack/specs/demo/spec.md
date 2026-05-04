# add-mvp-evidence-pack — Demo Scenarios Specification

## Baseline (Before Change)

- No structured demo scenario documentation exists.
- Demo is currently ad-hoc: paste a ticket into Streamlit console, click "处理工单", observe result.
- The README has a "Quick Start" section for running the console but no guided demo walkthroughs.

## ADDED Requirements

### Requirement: Demo Scenario 1 — 退款投诉 (Refund + Complaint)
The system SHALL provide a documented demo scenario for a refund request combined with complaint/legal risk.

#### Scenario: Demo scenario document exists
- WHEN `docs/demo/scenario_refund_complaint.md` is checked
- THEN it exists

#### Scenario: Scenario includes 3 sample tickets
- WHEN the scenario document is read
- THEN it contains 3 sample ticket texts in Chinese covering:
  - Refund due not arrived + complaint + compensation demand (Ticket A1)
  - Product defect + lawyer/legal action threat (Ticket A2)
  - Duplicate payment + 12315 complaint threat (Ticket A3)

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
- WHEN `docs/demo/scenario_privacy_account.md` is checked
- THEN it exists

#### Scenario: Scenario includes 3 sample tickets
- WHEN the scenario document is read
- THEN it contains 3 sample ticket texts in Chinese covering:
  - Account abnormal login + personal info leaked (Ticket B1)
  - Account stolen + unauthorized orders (Ticket B2)
  - Personal info leak leading to spam calls (Ticket B3)

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
- WHEN `docs/demo/scenario_invoice_payment.md` is checked
- THEN it exists

#### Scenario: Scenario includes 3 sample tickets
- WHEN the scenario document is read
- THEN it contains 3 sample ticket texts in Chinese covering:
  - Payment deducted but order not confirmed + duplicate charge + invoice issue (Ticket C1)
  - Invoice type correction request (Ticket C2)
  - Amount overcharge dispute + complaint threat (Ticket C3)

#### Scenario: Scenario documents expected pipeline behavior
- WHEN the scenario document is read
- THEN it describes the expected flow:
  - Classification: logistics, refund, or consulting depending on specifics
  - Risk: POLICY_CONFLICT or INSUFFICIENT_EVIDENCE; LOW to MEDIUM severity
  - must_human_review: false for no-risk simple cases, true when risk flags present (policy_conflict / complaint_risk)
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

### Requirement: Demo Overview Document
The system SHALL provide a demo overview document at `docs/demo/phase7_demo_scenarios.md` comparing all three scenarios.

#### Scenario: Overview document exists
- WHEN `docs/demo/phase7_demo_scenarios.md` is checked
- THEN it exists
- AND it contains a comparison table, capability coverage matrix, interview talking points, and screenshot opportunities

### Requirement: Demo Docs Are Docs-Only
All demo scenario documents SHALL be purely documentation — no source code, test files, data, or configuration modified.

#### Scenario: No code or data files modified
- WHEN checking git status after creating demo docs
- THEN only `docs/demo/*.md`, `docs/changelog.md`, and `openspec/changes/add-mvp-evidence-pack/**` are modified
- AND no `src/**`, `tests/**`, `data/**`, `reports/**`, `README*.md`, `pyproject.toml`, or `uv.lock` files are modified

## Validation

- All 3 demo scenario documents exist in `docs/demo/`
- Each document contains 3 sample tickets, expected pipeline flow, risk behavior, evidence behavior, draft boundary, and limitations
- Overview document exists at `docs/demo/phase7_demo_scenarios.md`
- OpenSpec validate --all passes
- Quality gate passes (Level 0: docs-only — scoped validation sufficient)
