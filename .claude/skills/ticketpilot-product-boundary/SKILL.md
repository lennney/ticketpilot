---
name: ticketpilot-product-boundary
description: Use when deciding project scope, prioritization, or whether a feature belongs in the TicketPilot MVP.
---

# TicketPilot Product Boundary

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot.

Must preserve:
- ticket normalization
- intent classification
- risk gate
- FAQ / Policy / Case layered retrieval
- hybrid retrieval
- evidence-grounded draft reply
- human review
- trace
- evaluation

First version should not include:
- multi-agent role-play inside the product
- model training
- complex knowledge graph
- voice support
- multi-channel CRM integration
- large-scale crawling
- distributed microservices

Priority principle:
If a feature does not improve workflow completeness, risk control, evidence traceability, human review closure, evaluation, or interview explainability, do not prioritize it.
