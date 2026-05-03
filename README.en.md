# TicketPilot

> Chinese customer support ticket triage and evidence-grounded reply copilot — local demo / portfolio project
>
> **This is not a production customer-service system. It does not auto-send replies.**

---

## 1. What is TicketPilot?

TicketPilot is a local portfolio/demo project for Chinese customer-service ticket triage and evidence-grounded draft replies. It takes unstructured Chinese support messages through normalization, intent classification, risk assessment, layered knowledge retrieval, evidence-grounded draft generation, and human review.

**Core positioning:**
- Local demo / portfolio project
- Architecture-first: clean module boundaries, data contracts via Pydantic, testability
- Deterministic: seed data and template-based generation, no real LLM or embedding service required
- Safety constraint: no auto-send is an architectural invariant

## 2. Why it is not a normal RAG demo

TicketPilot is not a chatbot or simple document QA. Key differences from common RAG demos:

| Dimension | Typical RAG Demo | TicketPilot |
|-----------|-----------------|-------------|
| Input | Free-text Q&A | Structured ticket processing pipeline |
| Classification | None | 8 intent types + 8 risk flags |
| Knowledge base | Single document store | Layered: FAQ / Policy / Case |
| Retrieval | Semantic search | Keyword + vector + RRF fusion |
| Generation | LLM direct output | Template-based, evidence-cited drafts |
| Review | None | Human review console with audit trail |
| Evaluation | Subjective | Deterministic offline evaluation pipeline |

**Key limitations:**
- Uses **fake embeddings** (384-dim deterministic hash vectors) — cosine similarity has no semantic meaning, only verifies pipeline connectivity
- Evaluation based on **10 seed tickets**, not representative of real-world performance
- System is **local demo / portfolio-ready**, not for production use

## 3. Core workflow

```
RawTicket (original message)
    │
    ▼
Normalization + entity extraction (order numbers, customer ID)
    │
    ▼
Intent classification (8 types: refund, exchange, account, complaint, logistics, technical, consulting, other)
    │
    ▼
Risk assessment (8 flags + severity: LOW / MEDIUM / HIGH)
    │
    ▼
Layered knowledge retrieval (keyword FTS + vector HNSW + RRF fusion)
    │
    ├─ EvidenceCandidate
    ├─ RetrievalTrace
    │
    ▼
Draft generation (template-driven, evidence-cited, zero LLM)
    │
    ├─ DraftReply + Citation
    ├─ fallback_reason (when no evidence available)
    │
    ▼
Streamlit human review console
    │
    ├─ Actions: Approve / Edit / Escalate / Reject
    ├─ Output: ReviewDecision JSONL (audit trail)
    │
    ▼
Offline evaluation pipeline
    ├─ CSV prediction mode: load sample predictions → compute metrics
    ├─ Pipeline prediction mode: run full pipeline → compute metrics
    └─ Output: JSON + Markdown evaluation reports
```

## 4. Feature overview

| Module | Capability | Coverage |
|--------|-----------|----------|
| **Ticket Intake** | Text normalization, order number extraction | Unit tests |
| **Intent Classification** | 8 ticket types (refund, exchange, account, complaint, logistics, technical, consulting, other) | Unit tests |
| **Risk Assessment** | 8 risk flags (complaint, compensation, legal, account security, privacy, policy conflict, low confidence, insufficient evidence) + severity grading | Unit tests |
| **Layered Retrieval** | Keyword FTS + pgvector HNSW + RRF fusion; supports FAQ / Policy / Case doc types | Unit + integration tests |
| **Draft Generation** | Template-driven (zero LLM, zero network); evidence-cited; no-evidence fallback; high-risk forced human review | Unit tests |
| **Human Review** | Streamlit console; approve/edit/escalate/reject; ReviewDecision JSONL audit trail | Unit + integration tests |
| **Evaluation Pipeline** | CSV prediction mode; pipeline prediction mode; 7 metrics (intent accuracy, severity accuracy, risk flag F1, evidence recall, etc.); JSON + Markdown reports | Unit + integration tests (85) |
| **Quality Gate** | Ruff + unit tests + integration tests (skip=fail) + coverage≥70% + OpenSpec validation | Fully automated |

**Safety constraints:**
- **No auto-send**: The system does not connect to any send channel. ReviewDecision writes only to local JSONL.
- **No LLM dependency**: Draft generation uses deterministic templates, no LLM API calls.
- **No real embeddings**: Vector search uses fake embeddings, no semantic retrieval quality.

## 5. Architecture summary

```
Layered module architecture (bottom-up):

┌─────────────────────────────────────────────┐
│                  Entry / CLI                  │
│  scripts/run_eval.py, streamlit console      │
├─────────────────────────────────────────────┤
│            Application layer (Pydantic)       │
│  RawTicket → NormalizedTicket → TicketOutput │
│  → DraftReply → ReviewDecision               │
├─────────┬─────────┬──────────┬───────────────┤
│ Intake  │ Class.  │ Risk     │ Retrieval     │
│ intake/ │ class-  │ risk/    │ retrieval/    │
│         │ ifica-  │          │               │
│         │ tion/   │          │               │
├─────────┴─────────┴──────────┴───────────────┤
│            Draft Generation                   │
│  drafting/ (templates + citation validator)   │
├─────────────────────────────────────────────┤
│            Review Console                     │
│  review/ (Streamlit + JSONL persistence)      │
├─────────────────────────────────────────────┤
│            Evaluation Pipeline                │
│  evaluation/ (loaders + metrics + reporting)  │
├─────────────────────────────────────────────┤
│            Storage Layer                      │
│  PostgreSQL + pgvector + full-text search     │
│  Docker Compose (local development)          │
└─────────────────────────────────────────────┘

Key design decisions:
- Fake provider boundary: all external dependencies (embeddings, LLM)
  have fake implementations for offline verification
- OpenSpec change management: every feature follows proposal →
  design → spec → tasks → acceptance → archive
- Quality gate: automated verification, no skipped integration tests allowed
```

## 6. Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16 + pgvector (required only for integration tests)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (optional, for starting PostgreSQL)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/ticketpilot.git
cd ticketpilot

# Install dependencies (including dev dependencies)
uv sync
```

### Run tests

```bash
# Run full quality gate (Ruff + unit tests + integration tests + coverage + OpenSpec)
./scripts/run_quality_gate.sh

# Or step by step:
uv run ruff check .
uv run python -m pytest tests/unit -q
uv run python -m pytest tests/integration/ -v --strict-markers
```

### Run offline evaluation

```bash
# CSV prediction mode (load sample predictions from file)
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --predictions data/eval/sample_predictions.csv \
  --out-json reports/eval/evaluation_report.json \
  --out-md reports/eval/evaluation_report.md

# Pipeline prediction mode (run full pipeline to generate predictions)
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --prediction-mode pipeline \
  --out-json reports/eval/current_pipeline_report.json \
  --out-md reports/eval/current_pipeline_report.md
```

### Run the human review console

> Requires PostgreSQL (see below).

```bash
# Start PostgreSQL (requires Docker)
docker compose up -d

# Run database migrations
alembic upgrade head

# Seed knowledge base
uv run python scripts/ingest_knowledge.py

# Start Streamlit console
uv run streamlit run src/ticketpilot/review/console.py
```

Open http://localhost:8501 in your browser.

### Run the full pipeline

```bash
# Requires PostgreSQL running
uv run python -c "
from ticketpilot.pipeline import run_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(original_text='我要退款，订单号：123456', submitted_at=datetime.utcnow())
output = run_pipeline(ticket)
print(f'Intent: {output.classification.intent.value}')
print(f'Risk flags: {[f.value for f in output.risk_assessment.flags]}')
print(f'Severity: {output.risk_assessment.severity.value}')
"
```

---

> Full documentation map available in [docs/README.md](docs/README.md) (added in a later batch).
> 中文版请见 [README.md](README.md)。
