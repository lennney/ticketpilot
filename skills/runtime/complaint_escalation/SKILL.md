# Complaint Escalation

## When to Use
Customer complaint, legal threat, or regulatory risk.
Common scenarios: filing complaint, legal action threat, compensation demand, privacy violation report, discrimination claim.

## Required Tools
- normalize_ticket
- classify_ticket
- assess_risk
- retrieve_evidence
- generate_draft

## Business Constraints
- No auto-send. All complaint tickets require human review.
- Do not admit liability.
- Do not promise specific compensation amounts.
- Escalate to legal team for LEGAL_RISK flags.
- Preserve all evidence for audit trail.

## Evidence Requirements
- Retrieve relevant policies (complaint handling, privacy, terms of service).
- Retrieve customer interaction history and order records.
- Retrieve prior complaint resolutions if available.

## Human Review Rules
- must_human_review: true for ALL complaint tickets.
- must_human_review: true when LEGAL_RISK or PRIVACY_RISK flagged.
- must_human_review: true when draft confidence < 0.6.
- Legal team notification required for LEGAL_RISK.

## Bad Cases
- Treating a complaint as a simple refund request — always escalate first.
- Over-promising resolution timelines.
- Dismissing legal threats without documentation.
