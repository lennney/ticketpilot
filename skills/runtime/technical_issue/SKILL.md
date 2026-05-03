# Technical Issue

## When to Use
Customer reports a technical problem with a product or service.
Common scenarios: system bug, error message, feature not working, crash, performance issue, setup failure.

## Required Tools
- normalize_ticket
- classify_ticket
- assess_risk
- retrieve_evidence
- generate_draft

## Business Constraints
- No auto-send. Technical issue drafts require human review.
- Do not promise specific fix timelines.
- Do not suggest workarounds without verifying they are safe.
- Collect reproduction steps when possible.

## Evidence Requirements
- Retrieve relevant technical documentation / FAQs from knowledge base.
- Retrieve known issue records if available.
- Check for similar resolved issues.

## Human Review Rules
- must_human_review: true when draft confidence < 0.6.
- must_human_review: true when unsupported claims > 2.
- must_human_review: true for security-related technical issues.
- Escalate to engineering team if no documented fix exists.

## Bad Cases
- Suggesting unsafe workarounds (registry edits, disabling security).
- Over-promising fix timelines.
- Treating a training/usage question as a technical bug.
