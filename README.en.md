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
- Deterministic: seed data and template-based generation, no real LLM or embedding service required by default (real embedding provider opt-in via environment variable)
- Safety constraint: no auto-send is an architectural invariant

**Project phases:** Phase 7 (MVP Data & Evaluation) → Phase 8 (Hybrid Retrieval Upgrade) → Phase 9 (Evaluation-Driven Knowledge Optimization) → Phase 10 (Ranking Diagnosis & Granular Evaluation) → Phase 11 (Evidence-Grounded LLM Draft, complete)

## 2. Why it is not a normal RAG demo

TicketPilot is not a chatbot or simple document QA. Key differences from common RAG demos:

| Dimension | Typical RAG Demo | TicketPilot |
|-----------|-----------------|-------------|
| Input | Free-text Q&A | Structured ticket processing pipeline |
| Classification | None | 8 intent types + 8 risk flags |
| Knowledge base | Single document store | Layered: FAQ / Policy / Case |
| Retrieval | Semantic search | Keyword + vector + RRF fusion |
| Generation | LLM direct output | Template-based / evidence-constrained LLM drafts |
| Review | None | Human review console with audit trail |
| Evaluation | Subjective | Deterministic offline evaluation pipeline |

**Key limitations:**
- Uses **fake embeddings by default** (384-dim deterministic hash vectors) — cosine similarity has no semantic meaning, only verifies pipeline connectivity. Real embeddings (DashScope text-embedding-v4) opt-in via environment variable
- Evaluation based on **101 synthetic tickets** and **106 knowledge records** (FAQ=41, Policy=34, Case=31), not representative of real-world performance
- System is **local demo / portfolio-ready**, not for production use
- Current intent accuracy (~53%) and severity accuracy (~54%) reflect deterministic behavior of rule-based components, not production-level metrics

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
    ├─ RetrievalTrace (full audit trail)
    │
    ▼
Draft generation (template-driven / LLM evidence-constrained, citation-grounded)
    │
    ├─ DraftReply + Citation
    ├─ ClaimGuard (statement validation + forbidden promise detection)
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
| **Real Embedding Comparison** | Fake 384-d vs Real 1024-d offline comparison: Top-1 31.7%→42.6%, MRR 0.4114→0.4913 | Full eval coverage |
| **Eval-Driven Optimization** | 8-category failure taxonomy → 24 knowledge gaps → 11 targeted additions → Provider Identity Gate | Full eval coverage |
| **Granular Retrieval Eval** | Doc-ID evidence evaluation: Recall@10=91.9%, 78% wrong cases = metric granularity issue | 86 labeled cases |
| **Draft Generation** | Template/LLM evidence-constrained (FakeLLMProvider + PromptBuilder + ClaimGuard); no-evidence fallback; high-risk forced human review | Unit tests |
| **Human Review** | Streamlit console; approve/edit/escalate/reject; ReviewDecision JSONL audit trail | Unit + integration tests |
| **Evaluation Pipeline** | CSV prediction mode; pipeline prediction mode; 7 metrics (intent accuracy, severity accuracy, risk flag F1, evidence recall); JSON + Markdown reports | 101-ticket eval coverage |
| **Quality Gate** | Ruff + unit tests + integration tests (skip=fail) + coverage≥70% + OpenSpec validation | Fully automated |

**Safety constraints:**
- **No auto-send**: The system does not connect to any send channel. ReviewDecision writes only to local JSONL.
- **No LLM dependency by default**: Draft generation uses templates; LLM provider interface defined for offline pipeline verification only.
- **Fake embedding by default**: Vector search uses fake embeddings. Real provider requires explicit opt-in via `.env.local`.

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
│  drafting/ (template + LLM provider + guard)  │
├─────────────────────────────────────────────┤
│            Review Console                     │
│  review/ (Streamlit + JSONL persistence)      │
├─────────────────────────────────────────────┤
│            Evaluation Pipeline                │
│  evaluation/ (loaders + metrics + comparison) │
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
- Provider Identity Gate: runtime verification of active provider,
  preventing silent fallback that could mislead metrics
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
git clone https://github.com/lennney/ticketpilot.git
cd ticketpilot

# Install dependencies (including dev dependencies)
uv sync
```

### Run tests

```bash
# Run full quality gate (Ruff + unit tests + integration tests + coverage + OpenSpec)
bash scripts/run_quality_gate.sh

# Or step by step:
uv run ruff check .
uv run pytest tests/unit -q
uv run pytest tests/integration/ -v --strict-markers
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

### Use real embeddings (optional)

```bash
# Edit .env.local:
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIM=1024
EMBEDDING_API_KEY=your_key_here

# Rebuild embedding index
uv run python scripts/rebuild_embeddings.py --confirm
```

### Run the human review console

> Requires PostgreSQL (see below).

```bash
# Start PostgreSQL (requires Docker)
docker compose up -d
# Database migrations run automatically via db/migrations/ on first start

# Verify knowledge seed data (local chunking, no database required)
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

> Full documentation map in section 7 below.
> 中文版请见 [README.md](README.md)。

---

## 7. Documentation Map

| Directory | Contents |
|-----------|----------|
| `docs/technical/` | Technical design docs: system architecture, data contracts, retrieval design, risk rules, quality gate, evaluation pipeline, Provider Identity Gate |
| `docs/demo/` | Demo guide: step-by-step instructions for 3 demo lines; 3 strong demo scenario docs |
| `docs/limitations.md` | Known limitations for the current release |
| `docs/portfolio/` | Portfolio materials: case studies (CN/EN), demo script, interview talking points, limitations and roadmap, Phase 7–10 snapshots |
| `docs/skills/` | Claude Code skills: batch implementation, quality gate acceptance, retrieval evaluation, secure development |
| `docs/development_trace/` | Development process records and retrospectives |
| `docs/changelog.md` | Changelog |
| `openspec/` | OpenSpec spec-driven development artifacts |
| `reports/eval/` | Evaluation report output (JSON + Markdown) |
| `reports/retrieval/` | Retrieval comparison reports (Fake vs Real, Phase 9–10 diagnosis) |

## 8. Project Evolution

### Phase 7 — MVP Evidence Pack (Complete)
- Eval dataset expanded from 10 to **101 synthetic tickets**
- Knowledge base expanded from 36 to **95 records** (FAQ=40, Policy=30, Case=25)
- Added invoice/payment domain, 7 multi-intent tickets, 5 edge-case tickets
- Deterministic offline evaluation pipeline (CSV + Pipeline modes)
- 3 strong demo scenario documents

### Phase 8 — Real Retrieval Upgrade (Complete)
- DashScope text-embedding-v4 (1024-d) integration, FakeEmbeddingProvider retained as default
- EmbeddingConfig + provider factory switching mechanism
- Fake 384-d vs Real 1024-d comparison on fixed dataset
  - Top-1 hit rate: 31.7% → 42.6% (+10.9%)
  - MRR: 0.4114 → 0.4913 (+0.0799)
- Wrong-case analysis: all 41 failures were missing_doc_type — bottleneck is knowledge coverage, not embedding quality

### Phase 9 — Evaluation-Driven Knowledge Optimization (Complete)
- 41 wrong cases → 8 failure categories → 24 knowledge gaps
- Targeted addition of **11 P0 knowledge records** (total 95→106)
- Discovered **Provider Identity Gate** issue: `load_dotenv()` never called, all evals silently fell back to fake provider
- Post-fix real eval: P0 hit rate 75.0%, Top-1 +2.0%
- Wrong cases unchanged at 41 — bottleneck shifted from knowledge coverage to retrieval ranking

### Phase 10 — Hybrid Retrieval Ranking Diagnosis (Complete)
- 8-category retrieval bottleneck taxonomy, 3-layer diagnosis (keyword / vector / fused)
- Doc-level golden labels expanded from 14 to **86 evaluation cases**
- Evaluation unit refined from doc_type to doc_id
- **Doc-ID Recall@10 = 91.9%**, 32.5pp above doc-type metric
- 32/41 doc-type wrong cases reclassified as doc_id-found
- Identified 7 zero-hit cases (query expansion candidates) and 32 partial-hit cases (fusion ranking candidates)

### Phase 11 — Evidence-Grounded LLM Draft (Complete)
- LLM provider abstraction + FakeLLMProvider deterministic implementation (no API dependency)
- Evidence-grounded prompt builder (evidence constraints + safety rules + output format spec)
- DraftCitationValidationResult and validate_draft_citations() (structural evidence ID validation)
- ClaimGuard (5 checks: citation coverage, uncited claims, forbidden promises, evidence sufficiency, risk-aware)
- DraftGenerationResult + generate_draft() wiring all components in sequence
- Human review console update (15 audit fields + guard status display)
- Offline draft evaluation metrics (8 deterministic metrics, citation precision=100%, claim guard pass rate=0%, FakeLLMProvider tests workflow mechanics only)
- 8-layer safety architecture: prompt constraint → citation validation → ClaimGuard → risk-aware → human review propagation → no-auto-send → fake default → provider identity

## 9. Current Limitations

- **Local demo / portfolio level**: This is an architecture-first functional demonstration, not a production customer-service system.
- **Seed data only**: Knowledge base has 106 seed records (FAQ=41, Policy=34, Case=31); evaluation has 101 synthetic tickets. Does not reflect enterprise data scale or diversity.
- **Pipeline metrics note**: Current intent accuracy (~53%) and severity accuracy (~54%) reflect deterministic behavior of rule-based components. These indicate the evaluation framework is established, not production-level performance. No-auto-send compliance=100% is an architectural constraint, not a reply quality metric.
- **Fake embeddings by default**: Vector search uses deterministic fake embeddings (384-dim SHA-256 hash vectors). Real embeddings (DashScope text-embedding-v4) require env var opt-in.
- **Phase 11 draft generation in progress**: LLM provider interface and FakeLLMProvider complete; real provider integration and offline draft evaluation metrics pending.
- **No auto-send**: See section 10.
- **Streamlit console**: MVP-level human review UI, not a production frontend.
- **No multi-user support**: No authentication or permissions model.

## 10. Roadmap

| Direction | Description | Dependency |
|-----------|-------------|------------|
| **Phase 11 completion** | Real LLM provider, ClaimGuard, offline draft eval | None |
| **Retrieval ranking optimization** | RRF weight tuning, query expansion per Phase 10 diagnosis | Phase 10 baseline |
| **Realistic data pack** | Expand knowledge base and eval dataset | None |
| **Expanded eval dataset** | 50+ tickets covering edge cases and combined scenarios | Data pack |
| **Trace persistence** | Optional Langfuse or other tracing integration | Data pack |
| **Auth / multi-user** | Login and role model for review console | None |
| **Production deployment** | Dockerized deployment, CI/CD, monitoring | All above |
| **LangGraph workflow** | Optional LangGraph orchestration of full pipeline | Core eval stable |

## 11. Safety Boundary: No Auto-Send

**This is an architectural constraint, not a configurable option.**

- Generated draft replies are **review suggestions**, not sent customer responses.
- Human review console actions (approve/edit/escalate/reject) write only to local `ReviewDecision` JSONL files — **they do not connect to any send channel**.
- The following situations **require** human review:
  - High-risk flags (legal risk, compensation demands, privacy leaks)
  - No evidence retrieved (fallback mode)
  - Draft contains unsupported claims (per policy rule detection)
  - ClaimGuard validation failure
- No API, message queue, or webhook exists in the current version for automatically sending customer replies.

---

*TicketPilot — local demo / portfolio project*
