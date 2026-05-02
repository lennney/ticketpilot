# TicketPilot Architecture

> **Status note (2026-05-02):** This document describes the aspirational end-to-end workflow.
> Stages up to "human review for high-risk" are implemented. "Rerank", "finalization",
> and "trace write-back" are not yet implemented. See `docs/technical_decisions.md` and
> `docs/phase_status.md` for the current implementation state.

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot.

The system must preserve the following workflow:

Ticket input
→ normalization
→ intent classification
→ risk assessment
→ rule gate
→ FAQ / Policy / Case layered retrieval
→ hybrid recall
→ RRF fusion
→ rerank
→ evidence-grounded draft reply
→ human review for high-risk or low-confidence cases
→ finalization
→ trace and evaluation write-back

The first MVP should not become a generic chatbot or a simple document QA system.
