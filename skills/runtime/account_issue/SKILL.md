# Account Issue

## When to Use
Customer reports account access or security problems.
Common scenarios: account locked, forgotten password, suspicious login, account hacked, email changed without consent.

## Required Tools
- normalize_ticket
- classify_ticket
- assess_risk
- retrieve_evidence
- generate_draft

## Business Constraints
- No auto-send. Security-related account issues require human verification.
- Do not share account credentials in any reply.
- Verify identity before performing account changes.
- Do not confirm account details (email, phone, address) in draft.

## Evidence Requirements
- Retrieve account recovery / security procedures from knowledge base.
- Retrieve login history if available.
- Check for ACCOUNT_SECURITY_RISK flag.

## Human Review Rules
- must_human_review: true when ACCOUNT_SECURITY_RISK or PRIVACY_RISK flagged.
- must_human_review: true when draft confidence < 0.6.
- must_human_review: true for any password reset or account recovery request.

## Bad Cases
- Releasing account details without identity verification.
- Treating account takeover as a simple login issue.
- Promising specific resolution time for security investigations.
