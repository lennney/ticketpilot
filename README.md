# TicketPilot

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot.

It is not a generic chatbot or a simple document QA demo. The system is designed around a customer support workflow:

Ticket input
→ normalization
→ intent classification
→ risk assessment
→ rule gate
→ FAQ / Policy / Case retrieval
→ hybrid recall
→ RRF fusion
→ rerank
→ evidence-grounded draft reply
→ human review
→ finalization
→ trace and evaluation

## MVP Stack

- FastAPI
- LangGraph
- PostgreSQL + pgvector
- PostgreSQL full-text search / BM25-compatible keyword search
- RRF
- Pydantic
- Streamlit review UI
- Docker Compose
- uv

## Development

This project uses spec-driven and AI-assisted development.

Development rules:
- Use OpenSpec for non-trivial changes.
- Use project-level Claude agents and skills for planning, implementation, review, and evaluation.
- Do not commit secrets.
- Update docs/changelog.md after meaningful changes.
