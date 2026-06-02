# TicketPilot

AI Customer Service Copilot for cross-border e-commerce.

## Features

- **Hybrid Retrieval**: BM25 + Vector search with RRF fusion
- **Real Embeddings**: DashScope text-embedding-v3 (1024 dimensions)
- **DraftAgent**: Multi-step reasoning with self-reflection
- **Guardrails**: PII detection, hallucination detection, confidence routing
- **Observability**: Full tracing and evaluation framework
- **Streaming**: SSE real-time response streaming

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+ with pgvector
- DashScope API key
- DeepSeek API key

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/ticketpilot.git
cd ticketpilot

# Install dependencies
pip install uv
uv sync

# Set up environment
cp .env.example .env.local
# Edit .env.local with your API keys

# Start database
docker compose up -d db

# Initialize database
uv run python -c "from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks; seed_knowledge_chunks(clear_existing=True)"

# Rebuild embeddings
uv run python scripts/rebuild_embeddings_curl.py

# Start API
uv run uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build and start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Harness                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Lifecycle │ │ Testing  │ │ Monitor  │ │ Deploy   │  │
│  │ Manager  │ │ & Eval   │ │ & Observe│ │ & CI/CD  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Guardrails & Safety                  │  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              DraftAgent                           │  │
│  │  Retrieve → Evaluate → Generate → Reflect → Verify│  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Hybrid Retrieval                     │  │
│  │  BM25 + Vector (DashScope) + RRF + Re-ranking    │  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              PostgreSQL + pgvector                │  │
│  │              340 knowledge chunks                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Evaluation

```bash
# Run adversarial evaluation
uv run python /tmp/adversarial_eval_v2.py

# Run agent evaluation framework
uv run python scripts/run_agent_eval.py

# View traces
ls logs/traces/
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/chat` - Chat with AI copilot
- `POST /api/chat/stream` - Streaming chat (SSE)
- `POST /api/tickets` - Process ticket
- `POST /api/reviews` - Submit review decision
- `GET /api/evaluation` - Get evaluation metrics

## Project Structure

```
ticketpilot/
├── src/ticketpilot/
│   ├── api/              # FastAPI endpoints
│   ├── classification/   # Intent classification
│   ├── drafting/         # DraftAgent
│   ├── evaluation/       # Evaluation framework
│   ├── guardrails/       # Safety checks
│   ├── retrieval/        # Hybrid retrieval
│   ├── schema/           # Data models
│   └── tracing/          # Observability
├── data/
│   ├── eval/             # Evaluation datasets
│   └── knowledge/        # Knowledge base
├── scripts/              # Utility scripts
├── reports/              # Evaluation reports
├── logs/                 # Traces and logs
├── Dockerfile            # Docker image
├── docker-compose.yml    # Full stack deployment
└── pyproject.toml        # Python dependencies
```

## Evaluation Results

| Metric | Score |
|--------|-------|
| Intent Accuracy | 100% |
| Evidence Hit Rate | 100% |
| Overall Score | 1.000 |

## License

MIT
