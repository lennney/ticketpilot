# TicketPilot Project Guide

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot.

## Core MVP Goal

Build a demonstrable AI workflow system for Chinese e-commerce after-sales tickets.

The system must support:
- text ticket input
- 8-class issue classification
- rule-based priority and risk gate
- FAQ / Policy / Case layered knowledge sources
- hybrid retrieval
- RRF fusion
- evidence-grounded reply draft
- high-risk human review
- trace
- evaluation
- README and demo cases

## Tech Stack

- Backend: FastAPI
- Workflow: LangGraph
- Database: PostgreSQL
- Vector search: pgvector
- Keyword search: PostgreSQL full-text search or BM25-compatible minimal implementation
- Fusion: RRF
- Structured output: Pydantic
- Review UI: Streamlit
- Dependency management: uv
- Development environment: WSL Ubuntu
- Deployment: Docker Compose

## Development Rules

1. Define the current goal before implementation.
2. Update docs/changelog.md after each meaningful change.
3. Every module must have clear inputs and outputs.
4. Critical outputs must use Pydantic schemas.
5. Do not pass untyped raw JSON freely.
6. Keep prompts centralized with prompt_version.
7. Never commit real API keys or secrets.
8. Do not introduce unnecessary frameworks.
9. Add tests or smoke tests for each completed module.
10. Every feature must serve the ticket triage and evidence-grounded reply workflow.

## First MVP Domain

Chinese e-commerce after-sales, especially refund, return/exchange, complaint, logistics, account issue, technical issue, product consulting, and other.

## Out of Scope for First Version

- Multi-agent role-play inside the product
- Training large models
- Complex knowledge graph
- Voice customer support
- Full CRM system
- Large-scale crawling
- Complex distributed microservices
