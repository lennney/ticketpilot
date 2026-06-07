# TicketPilot

AI Customer Service Copilot for cross-border e-commerce — **deterministic, no-LLM-in-pipeline, full-chain traceability**.

## What Makes TicketPilot Different

| Feature | Typical Approach | TicketPilot |
|---------|-----------------|-------------|
| Confidence scoring | Binary (confident / not) | 4-dimensional weighted: retrieval + classification + citation + evidence density |
| Response routing | All-auto or all-human | 4-tier degradation: AUTO_SEND → CAUTIOUS → HUMAN_REVIEW → ESCALATION |
| Hallucination guard | None or simple keyword filter | 8-category forbidden promise detection (refund amounts, legal threats, etc.) |
| Retrieval | Simple vector search | Keyword FTS + Vector HNSW → RRF fusion with per-ranker contribution tracing |
| Traceability | None | Full chain: answer → citation → chunk → document (ClaimProvenance + RetrievalTrace) |
| Agent architecture | Single agent | Multi-agent orchestrator with intent-based routing to specialized agents |
| Pipeline determinism | LLM-dependent | Rule-driven, zero LLM calls in pipeline |
| Calibration | Static thresholds | Feedback loop with isotonic regression calibration + reliability diagrams |
| Experimentation | Manual A/B | Built-in A/B experiment framework with comparison reports |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TicketPilot Pipeline                      │
│                                                               │
│  RawTicket ──→ Intake ──→ Classify ──→ Risk ──→ Retrieve     │
│                 │           │          │         │             │
│                 ▼           ▼          ▼         ▼             │
│            Normalize    Intent     RiskFlag   Evidence         │
│            Extract      Class      Severity   (FTS+Vector     │
│            Entities     Confidence            → RRF Fusion)    │
│                                                  │             │
│                          ┌───────────────────────┘             │
│                          ▼                                     │
│                    Multi-Agent Orchestrator                     │
│                    ┌─────┼─────┬─────┬─────┐                  │
│                    ▼     ▼     ▼     ▼     ▼                  │
│                 Refund Complaint Logis Tech Default             │
│                    │                                            │
│                    ▼                                            │
│              Generate Draft                                     │
│              (prompt template per agent)                        │
│                    │                                            │
│              ┌─────┴─────┐                                     │
│              ▼           ▼                                     │
│         Claim Guard   Citation Validator                       │
│         (forbidden    (Luhn check,                             │
│          promises)     unsupported claims)                     │
│              │           │                                     │
│              ▼           ▼                                     │
│         Confidence Scorer (4 dimensions)                        │
│              │                                                 │
│              ▼                                                 │
│         Degradation Router                                     │
│         ┌────┬────┬────┬────┐                                 │
│         ▼    ▼    ▼    ▼    ▼                                 │
│       HIGH  MED  LOW  CRIT  → Human Review Console             │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Feedback Loop: accept/reject → CalibrationCurve →       │ │
│  │  IsotonicCalibrator → ThresholdAdvisor                   │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Modules

### Confidence & Routing
- **ConfidenceScorer** — 4-dimensional scoring (retrieval 35%, classification 25%, citation 25%, evidence density 15%)
- **DegradationRouter** — 4-tier routing based on confidence level
- **Claim Guard** — Forbidden promise detection, citation coverage, risk acknowledgment
- **Citation Validator** — Luhn bank card check, unsupported claim detection

### Multi-Agent System
- **Orchestrator** — Intent-based routing to specialized agents
- **5 Specialists** — RefundAgent, ComplaintAgent, LogisticsAgent, TechnicalAgent, DefaultAgent
- **Per-agent prompt templates** — Each specialist uses domain-specific prompts

### Retrieval
- **Hybrid search** — PostgreSQL FTS + pgvector HNSW → RRF fusion
- **RetrievalTrace** — Full explainability: keyword rank, vector rank, RRF contribution per result
- **Context truncation** — Token-budget-aware truncation for retrieval results

### Feedback & Calibration
- **FeedbackCollector** — Records (confidence, action, was_correct) from human reviews
- **CalibrationCurve** — 5-bucket reliability analysis with ECE
- **IsotonicCalibrator** — Pure Python PAV algorithm for confidence calibration
- **ThresholdAdvisor** — Suggests optimal thresholds based on calibration data
- **ReliabilityDiagram** — ASCII art visualization for terminal

### Evaluation
- **NLI Scorer** — Sentence decomposition, synonym expansion, negation detection
- **Retrieval Metrics** — Precision@K, Recall@K, MRR, NDCG
- **A/B Experiment Framework** — Same tickets, two configs, comparison report

### Observability
- **AgentTrace** — Append-only event stream per run
- **ClaimProvenance** — Answer → citation → chunk → document traceability
- **Retrieval Visualization** — Streamlit table + contribution chart

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+ with pgvector

### Installation

```bash
git clone https://github.com/yourusername/ticketpilot.git
cd ticketpilot

pip install uv
uv sync

cp .env.example .env.local
# Edit .env.local with your API keys (optional — pipeline works without LLM keys)

docker compose up -d db

uv run python -c "from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks; seed_knowledge_chunks(clear_existing=True)"

uv run uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
# Unit tests (no database required)
TICKETPILOT_SKIP_DB_TESTS=1 uv run pytest tests/ --ignore=tests/integration -q

# Full quality gate
bash scripts/run_quality_gate.sh
```

### Review Console

```bash
uv run streamlit run src/ticketpilot/chat/app.py --server.port 8501
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/chat` | POST | Chat with AI copilot |
| `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/api/tickets` | POST | Process ticket |
| `/api/reviews` | POST | Submit review decision |
| `/api/evaluation` | GET | Get evaluation metrics |

## Project Structure

```
src/ticketpilot/
├── api/                # FastAPI endpoints + SSE streaming
├── classification/     # Intent classifier (deterministic)
├── config/             # Central confidence thresholds
├── confidence/         # 4-dimensional confidence scorer
├── degradation/        # 4-tier response router
├── drafting/           # DraftAgent, prompt builder, claim guard, citation validator
├── evaluation/         # RAGAS-style metrics, NLI scorer, retrieval metrics, A/B experiments
├── experiment/         # A/B experiment framework
├── feedback/           # Feedback collector, calibrator, threshold advisor
├── guardrails/         # PII detection, security scanning
├── intake/             # Ticket normalization, entity extraction
├── multi_agent/        # Orchestrator + 5 specialized agents
├── prompts/            # Per-agent prompt templates
├── retrieval/          # Hybrid retrieval (FTS + HNSW → RRF)
├── review/             # Streamlit review console, retrieval visualization
├── risk/               # Risk assessor + rules
├── schema/             # Pydantic data models
├── tracing/            # Provenance tracking
└── triggers/           # CLI + webhook entry points
```

## Test Coverage

```bash
1,498 tests passing
├── Unit tests (no DB): 1,498
├── Integration tests (DB required): separate
└── Coverage: >70% enforced
```

## License

MIT
