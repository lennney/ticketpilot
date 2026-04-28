---
name: ticket-risk-policy
description: Use when implementing or reviewing risk assessment, human review routing, complaint handling, compensation handling, legal risk, privacy risk, or account security risk.
---

# Ticket Risk Policy

Risk flags:
- complaint_risk
- compensation_risk
- legal_risk
- privacy_risk
- account_security_risk
- policy_conflict
- insufficient_evidence
- low_confidence

Hard rules:
1. Complaint, compensation, legal, privacy, and account security cases must enter human review.
2. Insufficient evidence must not produce a confident final reply.
3. Low classification confidence must enter human review.
4. Policy conflict must enter human review.
5. The system is a customer support assistant, not a fully automated support agent.
