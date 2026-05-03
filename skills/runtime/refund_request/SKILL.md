# Refund Request

## When to Use
Customer requests a refund for a product or service.
Common scenarios: dissatisfied with purchase, product not as described, duplicate charge, service cancellation.

## Required Tools
- normalize_ticket
- classify_ticket
- assess_risk
- retrieve_evidence
- generate_draft

## Business Constraints
- No auto-send. All draft replies require human review before sending.
- Verify customer identity before processing any refund.
- Refund amounts above threshold must be escalated.
- Do not promise specific refund timelines.

## Evidence Requirements
- Retrieve refund policy documents from knowledge base.
- Retrieve order / transaction records if available.
- Check for prior refund requests on same order (fraud indicator).

## Human Review Rules
- must_human_review: true when risk assessment flags COMPENSATION_RISK or LEGAL_RISK.
- must_human_review: true when unsupported claims exceed 2.
- Any refund exceeding policy limits must be escalated.
- First-time vs repeat customer may affect decision.

## Bad Cases
- Scam / fraud attempts claiming false charges.
- Requests for refund outside policy window.
- Requests involving both refund and complaint — route to complaint_escalation instead.
